"""Bucky O'Hare (arcade Konami, conjunto `bucky`, versão EAB): formatos de texto.

Programa 68000 = 173eab01.q5 (bytes pares) + 173eab02.q6 (bytes ímpares).
O jogo confere no boot a soma simples dos bytes de cada chip (os valores
esperados estão em 0x40000: 1D7F 5BBD 5E6B 9E32).

Tiles de texto (K056832): 173a05.t8 + 173a06.t10, ROM_LOAD32_WORD. O texto é
desenhado com tile = (byte - 0x30) & 0xFF, então:
    0x20-0x2F (espaço e ! " # ... , - . /) -> tiles 0xF0-0xFF
    0x30-0x5A (0-9 : ; < = > ? @ A-Z)       -> tiles 0x00-0x2A
    0x90-0x9B (letras acentuadas novas)      -> tiles 0x60-0x6B (estavam vazios)

Três tipos de texto:

1. Mensagens (rotina 0x1E16), tabela de 80 ponteiros em 0x402E0.
   Cada mensagem é uma lista de registros:
       0x0018LLCC (32 bits: endereço na VRAM; LL = linha, CC = coluna*4)
       texto
       '[' (vem outro registro) ou ']' (fim da mensagem)
   O registro seguinte é lido com movea.l, então tem de começar em endereço
   par: texto + terminador precisa ter tamanho par (o original completa com
   espaço). No texto, '>' pula uma casa (é onde o jogo escreve um número).
   Tela visível: colunas 8 a 55; o centro é a coluna 31,5.

2. Cenas da história (rotina 0x7A44): tabela de 8 ponteiros em 0x79C6, cada
   um para uma lista de N ponteiros de página (N fixo por cena, o código decide
   quando mostra cada página). Página: '[' abre caixa (limpa), '<' passa para a
   2ª linha, 'u' 't' 's' 'r' são pausas (0x10, 0x20, 0x40, 0x80 quadros),
   espaço pula uma casa, ']' fim. Linhas começam na coluna 13.

3. Falas dos chefes (rotina 0x7B2A): tabela de 16 ponteiros em 0x79E6.
   "NOME:" (impresso até o ':') e depois caixas como nas cenas, com 't' e 's'
   (sem 'u'/'r') e caixas de 2 linhas de 23 casas a partir da coluna 27.
"""
import os
import struct

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(RAIZ, '00_Original', 'bucky')

TAB_MSG, N_MSG = 0x402E0, 80
TAB_CENAS, N_CENAS = 0x79C6, 8
TAB_CHEFES, N_CHEFES = 0x79E6, 16

COL_MIN, COL_FIM = 8, 56          # colunas visíveis: 8..55
CENTRO2 = 63                      # coluna centrada = (63 - largura) // 2
CENA_LARG, CENA_LINHAS = 43, 2    # 13..55
CHEFE_LARG, CHEFE_LINHAS = 23, 2

# Letras novas: caractere -> tile (byte no texto = tile + 0x30)
ACENTOS = 'ÁÀÂÃÉÊÍÓÔÕÚÇ'
TILE_ACENTO0 = 0x60
IMPRIMIVEIS = (' !"#$%&\'()*+,-./0123456789:;=?ABCDEFGHIJKLMNOPQRSTUVWXYZ' + ACENTOS)


def codigo(c):
    """Caractere imprimível -> byte."""
    if c in ACENTOS:
        return TILE_ACENTO0 + ACENTOS.index(c) + 0x30
    if c in IMPRIMIVEIS:
        return ord(c)
    raise ValueError(f'caractere sem desenho na fonte: {c!r}')


def caractere(b):
    """Byte -> caractere imprimível, ou None se for código/gráfico."""
    if b in range(TILE_ACENTO0 + 0x30, TILE_ACENTO0 + 0x30 + len(ACENTOS)):
        return ACENTOS[b - TILE_ACENTO0 - 0x30]
    c = chr(b)
    return c if c in IMPRIMIVEIS else None


# ---------------------------------------------------------------- ROMs

def le(nome, pasta=ORIG):
    with open(os.path.join(pasta, nome), 'rb') as f:
        return f.read()


def programa(pasta=ORIG):
    a, b = le('173eab01.q5', pasta), le('173eab02.q6', pasta)
    p = bytearray(len(a) * 2)
    p[0::2], p[1::2] = a, b
    return p


def separa_programa(p):
    return bytes(p[0::2]), bytes(p[1::2])


def tiles(pasta=ORIG):
    a, b = le('173a05.t8', pasta), le('173a06.t10', pasta)
    d = bytearray(len(a) * 2)
    for i in range(0, len(a), 2):
        d[i * 2:i * 2 + 2] = a[i:i + 2]
        d[i * 2 + 2:i * 2 + 4] = b[i:i + 2]
    return d


