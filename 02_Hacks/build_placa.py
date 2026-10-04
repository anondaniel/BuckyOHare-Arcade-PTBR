"""Grava a placa traduzida (04_Graficos/placa.txt) nas ROMs de sprites:
quadro 0x5020 como está e quadro 0x5010 com 9->B e D->F (a placa pisca
trocando essas cores)."""
import os

import sprites as S

PLACA = os.path.join(S.RAIZ, '04_Graficos', 'placa.txt')
QUADROS = {0x5020: {}, 0x5010: {'9': 'B', 'D': 'F'}}
# Sprite 1x2 (0x5030/0x5031) que mostrava a ponta do "y" de "Hurry" à direita:
# na placa nova ele fica vazio.
APAGAR = (0x5030, 0x5032, 0x5031, 0x5033)


def le_placa():
    with open(PLACA, encoding='utf-8') as f:
        linhas = [l.rstrip('\n') for l in f if not l.startswith(';') and l.strip()]
    if len(linhas) != 64 or any(len(l) != 64 for l in linhas):
        raise ValueError('placa.txt: são 64 linhas de 64 pontos')
    return linhas


def aplica(d):
    linhas = le_placa()
    for codigo, troca in QUADROS.items():
        img = [[0 if c == '.' else int(troca.get(c, c), 16) for c in l] for l in linhas]
        for by in range(4):
            for bx in range(4):
                S.grava_bloco(d, codigo + S.XOFS[bx] + S.YOFS[by],
                              [r[bx * 16:bx * 16 + 16] for r in img[by * 16:by * 16 + 16]])
    for n in APAGAR:
        S.grava_bloco(d, n, [[0] * 16 for _ in range(16)])
