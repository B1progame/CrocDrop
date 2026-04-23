@echo off
setlocal
cd /d "%~dp0\.."

set VERSION=%1
if "%VERSION%"=="" (
  for /f "tokens=2 delims== " %%v in ('findstr /B /C:"APP_VERSION" app\version.py') do set VERSION=%%~v
)
set VERSION=%VERSION:"=%
if "%VERSION%"=="" set VERSION=1.1.1

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
