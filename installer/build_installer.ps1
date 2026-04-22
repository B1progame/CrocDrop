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

Write-Host "[CrocDrop] Preparing installer icon from assets/crocdrop_lock_logo.svg..."
$iconGenScript = @'
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

repo = Path.cwd()
svg_path = repo / "assets" / "crocdrop_lock_logo.svg"
ico_path = repo / "installer" / "CrocDrop.ico"
if not svg_path.exists():
    raise SystemExit(f"Missing logo SVG: {svg_path}")

app = QGuiApplication([])
renderer = QSvgRenderer(str(svg_path))
pix = QPixmap(256, 256)
pix.fill(Qt.GlobalColor.transparent)
painter = QPainter(pix)
renderer.render(painter)
painter.end()
ico_path.parent.mkdir(parents=True, exist_ok=True)
if not pix.save(str(ico_path), "ICO"):
    raise SystemExit(f"Failed to write ICO: {ico_path}")
print(f"Generated icon: {ico_path}")
'@
$tempScript = Join-Path $env:TEMP "crocdrop_generate_icon.py"
Set-Content -Path $tempScript -Value $iconGenScript -Encoding UTF8
try {
    & .\.venv\Scripts\python.exe $tempScript
    if ($LASTEXITCODE -ne 0) {
        throw "Icon generation failed with exit code $LASTEXITCODE."
    }
}
finally {
    if (Test-Path $tempScript) {
        Remove-Item $tempScript -Force
    }
}

Write-Host "[CrocDrop] Installing requirements..."
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "pip install -r requirements.txt failed with exit code $LASTEXITCODE."
}
.\.venv\Scripts\python.exe -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "pip install pyinstaller failed with exit code $LASTEXITCODE."
}

Write-Host "[CrocDrop] Building desktop bundle..."
# Prevent common lock failures from a running packaged app.
Get-Process -Name "CrocDrop" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

$distDir = Join-Path $repoRoot "dist\CrocDrop"
if (Test-Path $distDir) {
    for ($i = 0; $i -lt 3; $i++) {
        try {
            Remove-Item $distDir -Recurse -Force -ErrorAction Stop
            break
        }
        catch {
            Start-Sleep -Milliseconds 400
            if ($i -eq 2) {
                throw "Could not clean dist\CrocDrop. Close running app/windows using dist files and retry."
            }
        }
    }
}

.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --name CrocDrop --icon ".\installer\CrocDrop.ico" main.py
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path $distDir)) {
    throw "PyInstaller completed but dist\CrocDrop is missing."
}

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    throw "Inno Setup not found. Install Inno Setup 6 and retry."
}

Write-Host "[CrocDrop] Building installer..."
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputBase = "CrocDrop-Setup-$Version-$stamp"
& $iscc ".\installer\CrocDrop.iss" "/DMyAppVersion=$Version" "/DMyOutputBaseFilename=$outputBase"
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compile failed with exit code $LASTEXITCODE."
}

Write-Host "[CrocDrop] Installer created in .\installer_output"
