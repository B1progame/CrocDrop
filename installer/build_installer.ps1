Param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "[CrocDrop] Creating virtual environment..."
    python -m venv .venv
}

Write-Host "[CrocDrop] Installing requirements..."
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller

Write-Host "[CrocDrop] Building desktop bundle..."
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --name CrocDrop main.py

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    throw "Inno Setup not found. Install Inno Setup 6 and retry."
}

Write-Host "[CrocDrop] Building installer..."
& $iscc ".\installer\CrocDrop.iss" "/DMyAppVersion=$Version"

Write-Host "[CrocDrop] Installer created in .\installer_output"
