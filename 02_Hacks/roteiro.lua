-- Roteiro de teste para o MAME (-autoboot_script). Lê os comandos do arquivo
-- indicado na variável de ambiente ROTEIRO, uma linha por comando:
--   <quadro> aperta <porta> <campo> [quadros]   (padrão: 6 quadros)
--   <quadro> foto
--   <quadro> rastreia <ini_hex> <fim_hex>        (mostra o PC de quem lê a faixa)
--   <quadro> sai
-- Ex.: "400 aperta :IN0 Coin 1" / "460 aperta :P1_P3 1 Player Start"
-- Nomes de campo com espaço: tudo depois da porta até um número final opcional.

local cmds = {}
for linha in io.lines(os.getenv("ROTEIRO")) do
  local q, resto = linha:match("^%s*(%d+)%s+(.+)$")
  if q then
    cmds[tonumber(q)] = cmds[tonumber(q)] or {}
    table.insert(cmds[tonumber(q)], resto)
  end
end

local cpu = manager.machine.devices[":maincpu"]
local soltar = {}
local taps = {}
local n = 0

local function aperta(resto)
  local porta, campo = resto:match("^aperta%s+(%S+)%s+(.+)$")
  local dur = 6
  local c, d = campo:match("^(.-)%s+(%d+)$")
  if c and manager.machine.ioport.ports[porta].fields[c] then campo, dur = c, tonumber(d) end
  local f = manager.machine.ioport.ports[porta].fields[campo]
  f:set_value(1)
  table.insert(soltar, {n + dur, f})
end

local function rastreia(resto)
  local ini, fim = resto:match("rastreia%s+(%x+)%s+(%x+)")
  ini, fim = tonumber(ini, 16), tonumber(fim, 16)
  local vistos = {}
  local t = cpu.spaces["program"]:install_read_tap(ini, fim, "rastro" .. #taps, function(off, data, mask)
    local pc = cpu.state["PC"].value
    local k = pc .. ":" .. off
    if not vistos[k] then
      vistos[k] = true
      print(string.format("quadro %d: leitura %06X PC=%06X A0=%08X A1=%08X A5=%08X A6=%08X",
        n, off, pc, cpu.state["A0"].value, cpu.state["A1"].value, cpu.state["A5"].value, cpu.state["A6"].value))
    end
    return data
  end)
  table.insert(taps, t)
end

-- <quadro> escritas <ini_hex> <fim_hex>: mostra PC, endereço e valor de cada
-- escrita nova (combinação PC+endereço) na faixa
local function escritas(resto)
  local ini, fim = resto:match("escritas%s+(%x+)%s+(%x+)")
  ini, fim = tonumber(ini, 16), tonumber(fim, 16)
  local vistos = {}
  local t = cpu.spaces["program"]:install_write_tap(ini, fim, "escrita" .. #taps, function(off, data, mask)
    local pc = cpu.state["PC"].value
    local k = pc .. ":" .. off .. ":" .. data
    if not vistos[k] then
      vistos[k] = true
      print(string.format("quadro %d: escrita %06X = %04X PC=%06X", n, off, data, pc))
    end
    return data
  end)
  table.insert(taps, t)
end

emu.register_frame_done(function()
  n = n + 1
  for i = #soltar, 1, -1 do
    if soltar[i][1] <= n then soltar[i][2]:set_value(0); table.remove(soltar, i) end
  end
  for _, c in ipairs(cmds[n] or {}) do
    if c:match("^aperta") then aperta(c)
    elseif c:match("^foto") then manager.machine.video:snapshot()
    elseif c:match("^rastreia") then rastreia(c)
    elseif c:match("^escritas") then escritas(c)
    elseif c:match("^chama") then
      -- <quadro> chama <endereço_hex>: só para teste, faz um "jsr" na rotina
      -- (empilha o PC atual e desvia; a rotina volta para onde estava)
      local a = tonumber(c:match("chama%s+(%x+)"), 16)
      local sp = cpu.state["SP"].value - 4
      cpu.spaces["program"]:write_u32(sp, cpu.state["PC"].value)
      cpu.state["SP"].value = sp
      cpu.state["PC"].value = a
    elseif c:match("^despeja") then
      -- <quadro> despeja <ini_hex> <tamanho_hex> <arquivo>: grava a memória num arquivo
      local a, t, arq = c:match("despeja%s+(%x+)%s+(%x+)%s+(.+)$")
      a, t = tonumber(a, 16), tonumber(t, 16)
      local f = io.open(arq, "wb")
      for i = 0, t - 1 do f:write(string.char(cpu.spaces["program"]:read_u8(a + i))) end
      f:close()
    elseif c:match("^poke") then
      -- <quadro> poke <endereço_hex> <byte_hex>: escreve um byte na memória
      local a, v = c:match("poke%s+(%x+)%s+(%x+)")
      cpu.spaces["program"]:write_u8(tonumber(a, 16), tonumber(v, 16))
    elseif c:match("^sai") then manager.machine:exit()
    end
  end
end, "roteiro")
