@echo off
setlocal
cd /d "%~dp0\.."

set VERSION=%1
if "%VERSION%"=="" set VERSION=1.0.0

if not exist ".venv\Scripts\python.exe" (
  echo [CrocDrop] Creating virtual environment...
  python -m venv .venv
)

echo [CrocDrop] Running installer build pipeline (version %VERSION%)...
powershell -ExecutionPolicy Bypass -File ".\installer\build_installer.ps1" -Version %VERSION%
if errorlevel 1 (
  echo [CrocDrop] Installer build failed.
  exit /b 1
)

echo [CrocDrop] Installer build completed.
endlocal
