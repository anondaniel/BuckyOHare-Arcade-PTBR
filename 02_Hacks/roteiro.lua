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
    if not vistos[pc] then
      vistos[pc] = true
      print(string.format("quadro %d: leitura %06X PC=%06X A0=%08X A1=%08X A5=%08X A6=%08X",
        n, off, pc, cpu.state["A0"].value, cpu.state["A1"].value, cpu.state["A5"].value, cpu.state["A6"].value))
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
    elseif c:match("^sai") then manager.machine:exit()
    end
  end
end, "roteiro")
