"""Prévia ampliada de palavras com a fonte do jogo + 04_Graficos/acentos.txt,
sem precisar do build nem do MAME. Uso: previa_fonte.py saida.png "PALAVRA" ...
"""
import sys

from PIL import Image

import buckylib as B
from build import le_acentos

ORDEM_X = (2, 3, 0, 1, 6, 7, 4, 5)
CORES = {0: (16, 24, 120), 1: (255, 255, 255), 2: (120, 120, 160)}
Z = 6


def glifo_rom(d, t):
    g = []
    for y in range(8):
        lin = []
        for k in ORDEM_X:
            b = d[t * 32 + y * 4 + k // 2]
            lin.append(b >> 4 if k % 2 == 0 else b & 15)
        g.append(lin)
    return g


def main():
    d = B.tiles()
    novos = {c: [[0 if ch == '.' else int(ch, 16) for ch in r] for r in g]
             for c, g in le_acentos()[0].items()}
    frases = sys.argv[2:]
    larg = max(len(f) for f in frases)
    img = Image.new('RGB', (larg * 8 * Z, len(frases) * 10 * Z), CORES[0])
    px = img.load()
    for n, f in enumerate(frases):
        for i, c in enumerate(f):
            g = novos[c] if c in novos else glifo_rom(d, (B.codigo(c) - 0x30) & 0xFF)
            for y in range(8):
                for x in range(8):
                    v = g[y][x]
                    if v:
                        cor = CORES.get(v, (255, 200, 0))
                        for yy in range(Z):
                            for xx in range(Z):
                                px[(i * 8 + x) * Z + xx, (n * 10 + 1 + y) * Z + yy] = cor
    img.save(sys.argv[1])


if __name__ == '__main__':
    main()
