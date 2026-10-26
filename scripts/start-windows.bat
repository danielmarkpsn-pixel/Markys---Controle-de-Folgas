@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo O ambiente ainda nao foi instalado. Iniciando instalador...
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\install-windows.ps1"
  if errorlevel 1 exit /b 1
)
if not exist ".env" (
  echo Arquivo .env nao encontrado. Execute scripts\install-windows.ps1.
  pause
  exit /b 1
)
if exist "logs" (rem logs folder ready) else mkdir logs
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info
