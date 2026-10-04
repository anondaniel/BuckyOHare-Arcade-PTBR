"""ROMs de sprites do Bucky (K053246/K053247): 173a10.b8, 173a11.a8, 173a12.b10,
173a13.a10, carregadas com ROM_LOAD64_WORD (cada ROM dá 2 bytes de cada grupo
de 8). Sprite = blocos 16x16 de 4 bits, 128 bytes (16 linhas de 8 bytes),
nibbles na ordem 2,3,0,1,6,7,4,5,10,11,8,9,14,15,12,13 (nibble par = 4 bits
altos), como os tiles do K056832.

Um sprite de w x h blocos começa no código c; o bloco (bx, by) é
c + XOFS[bx] + YOFS[by].

Uso: sprites.py <código hex> <w> <h> saida.png  (mostra um sprite ampliado)
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(RAIZ, '00_Original', 'bucky')
ARQS = ('173a10.b8', '173a11.a8', '173a12.b10', '173a13.a10')
ORDEM_X = (2, 3, 0, 1, 6, 7, 4, 5, 10, 11, 8, 9, 14, 15, 12, 13)
XOFS = (0, 1, 4, 5, 16, 17, 20, 21)
YOFS = (0, 2, 8, 10, 32, 34, 40, 42)


def le(pasta=ORIG):
    rs = [open(os.path.join(pasta, a), 'rb').read() for a in ARQS]
    d = bytearray(len(rs[0]) * 4)
    for k, r in enumerate(rs):
        for j in range(2):
            d[k * 2 + j::8] = r[j::2]
    return d


def separa(d):
    out = []
    for k in range(4):
        r = bytearray(len(d) // 4)
        for j in range(2):
            r[j::2] = d[k * 2 + j::8]
        out.append(bytes(r))
    return dict(zip(ARQS, out))


def bloco(d, n):
    """16 linhas de 16 valores (0-15)."""
    base = n * 128
    g = []
    for y in range(16):
        lin = d[base + y * 8: base + y * 8 + 8]
        g.append([lin[k // 2] >> 4 if k % 2 == 0 else lin[k // 2] & 15 for k in ORDEM_X])
    return g


def grava_bloco(d, n, g):
    base = n * 128
    for y in range(16):
        for x, k in enumerate(ORDEM_X):
            o = base + y * 8 + k // 2
            v = g[y][x]
            d[o] = (d[o] & 0x0F) | v << 4 if k % 2 == 0 else (d[o] & 0xF0) | v


def sprite(d, codigo, w, h):
    """Imagem (lista de linhas) de um sprite de w x h blocos."""
    img = [[0] * (w * 16) for _ in range(h * 16)]
    for by in range(h):
        for bx in range(w):
            g = bloco(d, codigo + XOFS[bx] + YOFS[by])
            for y in range(16):
                img[by * 16 + y][bx * 16:bx * 16 + 16] = g[y]
    return img


if __name__ == '__main__':
    from PIL import Image
    d = le()
    c, w, h = int(sys.argv[1], 16), int(sys.argv[2]), int(sys.argv[3])
    img = sprite(d, c, w, h)
    im = Image.new('L', (w * 16, h * 16))
    im.putdata([v * 17 for r in img for v in r])
    im.resize((w * 16 * 6, h * 16 * 6), Image.NEAREST).save(sys.argv[4])
