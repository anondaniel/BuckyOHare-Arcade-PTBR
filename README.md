# Bucky O'Hare (arcade) — Tradução PT-BR

Tradução para português brasileiro de **Bucky O'Hare** (fliperama, Konami, 1992), o beat 'em up
para até 4 jogadores baseado no desenho animado. Conjunto `bucky` do MAME/FBNeo (versão mundial EAB).

Este projeto é gratuito, feito por fã para fãs, sem qualquer afiliação com a Konami ou os
detentores dos direitos autorais. Não distribuímos a ROM — só o código-fonte e os patches IPS
que você aplica no seu próprio conjunto.

## O que foi traduzido

- Toda a história: introdução, cenas entre as fases e falas dos 16 chefes.
- Nomes das fases, tela de seleção, telas de aviso e de direitos autorais, fichas e créditos
  (CRÉDITO/CRÉDITOS), dicas de botões e créditos finais.
- Placar redesenhado: PÕE FICHA, APERTE (START), ESCOLHA, CONTINUAR e FIM DE JOGO; a placa
  "Hurry Up!" virou "ANDA LOGO!".
- A fonte do jogo ganhou as letras acentuadas do português (Á À Â Ã É Ê Í Ó Ô Õ Ú Ç), também na
  fonte grande (Á Ã Ç e hífen).

Continuam em inglês: o botão START (nome do botão), "1UP", o menu de serviço (teste da máquina) e
os nomes próprios dos personagens.

O teste de ROM que o jogo faz ao ligar ("RAM ROM CHECK") continua dando OK: o build compensa a
soma de verificação de cada chip alterado.

## Como aplicar

1. Tenha o conjunto `bucky` (Bucky O'Hare, versão mundial EAB). Os 8 arquivos alterados
   precisam ter estes CRC32 originais:

   | Arquivo | Tamanho | CRC32 |
   |---|---|---|
   | 173eab01.q5 | 262144 | 7785AC8A |
   | 173eab02.q6 | 262144 | 9B45F122 |
   | 173a05.t8 | 1048576 | D14333B4 |
   | 173a06.t10 | 1048576 | 6541A34F |
   | 173a10.b8 | 2097152 | 42FB0A0C |
   | 173a11.a8 | 2097152 | B0D747C4 |
   | 173a12.b10 | 2097152 | 0FC2AD24 |
   | 173a13.a10 | 2097152 | 4CF85439 |

2. Baixe o pacote mais recente na aba [Releases](../../releases).
3. Descompacte o seu `bucky.zip`, aplique cada `.ips` da pasta `patch` no arquivo de mesmo nome
   (Floating IPS, Lunar IPS etc.) e compacte tudo de novo como `bucky.zip`.

O `LEIAME.txt` do pacote traz o passo a passo completo, os hashes (CRC32, MD5, SHA-1) antes e
depois do patch, e como jogar no **MAME** e no **RetroArch com FBNeo** (inclusive no Switch,
usando a pasta `fbneo/patched` e a opção "Allow patched romsets").

## Como compilar a partir do código-fonte

Requer Python 3 com Pillow e numpy, e o conjunto original em `00_Original/bucky.zip`.

```
python 02_Hacks/build.py
```

O build parte sempre do conjunto original, valida a tradução (recusa texto que não cabe ou letra
que a fonte não tem) e gera em `01_ROM/`: o conjunto traduzido, os IPS, o zip para o FBNeo e o
pacote com o LEIAME. `build.py --ida-e-volta` confere que o codificador reproduz o original byte a
byte.

## Estrutura do repositório

```
02_Hacks/         build e ferramentas (Python) + roteiro de teste do MAME (Lua)
03_Traducao/      texto original em inglês e a tradução
04_Graficos/      acentos da fonte, placar e placa "ANDA LOGO!" (desenhos em texto)
06_Documentacao/  modelo do LEIAME e notas técnicas do projeto
```

## Ferramentas

- `build.py` — monta o conjunto traduzido: texto em espaço livre com ponteiros novos, patches de
  código (tabela de 16 bits para a fonte grande, contagem de fichas), acentos, placar, soma dos
  chips, IPS e pacote.
- `buckylib.py` — formatos do jogo (mensagens, cenas, falas dos chefes, fontes 8x8 e 16x16).
- `extrair_texto.py` — extrai todo o texto do programa 68000 para `original_en.txt`.
- `gera_placa.py` / `build_placa.py` / `sprites.py` — redesenho dos sprites do placar e da placa.
- `tiles2png.py`, `previa_fonte.py`, `previa_placa.py` — prévias de tiles, fontes e placas.
- `roteiro.lua` — testes automáticos no MAME sem janela (aperta botões, tira fotos, força cenas).

## Créditos

Tradução e hacking: **Daniel Figueira**.

Bucky O'Hare © 1992 Konami; personagens © Continuity Graphic Associates, Inc.
