Param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($Version)) {
    try {
        $Version = python -c "from app.version import APP_VERSION; print(APP_VERSION)"
        $Version = ($Version | Select-Object -First 1).ToString().Trim()
    }
    catch {
        $Version = "1.3.1"
    }
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "[CrocDrop] Creating virtual environment..."
    python -m venv .venv
}

if (-not (Test-Path ".\installer\CrocDrop.ico")) {
Write-Host "[CrocDrop] Preparing installer icon from assets/crocdrop_lock_logo.svg..."
$iconGenScript = @'
from pathlib import Path
import io
import struct

from PySide6.QtCore import Qt
from PySide6.QtCore import QBuffer, QByteArray
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer

repo = Path.cwd()
svg_path = repo / "assets" / "crocdrop_lock_logo.svg"
ico_path = repo / "installer" / "CrocDrop.ico"
if not svg_path.exists():
    raise SystemExit(f"Missing logo SVG: {svg_path}")

app = QGuiApplication([])
renderer = QSvgRenderer(str(svg_path))
sizes = [16, 24, 32, 48, 64, 128, 256]
icon = QIcon()
png_blobs = []
for size in sizes:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    icon.addPixmap(pix)
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    ok = pix.save(buffer, "PNG")
    buffer.close()
    if not ok:
        raise SystemExit(f"Failed to render PNG for size {size}")
    png_blobs.append(bytes(ba))

# Write ICO container with PNG frames (multi-size icon).
count = len(sizes)
header = struct.pack("<HHH", 0, 1, count)
entries = []
offset = 6 + (16 * count)
for size, blob in zip(sizes, png_blobs):
    w = 0 if size >= 256 else size
    h = 0 if size >= 256 else size
    entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(blob), offset)
    entries.append(entry)
    offset += len(blob)

ico_path.parent.mkdir(parents=True, exist_ok=True)
with ico_path.open("wb") as f:
    f.write(header)
    for entry in entries:
        f.write(entry)
    for blob in png_blobs:
        f.write(blob)
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
} else {
    Write-Host "[CrocDrop] Reusing existing installer icon .\installer\CrocDrop.ico"
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

$buildDir = Join-Path $repoRoot "build"
$distRoot = Join-Path $repoRoot "dist"
$distDir = Join-Path $repoRoot "dist\CrocDrop"
$installerOutputDir = Join-Path $repoRoot "installer_output"
$specPath = Join-Path $repoRoot "CrocDrop.spec"
foreach ($path in @($buildDir, $distRoot, $installerOutputDir)) {
    if (Test-Path $path) {
        for ($i = 0; $i -lt 3; $i++) {
            try {
                Remove-Item $path -Recurse -Force -ErrorAction Stop
                break
            }
            catch {
                Start-Sleep -Milliseconds 400
                if ($i -eq 2) {
                    throw "Could not clean $path. Close running app/windows using build artifacts and retry."
                }
            }
        }
    }
}

if (-not (Test-Path $specPath)) {
    throw "Missing PyInstaller spec file: $specPath"
}

.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean $specPath
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
