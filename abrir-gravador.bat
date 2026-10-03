@echo off
rem Abre o gravador de consulta no Windows. De um duplo clique neste arquivo.
rem Sem acento de proposito: o console do Windows nao le UTF-8 por padrao.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   A instalacao nao esta completa: falta a pasta .venv.
  echo.
  echo   Abra o PowerShell nesta pasta e rode:
  echo       py -m venv .venv
  echo       .venv\Scripts\pip install -r app\requirements.txt
  echo.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" app\gravador.py %*
pause
