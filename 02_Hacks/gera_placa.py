"""Gera o rascunho da placa "Hurry Up!" traduzida (sprite 64x64, códigos 0x5010
e 0x5020) no estilo da original e grava em 04_Graficos/placa.txt, que o build
usa (e que pode ser retocado à mão). Uso: gera_placa.py [fonte.ttf [tamanho [espaço [estreita]]]]

Camadas da original (quadro 0x5020; o 0x5010 troca 9->B e D->F):
    9 face   D realce da face   E borda da face
    C relevo (para baixo/esquerda)   7 borda do relevo
    3 contorno   5 contorno de fora
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, '04_Graficos', 'placa.txt')
LINHAS = [('ANDA', 0, 3), ('LOGO!', 1, 26)]    # texto, deslocamento x do centro, topo
TAM = 19                                        # Arial Black 19, condensada a 68%
ESPACO = 1                                       # pixels entre letras
INCLINA = 0.25                                  # itálico (pixels por linha, a partir da base)
ESTREITA = 0.68                                 # largura relativa (condensa as letras)
ENGROSSA = 0                                    # pixels a mais em volta das letras
RELEVO = [(-1, 1), (-2, 2), (-2, 3)]           # deslocamentos do relevo


def mascara(fonte):
    f = ImageFont.truetype(fonte, TAM)
    out = [[False] * 64 for _ in range(64)]
    for texto, cx, topo in LINHAS:
        x0, y0, x1, y1 = f.getbbox(texto)
        larg_letras = [f.getbbox(c)[2] - f.getbbox(c)[0] for c in texto]
        img = Image.new('L', (sum(larg_letras) + ESPACO * len(texto) + 2, y1 - y0 + 2), 0)
        dr = ImageDraw.Draw(img)
        x = 1
        for c, lc in zip(texto, larg_letras):
            dr.text((x - f.getbbox(c)[0], 1 - y0), c, font=f, fill=255)
            x += lc + ESPACO
        img = img.resize((round(img.width * ESTREITA), img.height), Image.LANCZOS)
        w, h = img.size
        larg = w + round(h * INCLINA)
        ox = (64 - larg) // 2 + cx
        for y in range(h):
            dx = round((h - 1 - y) * INCLINA)     # itálico: o alto da linha vai para a direita
            for x in range(w):
                if img.getpixel((x, y)) > 110:
                    X, Y = ox + x + dx, topo + y
                    if 0 <= X < 64 and 0 <= Y < 64:
                        out[Y][X] = True
    for _ in range(ENGROSSA):
        out = [[out[y][x] or any(viz(out, x, y)) for x in range(64)] for y in range(64)]
    return out


def viz(m, x, y, n8=False):
    pts = [(1, 0), (-1, 0), (0, 1), (0, -1)] + ([(1, 1), (1, -1), (-1, 1), (-1, -1)] if n8 else [])
    for dx, dy in pts:
        if 0 <= x + dx < 64 and 0 <= y + dy < 64 and m[y + dy][x + dx]:
            yield dx, dy


def colore(face):
    relevo = [[False] * 64 for _ in range(64)]
    for y in range(64):
        for x in range(64):
            if face[y][x]:
                for dx, dy in RELEVO:
                    if 0 <= x + dx < 64 and 0 <= y + dy < 64:
                        relevo[y + dy][x + dx] = True
    corpo = [[face[y][x] or relevo[y][x] for x in range(64)] for y in range(64)]
    cont1 = [[not corpo[y][x] and any(viz(corpo, x, y, True)) for x in range(64)] for y in range(64)]
    tudo1 = [[corpo[y][x] or cont1[y][x] for x in range(64)] for y in range(64)]
    cont2 = [[not tudo1[y][x] and any(viz(tudo1, x, y, True)) for x in range(64)] for y in range(64)]
    g = [['.'] * 64 for _ in range(64)]
    for y in range(64):
        for x in range(64):
            if face[y][x]:
                borda = any(not face[y + dy][x + dx] for dx, dy in
                            [(1, 0), (-1, 0), (0, 1), (0, -1)]
                            if 0 <= x + dx < 64 and 0 <= y + dy < 64)
                if borda:
                    g[y][x] = 'E'
                elif not face[y - 2][x]:
                    g[y][x] = 'D'            # realce perto da borda de cima/esquerda
                else:
                    g[y][x] = '9'
            elif relevo[y][x]:
                g[y][x] = '7' if any(not corpo[y + dy][x + dx] for dx, dy in [(-1, 0), (0, 1)]
                                     if 0 <= x + dx < 64 and 0 <= y + dy < 64) else 'C'
            elif cont1[y][x]:
                g[y][x] = '3'
            elif cont2[y][x]:
                g[y][x] = '5'
    return [''.join(r) for r in g]


def main():
    global TAM, ESPACO, ESTREITA
    fonte = sys.argv[1] if len(sys.argv) > 1 else r'C:\Windows\Fonts\ariblk.ttf'
    if len(sys.argv) > 2:
        TAM = int(sys.argv[2])
    if len(sys.argv) > 3:
        ESPACO = int(sys.argv[3])
    if len(sys.argv) > 4:
        ESTREITA = float(sys.argv[4])
    linhas = colore(mascara(fonte))
    with open(SAIDA, 'w', encoding='utf-8', newline='\n') as f:
        f.write('; Placa "Hurry Up!" -> "ANDA LOGO!" (sprite 64x64, quadro 0x5020).\n'
                '; Gerada por 02_Hacks/gera_placa.py e retocável à mão. O build grava\n'
                '; este desenho em 0x5020 e, trocando 9->B e D->F, em 0x5010.\n'
                '; 9 face, D realce, E borda, C relevo, 7 borda do relevo, 3/5 contorno.\n')
        f.write('\n'.join(linhas) + '\n')
    cols = [x for l in linhas for x, c in enumerate(l) if c != '.']
    rows = [y for y, l in enumerate(linhas) if l.strip('.')]
    print(f'-> {SAIDA}  colunas {min(cols)}-{max(cols)}, linhas {min(rows)}-{max(rows)}')
    if min(cols) == 0 or max(cols) == 63 or min(rows) == 0:
        print('ATENÇÃO: o desenho encosta na borda do sprite')


if __name__ == '__main__':
    main()
