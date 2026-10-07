@echo off
rem Abre o gravador de consulta no Windows. De um duplo clique neste arquivo.
rem Sem acento de proposito: o console do Windows nao le UTF-8 por padrao.
rem
rem Funciona de dentro da pasta do projeto e tambem se este arquivo for copiado
rem para outro lugar: neste caso procura o projeto nos lugares habituais.

setlocal
set "PROJETO=%~dp0"
if exist "%PROJETO%app\gravador.py" goto achou

for %%D in ("%USERPROFILE%\One-" "%USERPROFILE%\Documents\One-" "%USERPROFILE%\Desktop\One-" "%USERPROFILE%\Downloads\One-") do (
  if exist "%%~D\app\gravador.py" (
    set "PROJETO=%%~D\"
    goto achou
  )
)

echo.
echo   Nao encontrei a pasta do projeto.
echo.
echo   Este atalho esta em:
echo       %~dp0
echo.
echo   Ele precisa estar dentro da pasta One-, ou a pasta One- precisa estar
echo   na sua pasta de usuario. Se voce copiou este arquivo para fora do
echo   projeto, apague a copia e use o que esta dentro de One-.
echo.
pause
exit /b 1

:achou
cd /d "%PROJETO%"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   Achei o projeto em %PROJETO%, mas a instalacao nao foi feita.
  echo.
  echo   Abra o PowerShell e rode:
  echo       cd "%PROJETO%"
  echo       py -m venv .venv
  echo       .venv\Scripts\pip install -r app\requirements.txt
  echo.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" app\gravador.py %*
pause
