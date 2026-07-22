@echo off
REM ============================================================
REM  T2M - Sincroniza os arquivos baixados para o projeto
REM
REM  Copia da pasta Downloads para os lugares certos:
REM    - MyForm.h            -> codigo-fonte (vira parte do .exe ao compilar)
REM    - *.py                -> codigo-fonte E Release (o app le da Release)
REM    - icon2.ico           -> codigo-fonte E Release
REM    - .iss/.txt/.md/.bat  -> raiz do repositorio
REM
REM  Coloque na RAIZ do repositorio e execute com 2 cliques.
REM ============================================================
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "DOWNLOADS=%USERPROFILE%\Downloads"
set "RAIZ=%~dp0"
set "SRC=%RAIZ%T2M_Security_Manager"
set "REL=%RAIZ%x64\Release"
set /a COPIADOS=0

echo.
echo ============================================================
echo   Sincronizando arquivos baixados
echo ============================================================
echo   Origem : %DOWNLOADS%
echo.

REM ---- MyForm.h: so no codigo-fonte ----
call :COPIA "MyForm.h" "%SRC%" "codigo-fonte"

REM ---- Scripts Python: nos dois lugares ----
for %%A in (agente_mcp.py gerador_ia.py get_token.py) do (
  call :COPIA "%%A" "%SRC%" "codigo-fonte"
  call :COPIA "%%A" "%REL%" "Release"
)

REM ---- Icone: nos dois lugares ----
call :COPIA "icon2.ico" "%SRC%" "codigo-fonte"
call :COPIA "icon2.ico" "%REL%" "Release"

REM ---- Apoio: raiz do repositorio ----
for %%A in (instalador_t2m.iss requirements.txt instalar_dependencias.bat README.md README.pt.md gerar_icone.py verificar_antes_do_instalador.bat) do (
  call :COPIA "%%A" "%RAIZ%" "raiz"
)

REM ---- Utilitarios de teste: Release ----
for %%A in (teste_ia.py teste_chat.py) do (
  call :COPIA "%%A" "%REL%" "Release"
)

echo.
echo ============================================================
if %COPIADOS%==0 (
  echo   Nenhum arquivo novo encontrado em Downloads.
) else (
  echo   %COPIADOS% arquivo^(s^) sincronizado^(s^).
  echo.
  echo   LEMBRETE: se o MyForm.h foi atualizado, feche o Visual Studio
  echo   ANTES de rodar este script e depois faca Rebuild.
)
echo ============================================================
echo.
pause
exit /b

REM ---------------- sub-rotina ----------------
:COPIA
if not exist "%DOWNLOADS%\%~1" exit /b
if not exist "%~2" exit /b
copy /Y "%DOWNLOADS%\%~1" "%~2\%~1" >nul
if errorlevel 1 (
  echo    [X] falhou: %~1 -^> %~3
) else (
  echo    [OK] %~1 -^> %~3
  set /a COPIADOS+=1
)
exit /b
