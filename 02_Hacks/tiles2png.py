"""Converte as ROMs de tiles do K056832 (173a05.t8 + 173a06.t10) em PNG.
Uso: tiles2png.py saida.png [primeiro_tile] [quantidade] [tiles_por_linha]

Layout (MAME, moo.cpp): ROM_LOAD32_WORD, t8 nas palavras pares e t10 nas
ímpares. Cada tile 8x8 tem 32 bytes, 4 bytes por linha, pixels de 4 bits
empacotados na ordem de nibbles 2,3,0,1,6,7,4,5 (nibble par = 4 bits altos).
A fonte 8x8 (0-9, símbolos, A-Z, só maiúsculas, sem acentos) fica no tile 0.
"""
import os
import sys

from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(RAIZ, '00_Original', 'bucky')
ORDEM_X = (2, 3, 0, 1, 6, 7, 4, 5)
CINZA = [v for i in range(16) for v in (i * 17,) * 3]


def tiles():
    a = open(os.path.join(ORIG, '173a05.t8'), 'rb').read()
    b = open(os.path.join(ORIG, '173a06.t10'), 'rb').read()
    d = bytearray(len(a) * 2)
    for i in range(0, len(a), 2):
        d[i * 2:i * 2 + 2] = a[i:i + 2]
        d[i * 2 + 2:i * 2 + 4] = b[i:i + 2]
    return d


def main():
    saida = sys.argv[1]
    ini = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
    qtd = int(sys.argv[3], 0) if len(sys.argv) > 3 else 1024
    larg = int(sys.argv[4]) if len(sys.argv) > 4 else 32
    d = tiles()
    img = Image.new('P', (larg * 8, (qtd + larg - 1) // larg * 8))
    img.putpalette(CINZA)
    pix = img.load()
    for t in range(qtd):
        base = (ini + t) * 32
        ox, oy = (t % larg) * 8, (t // larg) * 8
        for y in range(8):
            for x, k in enumerate(ORDEM_X):
                byte = d[base + y * 4 + k // 2]
                pix[ox + x, oy + y] = byte >> 4 if k % 2 == 0 else byte & 15
    img.save(saida)


if __name__ == '__main__':
    main()
