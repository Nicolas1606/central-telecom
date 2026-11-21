[CmdletBinding()]
param([ValidateSet("demo","ollama")][string]$Modo="demo")
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    $python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $local314 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"
        if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
        elseif (Test-Path $local314) { & $local314 -m venv .venv }
        else { & python -m venv .venv }
        if ($LASTEXITCODE -ne 0) { throw "A criação do ambiente falhou." }
    }
    & $python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências." }
    $env:AGENT_MODE = $Modo
    & $python main.py serve
} finally { Pop-Location }
