"""Extrai o texto do programa original para 03_Traducao/original_en.txt, no
mesmo formato que o build lê em 03_Traducao/traducao.txt.

Formato:
    ; comentário
    @msg.N          mensagem N da tabela de 0x402E0; uma linha por registro:
    LL CC TEXTO       LL = linha da tela (hex), CC = coluna (decimal) ou "c"
                      para centralizar
    @cena.S.P       página P da cena S: cada caixa começa com "[", a linha
                    seguinte da mesma caixa vem sem "["
    @chefe.N        fala do chefe N: 1ª linha = nome (até o ":"), depois caixas
Entre chaves vão bytes copiados sem conversão: pausas ({t}, {uus }), gráficos
({`} = ©) e espaços no fim da linha.
"""
import os

import buckylib as B

SAIDA = os.path.join(B.RAIZ, '03_Traducao', 'original_en.txt')


def extrai(p):
    """-> lista de (identificador, linhas)."""
    blocos = []
    for i in range(B.N_MSG):
        o = B.L(p, B.TAB_MSG + 4 * i)
        if o:
            blocos.append((f'msg.{i}', [f'{lin:02X} {col} {B.bytes_para_texto(bs)}'
                                        for lin, col, bs in B.le_mensagem(p, o)]))
    for s in range(B.N_CENAS):
        lista = B.L(p, B.TAB_CENAS + 4 * s)
        n = (B.L(p, lista) - lista) // 4
        for k in range(n):
            pag = B.le_ate_fim(p, B.L(p, lista + 4 * k))
            blocos.append((f'cena.{s}.{k}', B.paginas_para_linhas(pag[:-1])))
    for c in range(B.N_CHEFES):
        bs = B.le_ate_fim(p, B.L(p, B.TAB_CHEFES + 4 * c))[:-1]
        nome, resto = bs.split(b':', 1)
        pre, _, caixas = resto.partition(b'[')
        linha_nome = B.bytes_para_texto(nome + b':') + ('{' + pre.decode('latin-1') + '}' if pre else '')
        blocos.append((f'chefe.{c}', [linha_nome] + B.paginas_para_linhas(b'[' + caixas)))
    return blocos


def main():
    p = B.programa()
    blocos = extrai(p)
    with open(SAIDA, 'w', encoding='utf-8', newline='\n') as f:
        cab = __doc__.split('\n\n', 1)[1].strip()
        f.write(''.join(f'; {l}'.rstrip() + '\n' for l in cab.splitlines()))
        for ident, linhas in blocos:
            f.write(f'\n@{ident}\n' + ''.join(l + '\n' for l in linhas))
    print(f'{len(blocos)} blocos -> {SAIDA}')


if __name__ == '__main__':
    main()
