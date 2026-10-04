"""Build da tradução do Bucky O'Hare (arcade).

Parte sempre dos arquivos de 00_Original/bucky e gera:
    01_ROM/bucky/        conjunto completo traduzido (ROMs alteradas + as outras)
    01_ROM/bucky.zip     o mesmo, zipado, para o MAME (-rompath 01_ROM)
    01_ROM/patch/*.ips   um IPS por ROM alterada (conferido: original + IPS = build)

Uso:
    build.py                 build normal (lê 03_Traducao/traducao.txt)
    build.py --ida-e-volta   só confere que o codificador reproduz o original
                             byte a byte a partir de 03_Traducao/original_en.txt
    build.py --vitrine msg.32=msg.39,cena.0.0=cena.5.1
                             build de teste em _teste/vitrine: a mensagem/página
                             da esquerda mostra o conteúdo da direita (para ver
                             textos que só aparecem lá no fim do jogo)

O texto traduzido vai para o espaço livre no fim do programa (0x70A00...) e
só os ponteiros das três tabelas mudam. O texto antigo fica no lugar; assim,
qualquer referência que não conhecemos continua válida (e aparece em inglês
no teste, em vez de travar).
"""
import os
import struct
import sys
import zipfile
import zlib

import buckylib as B
import build_placa
import sprites

TRADUCAO = os.path.join(B.RAIZ, '03_Traducao', 'traducao.txt')
ORIGINAL_EN = os.path.join(B.RAIZ, '03_Traducao', 'original_en.txt')
ACENTOS = os.path.join(B.RAIZ, '04_Graficos', 'acentos.txt')
SAIDA = os.path.join(B.RAIZ, '01_ROM')

LIVRE_INI, LIVRE_FIM = 0x70A00, 0x7F980   # texto novo (depois: rotina e tabela da fonte grande)
COMPENSA_INI = 0x7FC00                    # bytes para acertar a soma de cada chip

ARQUIVOS = ['173eab01.q5', '173eab02.q6', '173a03.t5', '173a04.t6', '173a05.t8',
            '173a06.t10', '173a07.f5', '173a08.b6', '173a09.a6', '173a10.b8',
            '173a11.a8', '173a12.b10', '173a13.a10', 'bucky.nv']


class ErroBuild(Exception):
    pass


# ------------------------------------------------------------ leitura

def le_blocos(caminho):
    """-> dict identificador -> lista de linhas (na ordem do arquivo)."""
    blocos, atual = {}, None
    with open(caminho, encoding='utf-8') as f:
        for n, linha in enumerate(f, 1):
            linha = linha.rstrip('\n')
            if linha.startswith(';'):
                continue
            if linha.startswith('@'):
                atual = linha[1:].strip()
                if atual in blocos:
                    raise ErroBuild(f'{caminho}:{n}: bloco repetido @{atual}')
                blocos[atual] = []
            elif atual is not None:
                blocos[atual].append(linha)
    for k in blocos:                       # linhas vazias no fim são só separação
        while blocos[k] and blocos[k][-1] == '':
            blocos[k].pop()
    return blocos


# Mensagens desenhadas dentro de uma moldura: colunas permitidas [ini, fim).
MOLDURA = {16: (11, 37), 17: (28, 54), 18: (27, 53)}


def codifica_msg(i, linhas, erros):
    ident = f'msg.{i}'
    grande = i in B.MSG_GRANDE
    ini, fim = MOLDURA.get(i, (B.COL_MIN, B.COL_FIM))
    regs = []
    for t in linhas:
        if not t:
            erros.append(f'@{ident}: linha vazia no meio da mensagem')
            continue
        lin, col, texto = (t.split(' ', 2) + [''])[:3]
        try:
            bs, _ = B.texto_para_bytes(texto)
        except ValueError as e:
            erros.append(f'@{ident}: {e} em {texto!r}')
            continue
        if grande:
            pode = {B.codigo(c) for c in B.GRANDE_IMPRIMIVEIS}
            falta = sorted({chr(b) for b in bs if b not in pode})
            if falta:
                erros.append(f'@{ident}: a fonte grande não tem {"".join(falta)!r}: {texto!r}')
        casas = len(bs.rstrip(b' ')) * (2 if grande else 1)
        col = (B.CENTRO2 - casas) // 2 if col == 'c' else int(col)
        if casas and (col < ini or col + casas > fim):
            erros.append(f'@{ident}: {texto!r} não cabe (coluna {col}, {casas} casas;'
                         f' permitido {ini}-{fim - 1})')
        regs.append((int(lin, 16), col, bs))
    return B.monta_mensagem(regs)


