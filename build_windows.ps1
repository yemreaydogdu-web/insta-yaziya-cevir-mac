$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (!(Test-Path ".venv")) {
    py -3.11 -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }

pyinstaller --noconfirm --clean ZelkaScribe-Windows.spec

Write-Host ""
Write-Host "Bitti:"
Write-Host "  dist\Zelka Scribe\Zelka Scribe.exe"
