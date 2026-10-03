"""Build da tradução do Bucky O'Hare (arcade).

Parte sempre dos arquivos de 00_Original/bucky e gera:
    01_ROM/bucky/        conjunto completo traduzido (ROMs alteradas + as outras)
    01_ROM/bucky.zip     o mesmo, zipado, para o MAME (-rompath 01_ROM)
    01_ROM/patch/*.ips   um IPS por ROM alterada (conferido: original + IPS = build)

Uso:
    build.py                 build normal (lê 03_Traducao/traducao.txt)
    build.py --ida-e-volta   só confere que o codificador reproduz o original
                             byte a byte a partir de 03_Traducao/original_en.txt

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

TRADUCAO = os.path.join(B.RAIZ, '03_Traducao', 'traducao.txt')
ORIGINAL_EN = os.path.join(B.RAIZ, '03_Traducao', 'original_en.txt')
ACENTOS = os.path.join(B.RAIZ, '04_Graficos', 'acentos.txt')
SAIDA = os.path.join(B.RAIZ, '01_ROM')

LIVRE_INI, LIVRE_FIM = 0x70A00, 0x7FC00   # texto novo
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


def codifica_msg(ident, linhas, erros):
    regs = []
    for t in linhas:
        if not t:
            erros.append(f'@{ident}: linha vazia no meio da mensagem')
            continue
        lin, col, texto = (t.split(' ', 2) + [''])[:3]
        try:
            bs, larg = B.texto_para_bytes(texto)
        except ValueError as e:
            erros.append(f'@{ident}: {e} em {texto!r}')
            continue
        col = (B.CENTRO2 - larg) // 2 if col == 'c' else int(col)
        if larg and (col < B.COL_MIN or col + larg > B.COL_FIM):
            erros.append(f'@{ident}: {texto!r} sai da tela (coluna {col}, {larg} letras;'
                         f' visível {B.COL_MIN}-{B.COL_FIM - 1})')
        regs.append((int(lin, 16), col, bs))
    return B.monta_mensagem(regs)


def codifica_tudo(blocos, p):
    """-> (mensagens {i: bytes}, cenas {s: [bytes por página]}, chefes {c: bytes})."""
    erros = []
    msgs, cenas, chefes = {}, {}, {}
    for i in range(B.N_MSG):
        if B.L(p, B.TAB_MSG + 4 * i):
            ident = f'msg.{i}'
            if ident not in blocos:
                erros.append(f'falta @{ident}')
                continue
            msgs[i] = codifica_msg(ident, blocos[ident], erros)
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
    sobra = set(blocos) - {f'msg.{i}' for i in msgs} - {f'cena.{s}.{k}' for s in cenas
                                                        for k in range(len(cenas[s]))} \
        - {f'chefe.{c}' for c in chefes}
    erros += [f'bloco desconhecido @{x}' for x in sorted(sobra)]
    if erros:
        raise ErroBuild('\n'.join(erros))
    return msgs, cenas, chefes


# ------------------------------------------------------------ ida e volta

def ida_e_volta():
    p = B.programa()
    msgs, cenas, chefes = codifica_tudo(le_blocos(ORIGINAL_EN), p)
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
    glifos, atual = {}, None
    with open(ACENTOS, encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith(';'):
                continue
            if len(linha) == 1:
                atual = linha
                glifos[atual] = []
            else:
                glifos[atual].append(linha)
    for c, g in glifos.items():
        if len(g) != 8 or any(len(r) != 8 for r in g):
            raise ErroBuild(f'acentos.txt: {c} precisa ter 8 linhas de 8 pontos')
    falta = set(B.ACENTOS) - set(glifos)
    if falta:
        raise ErroBuild(f'acentos.txt: faltam {"".join(sorted(falta))}')
    return glifos


def desenha_acentos(d):
    pos_x = {k: x for x, k in enumerate((2, 3, 0, 1, 6, 7, 4, 5))}
    for c, g in le_acentos().items():
        t = B.TILE_ACENTO0 + B.ACENTOS.index(c)
        if any(d[t * 32:t * 32 + 32]):
            raise ErroBuild(f'tile {t:02X} (para {c}) não está vazio na ROM')
        for y, r in enumerate(g):
            for k in range(8):
                v = 0 if r[pos_x[k]] == '.' else int(r[pos_x[k]], 16)
                o = t * 32 + y * 4 + k // 2
                d[o] = (d[o] & 0x0F) | v << 4 if k % 2 == 0 else (d[o] & 0xF0) | v


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

def build():
    p = B.programa()
    msgs, cenas, chefes = codifica_tudo(le_blocos(TRADUCAO), p)
    usados = realoca(p, msgs, cenas, chefes)
    q5, q6 = B.separa_programa(p)
    q5 = compensa_soma(q5, B.le('173eab01.q5'), COMPENSA_INI // 2)
    q6 = compensa_soma(q6, B.le('173eab02.q6'), COMPENSA_INI // 2)
    d = B.tiles()
    desenha_acentos(d)
    t8, t10 = B.separa_tiles(d)
    novos = {'173eab01.q5': q5, '173eab02.q6': q6, '173a05.t8': t8, '173a06.t10': t10}

    pasta = os.path.join(SAIDA, 'bucky')
    os.makedirs(pasta, exist_ok=True)
    os.makedirs(os.path.join(SAIDA, 'patch'), exist_ok=True)
    with zipfile.ZipFile(os.path.join(SAIDA, 'bucky.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for nome in ARQUIVOS:
            dados = novos.get(nome) or B.le(nome)
            with open(os.path.join(pasta, nome), 'wb') as f:
                f.write(dados)
            z.writestr(nome, dados)
    print(f'texto novo: {usados} bytes em {LIVRE_INI:06X} (cabem {LIVRE_FIM - LIVRE_INI})')
    for nome, dados in novos.items():
        orig = B.le(nome)
        patch = ips(orig, dados)
        if aplica_ips(orig, patch) != dados:
            raise ErroBuild(f'IPS de {nome} não reproduz o build')
        with open(os.path.join(SAIDA, 'patch', nome + '.ips'), 'wb') as f:
            f.write(patch)
        print(f'{nome:12} CRC32 {zlib.crc32(dados):08X} (original {zlib.crc32(orig):08X})'
              f'  soma {sum(dados) & 0xFFFF:04X}  IPS {len(patch)} bytes')


def main():
    try:
        if '--ida-e-volta' in sys.argv:
            return ida_e_volta()
        build()
    except ErroBuild as e:
        print('BUILD RECUSADO:\n' + str(e))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
