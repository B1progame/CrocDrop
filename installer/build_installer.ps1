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
.\.venv\Scripts\python.exe -c $iconGenScript

Write-Host "[CrocDrop] Installing requirements..."
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller

Write-Host "[CrocDrop] Building desktop bundle..."
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --name CrocDrop --icon ".\installer\CrocDrop.ico" main.py

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    throw "Inno Setup not found. Install Inno Setup 6 and retry."
}

Write-Host "[CrocDrop] Building installer..."
& $iscc ".\installer\CrocDrop.iss" "/DMyAppVersion=$Version"

Write-Host "[CrocDrop] Installer created in .\installer_output"
