@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente Python nao instalado. Execute o instalador.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "scripts\backup.py"
if errorlevel 1 pause
