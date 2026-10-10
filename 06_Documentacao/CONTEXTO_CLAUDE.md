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

## Como está montado (03/10/2026)

Ferramentas: Python do venv `C:\Projetos\_ferramentas\venv` (Pillow, numpy); MAME 0.289 em
`C:\Projetos\_ferramentas\mame` (tem `unidasm.exe` para desmontar 68000). O `pip install --user`
no Python do sistema falha neste PC; use o venv.

- **Papéis das ROMs** (MAME `konami/moo.cpp`, `ROM_START( bucky )`): `173eab01.q5`/`173eab02.q6`
  programa 68000 (pares/ímpares); `173a03.t5`/`t6` dados em 0x200000; `173a07.f5` Z80; `173a05.t8`/
  `173a06.t10` tiles do K056832 (texto); `173a10`–`a13` sprites; `173a08`/`a09` som.
- **Build:** `02_Hacks\build.py` lê `03_Traducao\traducao.txt` (formato no cabeçalho e em
  `original_en.txt`), valida, grava o texto novo no espaço livre (0x70A00), troca só os ponteiros,
  aplica os patches de código, desenha os acentos (`04_Graficos\acentos.txt`), compensa a soma
  de cada chip (o jogo confere no boot) e gera em `01_ROM`: o conjunto (`bucky\`, `bucky.zip`),
  os IPS (`patch\`), o zip para o FBNeo (`fbneo_patched\bucky.zip`) e o pacote
  `Bucky_OHare_PTBR_v0.9.zip` (LEIAME gerado de `06_Documentacao\LEIAME_modelo.txt`).
  - `build.py --ida-e-volta`: o codificador reproduz o original byte a byte.
  - `build.py --vitrine msg.11=msg.39,cena.0.0=cena.5.1`: build de teste em `_teste\vitrine` para
    ver textos do fim do jogo nas telas do começo (seleção, "APERTE START", 1ª cena, fase 1).
- **Testes:** `02_Hacks\roteiro.lua` no MAME sem janela (`-video none -autoboot_script`, variável
  `ROTEIRO` com o arquivo de comandos: `aperta`, `foto`, `rastreia`, `escritas`, `poke`, `chama`).
  Ficha só funciona depois do boot (quadro ~700); start ~900; botão 1 ~1000 escolhe o personagem.
  `02_Hacks\previa_fonte.py` mostra palavras com a fonte e os acentos, sem o MAME.

## Formatos (detalhes em `02_Hacks\buckylib.py`)

- **Mensagens** (80 ponteiros em 0x402E0): registros `0018LLCC` (VRAM; linha, coluna×4) + texto +
  `[`/`]`. Cada registro precisa começar em endereço par. Duas rotinas usam a mesma tabela:
  - fonte pequena 8x8 (0x1E16): tile = byte − 0x30; espaço/pontuação nos tiles 0xF0–0xFF;
  - **fonte grande** 16x16 (0x1E9C), msgs 11, 12, 19, 20, 32–39: tabela por caractere; o build
    trocou a tabela de 1 byte (0x1F2E) por uma de 16 bits (0x7FA00, rotina em 0x7F980) para usar
    os tiles novos de Á Ã Ç e hífen. Só tem A–Z, 0–9, `! . ?`, Á Ã Ç e hífen.
- **Cenas** (8 ponteiros em 0x79C6, cada um para N páginas): `[` caixa, `<` 2ª linha, `u t s r`
  pausas. 43 letras × 2 linhas. **Chefes** (16 ponteiros em 0x79E6): `NOME:` + caixas de 23 × 2.
- **Créditos do canto** (0x2600, "FREEPLAY/CREDIT/CREDITS"): o build realoca para campos de 9
  (bloco `@hud.creditos`).
- **Msg 28** ("INICIAR 1 FICHA(S)"): o número e o "S" são escritos pelo código em 0x7126; o build
  muda essas colunas (conferido com `chama 70EC` + `escritas`).
- Tiles livres usados: 0x60–0x67 e 0x70–0x73 (acentos pequenos), 0x68–0x6F e 0x78–0x7F (grandes).
  O logotipo da Konami usa os bytes 0x70–0x8D (tiles 0x40–0x5D): não mexer.

## Situação

**Versão 1.0 (03/10/2026), testada no MAME:** boot (teste de ROM OK), introdução, título,
seleção, as 8 cenas e os 8 nomes de fase (vitrine), placar, placa "ANDA LOGO!", créditos e as
falas dos 16 chefes. As falas foram forçadas com `seguro 7B2A <chefe>` + `seguro 7B66 0 80CA8` no
roteiro (trecho na RAM que salva registradores e devolve a página da VRAM). No começo da fase, o
jogo apaga a página de texto logo depois da 1ª caixa, então as 2ªs caixas dos chefes 6, 7, 8, 13 e
14 foram vistas com `_teste\tira_caixa.py` + `BUCKY_TRADUCAO` (build de teste sem a 1ª caixa).
Pacote: `01_ROM\Bucky_OHare_PTBR_v1.0.zip`.

**Projeto concluído em 04/10/2026.** O Daniel copiou a versão final para o Switch (RetroArch +
FBNeo: `/retroarch/cores/system/fbneo/patched/bucky.zip`, com o bucky.zip original na pasta de
ROMs e "Allow patched romsets" ativado) e fechou o projeto. "1UP" continua em inglês (sprite).

**10/10/2026:** o Daniel zerou o jogo com a tradução, tudo certo. Publicado no GitHub
(`anondaniel/BuckyOHare-Arcade-PTBR`, release v1.0 com o pacote) e divulgado no
romhacking.net.br, como o Yu Yu: https://www.romhacking.net.br/index.php?topic=3540.0
(Lançamentos, "[ARCADE] Bucky O'Hare [PT-BR]"). Telas para divulgação em
`06_Documentacao\telas\` (mosaico.png + 9 telas em 2x).