def separa_tiles(d):
    a, b = bytearray(len(d) // 2), bytearray(len(d) // 2)
    for i in range(0, len(a), 2):
        a[i:i + 2] = d[i * 2:i * 2 + 2]
        b[i:i + 2] = d[i * 2 + 2:i * 2 + 4]
    return bytes(a), bytes(b)


def L(p, o):
    return struct.unpack_from('>I', p, o)[0]


# ------------------------------------------------- texto <-> arquivo

def _cru(b):
    c = chr(b)
    return c if ' ' <= c <= '~' and c not in '{}\\' else f'\\{b:02X}'


def bytes_para_texto(bs):
    """Bytes de uma linha -> texto do arquivo de tradução. O que não é letra
    da fonte (códigos de pausa, gráficos) e espaços no fim vão entre chaves;
    lá dentro, '{', '}', '\\' e bytes fora do ASCII viram \\NN (hex)."""
    corpo = bs.rstrip(b' ')
    fim = bs[len(corpo):]
    out, cru = [], []
    for b in corpo:
        c = caractere(b)
        if c is None:
            cru.append(_cru(b))
            continue
        if cru:
            out.append('{' + ''.join(cru) + '}')
            cru = []
        out.append(c)
    cru.extend(_cru(b) for b in fim)
    if cru:
        out.append('{' + ''.join(cru) + '}')
    return ''.join(out)


def _cru_para_bytes(s):
    out = bytearray()
    i = 0
    while i < len(s):
        if s[i] == '\\':
            out.append(int(s[i + 1:i + 3], 16))
            i += 3
        else:
            out.append(ord(s[i]))
            i += 1
    return out


def texto_para_bytes(t):
    """Inverso de bytes_para_texto. Devolve (bytes, largura visível)."""
    out = bytearray()
    larg = 0
    i = 0
    while i < len(t):
        if t[i] == '{':
            j = t.index('}', i)
            out += _cru_para_bytes(t[i + 1:j])
            i = j + 1
            continue
        out.append(codigo(t[i]))
        larg += 1
        i += 1
    return bytes(out), larg


# ------------------------------------------------- 1. mensagens

def le_mensagem(p, o):
    """-> lista de (linha, coluna, bytes)."""
    regs = []
    while True:
        h = L(p, o)
        if h >> 16 != 0x18:
            raise ValueError(f'registro inesperado em {o:06X}')
        o += 4
        s = o
        while p[o] not in (0x5B, 0x5D):
            o += 1
        regs.append(((h >> 8) & 0xFF, (h & 0xFF) // 4, bytes(p[s:o])))
        o += 1
        if p[o - 1] == 0x5D:
            return regs


def monta_mensagem(regs):
    out = bytearray()
    for k, (lin, col, bs) in enumerate(regs):
        if len(bs) % 2 == 0:   # texto + terminador precisa ser par
            bs += b' '
        out += struct.pack('>I', 0x180000 | lin << 8 | col * 4) + bs
        out.append(0x5D if k == len(regs) - 1 else 0x5B)
    return bytes(out)


# ------------------------------------------------- 2/3. páginas com caixas

def le_ate_fim(p, o):
    """Bytes de o até o ']' inclusive."""
    e = p.index(b']', o)
    return bytes(p[o:e + 1])


def paginas_para_linhas(bs):
    """Página (sem o ']' final) -> linhas do arquivo: cada caixa começa com
    '[', cada '<' vira nova linha."""
    linhas = []
    pre, _, resto = bs.partition(b'[')
    if pre:
        raise ValueError(f'texto antes do primeiro [: {pre!r}')
    for caixa in resto.split(b'['):
        for k, lin in enumerate(caixa.split(b'<')):
            linhas.append(('[' if k == 0 else '') + bytes_para_texto(lin))
    return linhas


def linhas_para_pagina(linhas, larg_max, linhas_max, pausas):
    """Inverso de paginas_para_linhas, validando largura e linhas por caixa."""
    out = bytearray()
    erros = []
    n_caixa = 0
    for t in linhas:
        if t.startswith('['):
            out.append(0x5B)
            t = t[1:]
            n_caixa = 0
        elif not out:
            erros.append('a primeira linha tem de começar com [')
        else:
            out.append(0x3C)
        n_caixa += 1
        try:
            bs, larg = texto_para_bytes(t)
        except ValueError as e:
            erros.append(f'{e} em {t!r}')
            continue
        cru = bytes(b for b in bs if caractere(b) is None)
        if any(chr(b) not in pausas for b in cru):
            erros.append(f'código não permitido aqui em {t!r} (só {pausas!r})')
        if larg > larg_max:
            erros.append(f'linha com {larg} letras (máx. {larg_max}): {t!r}')
        if n_caixa > linhas_max:
            erros.append(f'caixa com mais de {linhas_max} linhas: {t!r}')
        out += bs
    out.append(0x5D)
    return bytes(out), erros
