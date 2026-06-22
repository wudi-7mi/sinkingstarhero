$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $root '.venv'
$name = 'SinkingStarHero'

if (-not (Test-Path -LiteralPath $venv)) {
    py -3.10 -m venv $venv
}

& (Join-Path $venv 'Scripts\python.exe') -m pip install --upgrade pip pyinstaller
& (Join-Path $venv 'Scripts\python.exe') -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name $name `
    --distpath (Join-Path $root 'build') `
    --workpath (Join-Path $root 'build_work') `
    --specpath (Join-Path $root 'build_spec') `
    (Join-Path $root 'src\sinking_star_light_trainer.py')

Write-Host "Built: $(Join-Path $root "build\$name.exe")"
