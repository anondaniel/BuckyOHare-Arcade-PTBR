# Bucky O'Hare (arcade Konami, 1992): tradução PT-BR

Leia antes `C:\Projetos\CONTEXTO_GERAL_CLAUDE.md`.

## Qual versão

**A de fliperama (arcade) da Konami**: beat 'em up para até 4 jogadores. Confirmado pelo Daniel em
03/10/2026. **A versão de NES não interessa**: ele jogou e não gostou. No Switch dele existe um
`/roms/nes/Bucky O'Hare.nes`; ignore.

## O que temos

- O conjunto do arcade, versão **EAB** (mundial; no MAME/FBNeo é o conjunto **`bucky`**):
  - `00_Original\bucky\`: os arquivos soltos, como o Daniel trouxe (de `Downloads\bucky`);
  - `00_Original\bucky.zip`: o mesmo conjunto zipado, como o MAME e o FBNeo esperam.

  | Arquivo | Tamanho | CRC32 | Uso provável |
  |---|---|---|---|
  | 173eab01.q5 | 262144 | 7785AC8A | programa 68000 (bytes pares) |
  | 173eab02.q6 | 262144 | 9B45F122 | programa 68000 (bytes ímpares) |
  | 173a03.t5 | 131072 | CD724026 | |
  | 173a04.t6 | 131072 | 7DD54D6F | |
  | 173a05.t8 | 1048576 | D14333B4 | |
  | 173a06.t10 | 1048576 | 6541A34F | |
  | 173a07.f5 | 262144 | 4CDAEE71 | |
  | 173a08.b6 … 173a13.a10 | 6 × 2097152 | DCDDED95, C93697C4, 42FB0A0C, B0D747C4, 0FC2AD24, 4CF85439 | sprites |
  | bucky.nv | 128 | 6A5986F3 | EEPROM padrão |

  Confira os papéis de cada arquivo no driver do MAME (`moo.cpp`, conjunto `bucky`).
- Original em **inglês**. Juntando os dois arquivos do programa (byte de `q5`, byte de `q6`,
  alternados), o texto aparece em **ASCII legível**. Há uns 620 trechos, por exemplo:
  "FREEPLAY CREDIT CREDITS", nomes de inimigos ("AL NEGATOR", "TOAD BORG", "TERROR TOAD",
  "AIR MARSHALL", "KOMPLEX") e o menu de teste ("NEXT", "REPEAT", "BACK"). Bom sinal: dá para
  traduzir trocando o texto no programa, respeitando o tamanho de cada trecho ou repontando.
  Parte do texto pode estar em gráficos (tiles).

## Primeiros passos sugeridos

1. Rodar no MAME com o depurador (`-debug`) e achar onde ficam o texto e a fonte (ROMs de programa
   68000 e ROMs de tiles).
2. Ver se a fonte tem acentos. Se não tiver, desenhar as letras nos tiles livres.
3. Montar o pipeline do contexto geral: script que aplica a tradução sobre os arquivos do conjunto
   e gera um conjunto modificado (ou IPS por arquivo de ROM), sempre conferindo os CRCs.
4. No Switch, ele roda pelo RetroArch com FBNeo ou MAME. Confirme qual núcleo aceita o conjunto
   modificado (o FBNeo confere CRC; pode ser preciso usar um nome de conjunto diferente ou um arquivo
   de "hiscore/dat").

## Levantamento (03/10/2026)

Ferramentas: Python do venv `C:\Projetos\_ferramentas\venv` (Pillow, numpy). O
`pip install --user` no Python do sistema falha neste PC; use o venv.

- **Papéis das ROMs** (MAME `konami/moo.cpp`, `ROM_START( bucky )`):
  - `173eab01.q5`/`173eab02.q6`: programa 68000 (bytes pares/ímpares), 0x000000–0x07FFFF;
  - `173a03.t5`/`173a04.t6`: dados do 68000, em 0x200000;
  - `173a07.f5`: programa Z80 do som;
  - `173a05.t8`/`173a06.t10`: **tiles do K056832** (texto e cenários), 4 bits, `ROM_LOAD32_WORD`;
  - `173a10`–`173a13`: sprites (K053246);
  - `173a08`/`173a09`: amostras de som (K054539).
- **Todo o texto do jogo está em ASCII no programa** (≈12 KB): `02_Hacks\extrair_texto.py` lista
  280 trechos com endereço em `03_Traducao\original_en.txt`. Faixas principais:
  - 0x040000–0x040F00: testes, aviso legal, introdução da história, créditos, nomes das fases;
  - 0x040F00–0x046C00: falas entre as fases e dos chefes;
  - 0x046C00–: menu de serviço (dá para deixar em inglês).

  Códigos de controle prováveis: `[` (início de fala), `<` (quebra de linha), `]` (fim),
  `t`/`u`/`s` (pausas). Nos menus, o byte antes de cada trecho parece ser a posição. Falta
  confirmar no depurador, e achar os ponteiros que apontam para cada bloco (para poder aumentar
  frases).
- **Fonte:** 8x8, no começo da ROM de tiles (`02_Hacks\tiles2png.py`, imagem em
  `_extraido\tiles_0000.png`). Tem `0-9 : ; < = > ? A-Z` e alguns símbolos; **só maiúsculas,
  sem acentos**. Vamos precisar desenhar Á É Í Ó Ú Â Ê Ô Ã Õ Ç em tiles livres.
- **Texto em tiles** (precisa redesenhar): "INSERT COIN", "CONTINUE", "GAME OVER", "PRESS START",
  "SELECT", letras grandes do título e das fases (tiles ≈0x200–0x2FF).
- Mudar a ROM de tiles muda o CRC: o FBNeo recusa conjunto com CRC diferente. Plano provável:
  conjunto com outro nome (ex.: `buckyptbr`) só no MAME, ou um arquivo de patch para o RetroArch.
  Decidir antes de montar o pacote.

## Próximos passos

1. Instalar MAME neste PC; com o depurador, achar a rotina que imprime as falas e os ponteiros.
2. Tabela de caracteres com os acentos novos e codificador com limite de tamanho por trecho.
3. Build: original → conjunto traduzido + patch, conferindo os CRCs.

## Situação

Nada traduzido. Levantamento técnico feito em 03/10/2026. É o menor dos três (≈12 KB de texto).
