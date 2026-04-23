@echo off
setlocal
cd /d "%~dp0\.."

set VERSION=%1
if "%VERSION%"=="" (
  for /f "tokens=2 delims== " %%v in ('findstr /B /C:"APP_VERSION" app\version.py') do set VERSION=%%~v
)
set VERSION=%VERSION:"=%
if "%VERSION%"=="" set VERSION=1.1.1

if "%GITHUB_TOKEN%"=="" (
  echo [CrocDrop] GITHUB_TOKEN is not set. Please set it first.
  exit /b 1
)

echo [CrocDrop] Publishing release %VERSION% to GitHub...
powershell -ExecutionPolicy Bypass -File ".\installer\publish_release.ps1" -Version %VERSION%
if errorlevel 1 (
  echo [CrocDrop] Release publish failed.
  exit /b 1
)

echo [CrocDrop] Release publish completed.
endlocal
