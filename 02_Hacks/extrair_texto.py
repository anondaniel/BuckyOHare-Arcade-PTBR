"""Junta o programa 68000 do Bucky (q5 = bytes pares, q6 = ímpares) e lista os
trechos de texto ASCII com o endereço, em 03_Traducao/original_en.txt.

Levantamento inicial (03/10/2026); o formato exato dos códigos de controle
ainda não foi confirmado no depurador:
  '['  início de fala/linha   '<'  quebra de linha   ']'  fim do bloco
  't', 'u', 's' logo antes de '[' ou ']' parecem pausas
  O byte antes de cada trecho dos menus/créditos parece ser a posição X.
"""
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(RAIZ, '00_Original', 'bucky')
SAIDA = os.path.join(RAIZ, '03_Traducao', 'original_en.txt')

# Faixas do programa com texto (endereço da CPU = deslocamento no programa).
FAIXAS = [
    (0x0025F0, 0x002960, 'créditos e nomes de inimigos'),
    (0x0196A0, 0x0198F0, 'ranking'),
    (0x040000, 0x040F00, 'testes, aviso legal, introdução, créditos'),
    (0x040F00, 0x046C00, 'história (falas entre fases e dos chefes)'),
    (0x046C00, 0x048000, 'menu de serviço'),
]


def programa():
    a = open(os.path.join(ORIG, '173eab01.q5'), 'rb').read()
    b = open(os.path.join(ORIG, '173eab02.q6'), 'rb').read()
    p = bytearray(len(a) * 2)
    p[0::2], p[1::2] = a, b
    return bytes(p)


def main():
    prog = programa()
    n = 0
    with open(SAIDA, 'w', encoding='utf-8', newline='\n') as out:
        for ini, fim, desc in FAIXAS:
            out.write(f'# {ini:06X}-{fim:06X} {desc}\n\n')
            for m in re.finditer(rb'[ -~]{4,}', prog[ini:fim]):
                t = m.group().decode('ascii')
                if not re.search(r'[A-Z]{2}', t):
                    continue
                out.write(f'@{ini + m.start():06X} ({len(t)})\n{t}\n\n')
                n += 1
    print(f'{n} trechos -> {SAIDA}')


if __name__ == '__main__':
    main()
