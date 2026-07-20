@echo off
REM ============================================================
REM  T2M Security Manager - instalacao das dependencias
REM  Executado automaticamente pelo instalador (ou manualmente).
REM ============================================================
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PATH=%PATH%;%ProgramFiles%\nodejs;%APPDATA%\npm;%ProgramFiles(x86)%\nodejs"
set FALTA=0

echo.
echo ============================================================
echo   T2M Security Manager - preparando o ambiente
echo ============================================================
echo.

REM ---------- 1. Python ----------
echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo    [X] Python NAO encontrado.
  echo        Baixe em: https://www.python.org/downloads/
  echo        IMPORTANTE: marque "Add Python to PATH" durante a instalacao.
  set FALTA=1
) else (
  for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo    [OK] %%v
)

REM ---------- 2. Node.js ----------
echo.
echo [2/4] Verificando Node.js...
where npx >nul 2>&1
if errorlevel 1 (
  echo    [X] Node.js NAO encontrado.
  echo        Baixe a versao LTS em: https://nodejs.org/
  echo        Necessario para os servidores MCP ^(navegador, banco, MongoDB^).
  set FALTA=1
) else (
  for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo    [OK] Node %%v
)

if "%FALTA%"=="1" (
  echo.
  echo ------------------------------------------------------------
  echo  Instale o que falta acima e rode este arquivo novamente.
  echo  Ele fica em: %~dp0
  echo ------------------------------------------------------------
  echo.
  pause
  exit /b 1
)

REM ---------- 3. Bibliotecas Python ----------
echo.
echo [3/4] Instalando bibliotecas Python ^(pode levar alguns minutos^)...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo    [X] Falha ao instalar as bibliotecas Python.
  echo        Tente rodar manualmente: python -m pip install -r requirements.txt
  pause
  exit /b 1
)
echo    [OK] Bibliotecas Python instaladas.

REM ---------- 4. Navegador do Playwright ----------
echo.
echo [4/4] Instalando o navegador de testes ^(Playwright/Chromium^)...
call npx -y playwright install chromium
if errorlevel 1 (
  echo    [!] Nao foi possivel instalar o Chromium agora.
  echo        O Teste de Tela pode falhar ate voce rodar:
  echo        npx playwright install chromium
) else (
  echo    [OK] Navegador pronto.
)

echo.
echo ============================================================
echo   Ambiente preparado. Voce ja pode usar o T2M.
echo.
echo   Lembre-se: adicione sua chave de API dentro do app
echo   ^(Claude, OpenAI ou Gemini^) antes de usar a automacao.
echo ============================================================
echo.
pause
