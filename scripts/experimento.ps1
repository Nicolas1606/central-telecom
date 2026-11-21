[CmdletBinding()]
param([ValidateRange(1,20)][int]$Repeticoes=3,[string]$Grupo="verification",[switch]$Juiz)
$ErrorActionPreference="Stop"
Push-Location (Split-Path $PSScriptRoot -Parent)
$previous = $env:AGENT_CONFIG
try {
    $python = ".\.venv\Scripts\python.exe"
    $base = "reports/runs/comparacao-" + [Guid]::NewGuid().ToString("N").Substring(0,8)
    $runs = @()
    foreach ($variant in @("generalista","especialistas","candidata")) {
        $design = if ($variant -eq "generalista") { "single" } else { "multi" }
        $env:AGENT_CONFIG = if ($variant -eq "candidata") { "config/candidate.json" } else { "config/agents.json" }
        $dest = Join-Path $base $variant
        $argsEval = @("main.py","evaluate","--mode","ollama","--design",$design,"--split",$Grupo,"--repeat",$Repeticoes,"--output",$dest)
        if ($Juiz) { $argsEval += "--judge" }
        & $python @argsEval
        if ($LASTEXITCODE -ne 0) { throw "Falha em $variant. Inspecione o resultado em $dest." }
        $runs += (Get-ChildItem $dest -Directory | Select-Object -First 1).FullName
    }
    & $python main.py compare $runs[0] $runs[1]
    if ($LASTEXITCODE -ne 0) { throw "Falha na comparação das arquiteturas." }
    & $python main.py compare $runs[1] $runs[2]
    if ($LASTEXITCODE -ne 0) { throw "Falha na comparação das configurações." }
} finally {
    $env:AGENT_CONFIG=$previous
    Pop-Location
}
