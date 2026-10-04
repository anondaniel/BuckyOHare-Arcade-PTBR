"""Prévia colorida da placa (original x 04_Graficos/placa.txt), com a paleta
lida de uma captura do MAME. Uso: previa_placa.py captura.png saida.png
(a captura deve mostrar a placa original no canto x=298..361, y=64..111)."""
import sys

from PIL import Image

import sprites as S
from build_placa import le_placa


def paleta_da_captura(cap, orig):
    """Casa os pixels da captura com os índices do sprite original."""
    im = Image.open(cap).convert('RGB')
    melhor = None
    for ox in range(280, 320):
        for oy in range(50, 80):
            cores, ok = {}, 0
            for y in range(0, 50, 2):
                for x in range(0, 64, 2):
                    v = orig[y][x]
                    if v:
                        c = im.getpixel((ox + x, oy + y)) if ox + x < 384 and oy + y < 224 else None
                        if cores.setdefault(v, c) == c:
                            ok += 1
            if melhor is None or ok > melhor[0]:
                melhor = (ok, cores)
    return melhor[1]


def main():
    d = S.le()
    orig = S.sprite(d, 0x5020, 4, 4)
    pal = paleta_da_captura(sys.argv[1], orig)
    nova = [[0 if c == '.' else int(c, 16) for c in r] for r in le_placa()]
    Z = 5
    out = Image.new('RGB', (64 * Z * 2 + 20, 64 * Z), (90, 140, 60))
    for k, img in enumerate((orig, nova)):
        for y in range(64):
            for x in range(64):
                v = img[y][x]
                if v:
                    for yy in range(Z):
                        for xx in range(Z):
                            out.putpixel((k * (64 * Z + 20) + x * Z + xx, y * Z + yy),
                                         pal.get(v) or (255, 0, 255))
    out.save(sys.argv[2])


if __name__ == '__main__':
    main()