def codifica_tudo(blocos, p):
    """-> (mensagens {i: bytes}, cenas {s: [bytes por página]}, chefes {c: bytes})."""
    erros = []
    msgs, cenas, chefes = {}, {}, {}
    for i in range(B.N_MSG):
        o = B.L(p, B.TAB_MSG + 4 * i)
        if o:
            ident = f'msg.{i}'
            if ident not in blocos:
                erros.append(f'falta @{ident}')
                continue
            msgs[i] = codifica_msg(i, blocos[ident], erros)
            # gráficos e casas reservadas ({`}, logotipo, {>}) não podem sumir
            graf = lambda regs: sorted(b for _, _, bs in regs for b in bs
                                       if b != 0x20 and B.caractere(b) is None)
            novo = graf(B.le_mensagem(msgs[i], 0))
            orig = graf(B.le_mensagem(p, o))
            if novo != orig:
                erros.append(f'@{ident}: bytes gráficos diferentes do original '
                             f'(original {bytes(orig).hex(" ")}, agora {bytes(novo).hex(" ")})')
    for s in range(B.N_CENAS):
        lista = B.L(p, B.TAB_CENAS + 4 * s)
        cenas[s] = []
        for k in range((B.L(p, lista) - lista) // 4):
            ident = f'cena.{s}.{k}'
            if ident not in blocos:
                erros.append(f'falta @{ident}')
                continue
            bs, e = B.linhas_para_pagina(blocos[ident], B.CENA_LARG, B.CENA_LINHAS, 'tusr ')
            erros += [f'@{ident}: {x}' for x in e]
            cenas[s].append(bs)
    for c in range(B.N_CHEFES):
        ident = f'chefe.{c}'
        if ident not in blocos:
            erros.append(f'falta @{ident}')
            continue
        nome, *caixas = blocos[ident]
        bs_nome, _ = B.texto_para_bytes(nome)
        if bs_nome.count(b':') != 1 or not bs_nome.split(b':')[1].strip(b' ') == b'':
            erros.append(f'@{ident}: o nome tem de terminar com ":" (depois só espaços)')
        bs, e = B.linhas_para_pagina(caixas, B.CHEFE_LARG, B.CHEFE_LINHAS, 'ts ')
        erros += [f'@{ident}: {x}' for x in e]
        chefes[c] = bs_nome + bs
    hud = None
    if 'hud.creditos' in blocos:
        linhas = blocos['hud.creditos']
        if len(linhas) != 3:
            erros.append('@hud.creditos: são 3 linhas (jogo livre, 1 crédito, 2+ créditos)')
        hud = b''
        for t in linhas:
            bs, _ = B.texto_para_bytes(t)
            if len(bs) > HUD_LARG - 1:
                erros.append(f'@hud.creditos: {t!r} passa de {HUD_LARG - 1} casas')
            hud += bs.rjust(HUD_LARG - 1, b' ') + b' '   # número a 1 espaço
    sobra = set(blocos) - {'hud.creditos'} - {f'msg.{i}' for i in msgs} - {f'cena.{s}.{k}' for s in cenas
                                                        for k in range(len(cenas[s]))} \
        - {f'chefe.{c}' for c in chefes}
    erros += [f'bloco desconhecido @{x}' for x in sorted(sobra)]
    if erros:
        raise ErroBuild('\n'.join(erros))
    return msgs, cenas, chefes, hud


# ------------------------------------------------------------ ida e volta

def ida_e_volta():
    p = B.programa()
    msgs, cenas, chefes, _ = codifica_tudo(le_blocos(ORIGINAL_EN), p)
    dif = 0
    for i, bs in msgs.items():
        o = B.L(p, B.TAB_MSG + 4 * i)
        if p[o:o + len(bs)] != bs:
            print(f'msg.{i} difere'); dif += 1
    for s, pags in cenas.items():
        lista = B.L(p, B.TAB_CENAS + 4 * s)
        for k, bs in enumerate(pags):
            o = B.L(p, lista + 4 * k)
            if p[o:o + len(bs)] != bs:
                print(f'cena.{s}.{k} difere'); dif += 1
    for c, bs in chefes.items():
        o = B.L(p, B.TAB_CHEFES + 4 * c)
        if p[o:o + len(bs)] != bs:
            print(f'chefe.{c} difere'); dif += 1
    print('ida e volta:', 'OK, idêntico ao original' if not dif else f'{dif} diferenças')
    return 1 if dif else 0


# ------------------------------------------------------------ montagem

def realoca(p, msgs, cenas, chefes):
    cur = LIVRE_INI

    def grava(bs, alinha=True):
        nonlocal cur
        if alinha and cur % 2:
            p[cur] = 0xFF
            cur += 1
        if cur + len(bs) > LIVRE_FIM:
            raise ErroBuild(f'o texto não cabe no espaço livre ({LIVRE_FIM - LIVRE_INI} bytes)')
        o = cur
        p[o:o + len(bs)] = bs
        cur += len(bs)
        return o

    ja = {}
    for i, bs in msgs.items():
        if bs not in ja:
            ja[bs] = grava(bs)
        struct.pack_into('>I', p, B.TAB_MSG + 4 * i, ja[bs])
    for s, pags in cenas.items():
        lista = grava(bytes(4 * len(pags)))
        for k, bs in enumerate(pags):
            struct.pack_into('>I', p, lista + 4 * k, grava(bs, alinha=False))
        struct.pack_into('>I', p, B.TAB_CENAS + 4 * s, lista)
    for c, bs in chefes.items():
        struct.pack_into('>I', p, B.TAB_CHEFES + 4 * c, grava(bs, alinha=False))
    return cur - LIVRE_INI


def compensa_soma(chip_novo, chip_orig, ini):
    """Acerta a soma de 16 bits do chip baixando bytes 0xFF a partir de `ini`
    (endereço no chip). Diminuir 0x10000 - falta equivale a somar a falta."""
    chip = bytearray(chip_novo)
    alvo = sum(chip_orig) & 0xFFFF
    baixar = (sum(chip) - alvo) & 0xFFFF
    o = ini
    while baixar:
        if chip[o] != 0xFF:
            raise ErroBuild(f'byte de compensação ocupado em {o:05X}')
        d = min(baixar, 0xFF)
        chip[o] -= d
        baixar -= d
        o += 1
    assert sum(chip) & 0xFFFF == alvo
    return bytes(chip)


def le_acentos():
    """-> (pequenos {c: 8 linhas}, grandes {c: 16 linhas})."""
    peq, gde, atual = {}, {}, None
    with open(ACENTOS, encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith(';'):
                continue
            if len(linha) == 1:
                atual = peq.setdefault(linha, [])
            elif linha.endswith(' grande'):
                atual = gde.setdefault(linha[0], [])
            else:
                atual.append(linha)
    for nome, glifos, tam in (('', peq, 8), (' grande', gde, 16)):
        for c, g in glifos.items():
            if len(g) != tam or any(len(r) != tam for r in g):
                raise ErroBuild(f'acentos.txt: {c}{nome} precisa ter {tam} linhas de {tam} pontos')
    falta = (set(B.ACENTOS) - set(peq)) | (set(B.GRANDES_NOVOS) - set(gde))
    if falta:
        raise ErroBuild(f'acentos.txt: faltam {"".join(sorted(falta))}')
    return peq, gde


def grava_tile(d, t, linhas, vazio=True):
    """Grava 8x8 pontos ('.' ou dígito hex) no tile t, conferindo (se vazio=True)
    que ele estava vazio."""
    if vazio and any(d[t * 32:t * 32 + 32]):
        raise ErroBuild(f'tile {t:03X} não está vazio na ROM')
    pos_x = {k: x for x, k in enumerate((2, 3, 0, 1, 6, 7, 4, 5))}
    for y, r in enumerate(linhas):
        for k in range(8):
            v = 0 if r[pos_x[k]] == '.' else int(r[pos_x[k]], 16)
            o = t * 32 + y * 4 + k // 2
            d[o] = (d[o] & 0x0F) | v << 4 if k % 2 == 0 else (d[o] & 0xF0) | v


def desenha_acentos(d):
    peq, gde = le_acentos()
    for c, g in peq.items():
        grava_tile(d, B.TILES_ACENTO[B.ACENTOS.index(c)], g)
    for c, g in gde.items():
        cc = B.GRANDES_NOVOS[c]
        for dt, y0, x0 in ((0, 0, 0), (1, 0, 8), (0x10, 8, 0), (0x11, 8, 8)):
            grava_tile(d, cc + dt, [r[x0:x0 + 8] for r in g[y0:y0 + 8]])


# ------------------------------------------------------------ placar

PLACAR = os.path.join(B.RAIZ, '04_Graficos', 'placar.txt')
# Tiles das palavras originais (INSERT COIN, CONTINUE, GAME OVER, PRESS,
# START, SELECT), que passam a guardar as palavras novas.
PLACAR_TILES = (list(range(0x250, 0x258)) + list(range(0x260, 0x268)) +
                list(range(0x270, 0x27F)) + list(range(0x280, 0x28F)) +
                list(range(0x290, 0x2A0)) + list(range(0x2A0, 0x2B0)) +
                # tiles com o padrão "x" de não usado (iguais ao tile 0x10)
                [0x249, 0x258, 0x259, 0x26F, 0x27F, 0x28F, 0x2BF, 0x2DD, 0x2DE, 0x2DF,
                 0x2FC, 0x2FD, 0x2FE, 0x2FF])
PLACAR_VAZIO = 0x46


def le_placar():
    palavras, letras, espaco, atual = [], {}, 2, None
    with open(PLACAR, encoding='utf-8') as f:
        for linha in f:
            linha = linha.rstrip('\n')
            if linha.startswith(';'):
                continue
            if linha.startswith('@palavra '):
                _, tab, larg, alin, cor, texto = linha.split(' ', 5)
                palavras.append((int(tab, 16), int(larg), alin, int(cor), texto))
            elif linha.startswith('@espaco '):
                espaco = int(linha.split()[1])
            elif not linha.strip():
                atual = None
            elif atual is None:
                atual = letras.setdefault(linha.strip(), [])
            else:
                atual.append(linha.strip())
    for c, g in letras.items():
        if len(g) not in (14, 16) or len({len(r) for r in g}) != 1:
            raise ErroBuild(f'placar.txt: letra {c} precisa de 14 ou 16 linhas de mesma largura')
    return palavras, letras, espaco


def desenha_palavra(texto, larg_tiles, alin, cor, letras, espaco):
    """-> 16 linhas de larg_tiles*8 caracteres ('.' ou dígito hex)."""
    cols = []
    for c in texto:
        if c == ' ':
            cols += [['.'] * 16] * espaco
            continue
        if c not in letras:
            raise ErroBuild(f'placar.txt: falta a letra {c!r} (palavra {texto!r})')
        g = letras[c]
        g = ['.' * len(g[0])] * (16 - len(g)) + g
        for x in range(len(g[0])):
            cols.append([g[y][x] for y in range(16)])
    total = larg_tiles * 8
    if len(cols) > total:
        raise ErroBuild(f'placar: {texto!r} tem {len(cols)} pixels; cabem {total}')
    x0 = {'e': 2, 'd': total - 2 - len(cols), 'c': (total - len(cols)) // 2}[alin]
    x0 = max(0, min(x0, total - len(cols)))
    linhas = [['.'] * total for _ in range(16)]
    for x, col in enumerate(cols):
        for y, v in enumerate(col):
            linhas[y][x0 + x] = {'1': f'{cor:X}', '2': '2'}.get(v, '.')
    return [''.join(r) for r in linhas]


def aplica_placar(p, d):
    palavras, letras, espaco = le_placar()
    livres = list(PLACAR_TILES)
    ja = {}
    for tab, larg, alin, cor, texto in palavras:
        img = desenha_palavra(texto, larg, alin, cor, letras, espaco)
        bytes_tab = bytearray()
        for y0 in (0, 8):
            for tx in range(larg):
                t = tuple(r[tx * 8:tx * 8 + 8] for r in img[y0:y0 + 8])
                if all(c == '.' for r in t for c in r):
                    bytes_tab.append(PLACAR_VAZIO)
                    continue
                if t not in ja:
                    if not livres:
                        raise ErroBuild('placar: acabaram os tiles livres')
                    ja[t] = livres.pop(0)
                    grava_tile(d, ja[t], t, vazio=False)
                bytes_tab.append(ja[t] - 0x200)
        p[tab:tab + len(bytes_tab)] = bytes_tab
    for t in livres:                       # o que sobrou fica vazio
        d[t * 32:t * 32 + 32] = bytes(32)
    return len(PLACAR_TILES) - len(livres)


# ------------------------------------------------------------ patches no código

# Rotina nova da fonte grande e a tabela de 16 bits (tile por caractere,
# índice = byte - 0x20), no fim do espaço livre.
ROTINA_GRANDE, TAB_GRANDE = 0x7F980, 0x7FA00

# Créditos no canto (rotina 0x258E): 3 campos de 8 letras em 0x2600 (jogo livre,
# CREDIT, CREDITS) seguidos do número. Passam a ter 9 casas, começando uma coluna
# antes (43), com o texto em HUD_TEXTO.
HUD_LARG, HUD_TEXTO = 9, 0x7FBC0
PATCHES_HUD = [
    (0x25A8, '4DF9 0018 1CB0', '4DF9 0018 1CAC', 'créditos: começam na coluna 43'),
    (0x25AE, '4BF9 0000 2600', f'4BF9 {HUD_TEXTO >> 16:04X} {HUD_TEXTO & 0xFFFF:04X}', 'créditos: texto novo'),
    (0x25BE, '4BED 0008', '4BED 0009', 'créditos: campos de 9'),
    (0x25D0, '4BED 0008', '4BED 0009', 'créditos: campos de 9'),
    (0x25EE, '3A3C 0007', '3A3C 0008', 'créditos: 9 letras por campo'),
]

# (endereço, bytes originais, bytes novos, motivo). O build confere os
# originais antes de trocar.
PATCHES = [
    (0x1EC0, '49F9 0000 1F2E', f'49F9 {TAB_GRANDE >> 16:04X} {TAB_GRANDE & 0xFFFF:04X}',
     'fonte grande: lea da tabela nova (16 bits)'),
    (0x1ED8, '0407 0020 1C07 1E34 6000',
     f'4EB9 {ROTINA_GRANDE >> 16:04X} {ROTINA_GRANDE & 0xFFFF:04X} 4E71 4E71',
     'fonte grande: jsr para a rotina que lê a tabela de 16 bits'),
    # Tela de fichas (mensagem 28): o jogo escreve o número de fichas e o "S"
    # do plural em casas fixas. Com "INICIAR 1 FICHA(S)  CONTINUAR 1 FICHA(S)"
    # a partir da coluna 13: número nas colunas 21 e 41, "S" nas 28 e 48.
    (0x7126, '43F9 0018 1160', '43F9 0018 1154', 'fichas: 1º número na coluna 21'),
    (0x714E, '2341 0014', '2341 001C', 'fichas: 1º "S" na coluna 28'),
    (0x7158, '2340 0058', '2340 0050', 'fichas: 2º número na coluna 41'),
    (0x7164, '2341 006C', '2341 006C', 'fichas: 2º "S" na coluna 48 (igual)'),
]

ROTINA_GRANDE_COD = bytes.fromhex(
    '0407 0020'    # subi.b #$20,D7
    '7C00'         # moveq  #0,D6
    '1C07'         # move.b D7,D6
    'DC46'         # add.w  D6,D6
    '3E34 6000'    # move.w (A4,D6.w),D7   (tile completo; antes era 0x100 + byte)
    '4E75')        # rts


def aplica_patches(p, hud):
    for ende, orig, novo, motivo in PATCHES + (PATCHES_HUD if hud else []):
        orig, novo = bytes.fromhex(orig), bytes.fromhex(novo)
        if p[ende:ende + len(orig)] != orig:
            raise ErroBuild(f'patch {ende:06X} ({motivo}): bytes originais não conferem')
        p[ende:ende + len(novo)] = novo
    p[ROTINA_GRANDE:ROTINA_GRANDE + len(ROTINA_GRANDE_COD)] = ROTINA_GRANDE_COD
    tab = bytearray()
    for b in range(0x20, 0x100):
        c = B.caractere(b)
        if b < 0x60:
            t = 0x100 + p[B.TAB_GRANDE_ORIG + b - 0x20]
        else:
            t = 0x140                                  # espaço
        if c in B.GRANDES_NOVOS:
            t = B.GRANDES_NOVOS[c]
        tab += struct.pack('>H', t)
    p[TAB_GRANDE:TAB_GRANDE + len(tab)] = tab
    if hud:
        p[HUD_TEXTO:HUD_TEXTO + len(hud)] = hud


# ------------------------------------------------------------ IPS

def ips(orig, novo):
    out = bytearray(b'PATCH')
    i = 0
    while i < len(novo):
        if novo[i] == orig[i]:
            i += 1
            continue
        j = i
        while j < len(novo) and j - i < 0xFFFF and (novo[j] != orig[j] or
                                                   novo[j + 1:j + 6] != orig[j + 1:j + 6]):
            j += 1
        if i == 0x454F46:                 # "EOF" não pode ser deslocamento
            i -= 1
        out += i.to_bytes(3, 'big') + (j - i).to_bytes(2, 'big') + novo[i:j]
        i = j
    return bytes(out + b'EOF')


def aplica_ips(orig, patch):
    d = bytearray(orig)
    o = 5
    while patch[o:o + 3] != b'EOF':
        ofs = int.from_bytes(patch[o:o + 3], 'big')
        n = int.from_bytes(patch[o + 3:o + 5], 'big')
        o += 5
        if n:
            d[ofs:ofs + n] = patch[o:o + n]
            o += n
        else:
            n = int.from_bytes(patch[o:o + 2], 'big')
            d[ofs:ofs + n] = patch[o + 2:o + 3] * n
            o += 3
    return bytes(d)


# ------------------------------------------------------------ main

def ponteiro(p, ident):
    """Endereço da entrada de tabela que aponta para msg.N / cena.S.K."""
    partes = ident.split('.')
    if partes[0] == 'msg':
        return B.TAB_MSG + 4 * int(partes[1])
    if partes[0] == 'cena':
        return B.L(p, B.TAB_CENAS + 4 * int(partes[1])) + 4 * int(partes[2])
    raise ErroBuild(f'vitrine: {ident} não é msg.N nem cena.S.K')


def vitrine(p, trocas):
    """Só para teste: faz a mensagem/página A mostrar o conteúdo de B."""
    for troca in trocas:
        a, b = troca.split('=')
        if a.startswith('placar.'):        # placar.251A=254A: copia a tabela de 8+8 tiles
            a, b = int(a.split('.')[1], 16), int(b.split('.')[-1], 16)
            p[a:a + 16] = p[b:b + 16]
            continue
        struct.pack_into('>I', p, ponteiro(p, a), B.L(p, ponteiro(p, b)))


def build(trocas=None):
    global SAIDA
    p = B.programa()
    msgs, cenas, chefes, hud = codifica_tudo(le_blocos(TRADUCAO), p)
    usados = realoca(p, msgs, cenas, chefes)
    aplica_patches(p, hud)
    d = B.tiles()
    desenha_acentos(d)
    n_placar = aplica_placar(p, d)
    if trocas:
        vitrine(p, trocas)
        SAIDA = os.path.join(B.RAIZ, '_teste', 'vitrine')
        print('VITRINE (só para teste):', ', '.join(trocas), '->', SAIDA)
    q5, q6 = B.separa_programa(p)
    q5 = compensa_soma(q5, B.le('173eab01.q5'), COMPENSA_INI // 2)
    q6 = compensa_soma(q6, B.le('173eab02.q6'), COMPENSA_INI // 2)
    t8, t10 = B.separa_tiles(d)
    novos = {'173eab01.q5': q5, '173eab02.q6': q6, '173a05.t8': t8, '173a06.t10': t10}
    spr = sprites.le()
    build_placa.aplica(spr)                # placa "Hurry Up!" -> "ANDA LOGO!"
    for nome, dados in sprites.separa(spr).items():
        if dados != B.le(nome):
            novos[nome] = dados

    pasta = os.path.join(SAIDA, 'bucky')
    os.makedirs(pasta, exist_ok=True)
    os.makedirs(os.path.join(SAIDA, 'patch'), exist_ok=True)
    with zipfile.ZipFile(os.path.join(SAIDA, 'bucky.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for nome in ARQUIVOS:
            dados = novos.get(nome) or B.le(nome)
            with open(os.path.join(pasta, nome), 'wb') as f:
                f.write(dados)
            z.writestr(nome, dados)
    # para o FBNeo: só os arquivos alterados, em system/fbneo/patched/bucky.zip
    os.makedirs(os.path.join(SAIDA, 'fbneo_patched'), exist_ok=True)
    with zipfile.ZipFile(os.path.join(SAIDA, 'fbneo_patched', 'bucky.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for nome, dados in novos.items():
            z.writestr(nome, dados)
    print(f'texto novo: {usados} bytes em {LIVRE_INI:06X} (cabem {LIVRE_FIM - LIVRE_INI})')
    print(f'placar: {n_placar} de {len(PLACAR_TILES)} tiles usados')
    for nome, dados in novos.items():
        orig = B.le(nome)
        patch = ips(orig, dados)
        if aplica_ips(orig, patch) != dados:
            raise ErroBuild(f'IPS de {nome} não reproduz o build')
        with open(os.path.join(SAIDA, 'patch', nome + '.ips'), 'wb') as f:
            f.write(patch)
        print(f'{nome:12} CRC32 {zlib.crc32(dados):08X} (original {zlib.crc32(orig):08X})'
              f'  soma {sum(dados) & 0xFFFF:04X}  IPS {len(patch)} bytes')
    if not trocas:
        pacote(novos)


VERSAO = '0.9'


def pacote(novos):
    """Zip de distribuição: LEIAME + um IPS por ROM alterada. Nunca a ROM."""
    import hashlib
    linhas = []
    for nome in novos:
        o = B.le(nome)
        linhas.append(f'  {nome:12} {len(o):8} bytes  CRC32 {zlib.crc32(o):08X}\r\n'
                      f'      MD5   {hashlib.md5(o).hexdigest().upper()}\r\n'
                      f'      SHA-1 {hashlib.sha1(o).hexdigest().upper()}\r\n')
    finais = ''.join(f'  {n:12} CRC32 {zlib.crc32(d):08X}\r\n' for n, d in novos.items())
    with open(os.path.join(B.RAIZ, '06_Documentacao', 'LEIAME_modelo.txt'), encoding='utf-8') as f:
        leiame = f.read().replace('\n', '\r\n')
    leiame = (leiame.replace('{VERSAO}', VERSAO).replace('{ORIGINAIS}', ''.join(linhas).rstrip('\r\n'))
              .replace('{FINAIS}', finais.rstrip('\r\n')).replace('{N}', str(len(novos)))
              .replace('{LISTA_IPS}', '\r\n'.join(f'     {n + ".ips":17} ->  {n}' for n in novos)))
    nome_zip = os.path.join(SAIDA, f'Bucky_OHare_PTBR_v{VERSAO}.zip')
    with zipfile.ZipFile(nome_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('LEIAME.txt', '﻿'.encode('utf-8') + leiame.encode('utf-8'))
        for nome in novos:
            z.write(os.path.join(SAIDA, 'patch', nome + '.ips'), f'patch/{nome}.ips')
    print('pacote:', nome_zip)


def main():
    try:
        if '--ida-e-volta' in sys.argv:
            return ida_e_volta()
        if '--vitrine' in sys.argv:
            return build(sys.argv[sys.argv.index('--vitrine') + 1].split(','))
        build()
    except ErroBuild as e:
        print('BUILD RECUSADO:\n' + str(e))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
