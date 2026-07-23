@echo off
REM ============================================================
REM  T2M Security Manager - preparacao do ambiente
REM
REM  Verifica Python e Node.js e, se faltarem (ou forem antigos),
REM  oferece instalar pelo winget - o gerenciador de pacotes que
REM  ja vem no Windows 10 e 11. Sempre pede permissao antes.
REM ============================================================
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ------------------------------------------------------------
REM  VERSOES INSTALADAS QUANDO ALGO ESTIVER FALTANDO
REM
REM  Python fica FIXO de proposito. Instalar sempre a versao mais
REM  recente parece melhor, mas quebra na pratica: bibliotecas como
REM  oracledb e grpcio levam meses para publicar versoes compativeis
REM  com um Python recem-lancado, e o pip install falha nesse meio-tempo.
REM
REM  Se ja houver Python 3.10+ na maquina, NADA e instalado.
REM
REM  Para atualizar no futuro: troque por uma versao com pelo menos
REM  seis meses de lancamento.
REM ------------------------------------------------------------
set "PYTHON_WINGET_ID=Python.Python.3.12"

REM  O Node usa o identificador LTS, que acompanha sozinho a versao
REM  de suporte estendido atual.
set "NODE_WINGET_ID=OpenJS.NodeJS.LTS"

REM  Importante: NAO mexemos no PATH aqui. O PATH herdado do terminal
REM  ja funciona, e altera-lo sem necessidade quebrava a deteccao
REM  (a variavel crescia alem do limite do Windows e perdia entradas).
set FALTA=0
set INSTALOU=0

echo.
echo ============================================================
echo   T2M Security Manager - preparando o ambiente
echo ============================================================
echo.

set TEM_WINGET=0
where winget >nul 2>&1
if not errorlevel 1 set TEM_WINGET=1

REM ============================================================
REM  1. PYTHON
REM ============================================================
echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 goto PY_AUSENTE

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo    [OK] %%v
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 goto NODE

echo    [!] Versao antiga demais. O T2M precisa do Python 3.10 ou superior.
if "%TEM_WINGET%"=="0" (
  echo        Baixe uma versao atual em: https://www.python.org/downloads/
  set FALTA=1
  goto NODE
)
echo.
echo        Instalar uma versao nova NAO remove a atual: as duas convivem,
echo        e seus outros projetos continuam funcionando.
set /p RESP="    Deseja instalar uma versao compativel agora? (S/N): "
if /i not "!RESP!"=="S" (
  set FALTA=1
  goto NODE
)
goto PY_INSTALAR

:PY_AUSENTE
echo    [X] Python nao encontrado.
if "%TEM_WINGET%"=="0" (
  echo        Baixe em: https://www.python.org/downloads/
  echo        IMPORTANTE: marque "Add Python to PATH" durante a instalacao.
  set FALTA=1
  goto NODE
)
echo.
set /p RESP="    Deseja instalar o Python agora? (S/N): "
if /i not "!RESP!"=="S" (
  echo        Baixe em: https://www.python.org/downloads/
  set FALTA=1
  goto NODE
)

:PY_INSTALAR
echo    Instalando o Python... isso leva alguns minutos.
winget install --id !PYTHON_WINGET_ID! --source winget --silent --accept-package-agreements --accept-source-agreements
call :ACRESCENTAR_CAMINHOS
set INSTALOU=1
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo    [!] Instalado, mas ainda nao reconhecido nesta janela.
  set FALTA=1
) else (
  echo    [OK] Python pronto.
)

REM ============================================================
REM  2. NODE.JS
REM ============================================================
:NODE
echo.
echo [2/4] Verificando Node.js...
where npx >nul 2>&1
if errorlevel 1 goto NODE_AUSENTE

for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo    [OK] Node %%v
set NODE_MAIOR=
for /f "tokens=1 delims=." %%m in ('node -p "process.versions.node" 2^>nul') do set NODE_MAIOR=%%m
if not defined NODE_MAIOR goto CONTINUAR
if !NODE_MAIOR! GEQ 18 goto CONTINUAR

echo    [!] Versao antiga demais. Os servidores MCP precisam do Node 18 ou superior.
if "%TEM_WINGET%"=="0" (
  echo        Baixe a versao LTS em: https://nodejs.org/
  set FALTA=1
  goto CONTINUAR
)
echo.
set /p RESP2="    Deseja atualizar o Node.js agora? (S/N): "
if /i not "!RESP2!"=="S" (
  set FALTA=1
  goto CONTINUAR
)
goto NODE_INSTALAR

:NODE_AUSENTE
echo    [X] Node.js nao encontrado.
if "%TEM_WINGET%"=="0" (
  echo        Baixe a versao LTS em: https://nodejs.org/
  echo        Necessario para os servidores MCP ^(navegador, banco, MongoDB^).
  set FALTA=1
  goto CONTINUAR
)
echo.
set /p RESP2="    Deseja instalar o Node.js agora? (S/N): "
if /i not "!RESP2!"=="S" (
  echo        Baixe a versao LTS em: https://nodejs.org/
  set FALTA=1
  goto CONTINUAR
)

:NODE_INSTALAR
echo    Instalando o Node.js LTS... isso leva alguns minutos.
winget install --id !NODE_WINGET_ID! --source winget --silent --accept-package-agreements --accept-source-agreements
call :ACRESCENTAR_CAMINHOS
set INSTALOU=1
where npx >nul 2>&1
if errorlevel 1 (
  echo    [!] Instalado, mas ainda nao reconhecido nesta janela.
  set FALTA=1
) else (
  echo    [OK] Node.js pronto.
)

:CONTINUAR
if "%FALTA%"=="1" goto PENDENTE

REM ============================================================
REM  3. BIBLIOTECAS PYTHON
REM ============================================================
echo.
echo [3/4] Instalando as bibliotecas Python...
echo       ^(pode levar alguns minutos na primeira vez^)
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo    [X] Falha ao instalar as bibliotecas.
  echo        Tente manualmente: python -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)
echo    [OK] Bibliotecas instaladas.

REM ============================================================
REM  4. NAVEGADOR DE TESTES
REM ============================================================
echo.
echo [4/4] Instalando o navegador de testes ^(Chromium^)...
echo.
echo       Observacao: o Playwright vai exibir um aviso amarelo sugerindo
echo       rodar "npm install". Pode ignorar - ele assume que voce esta num
echo       projeto Node, e o T2M nao e. A instalacao funciona normalmente.
echo.
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
echo   Ambiente pronto. Voce ja pode usar o T2M.
echo.
echo   Proximo passo: abra o aplicativo e adicione sua chave de
echo   API ^(Claude, OpenAI ou Gemini^) para comecar.
echo ============================================================
echo.
pause
exit /b 0

:PENDENTE
echo.
echo ------------------------------------------------------------
echo  Instale o que falta acima e rode este arquivo novamente.
echo  Ele fica em: %~dp0
if "%INSTALOU%"=="1" (
  echo.
  echo  DICA: algo foi instalado agora. Feche este terminal, abra
  echo  outro e rode de novo - o Windows so reconhece programas
  echo  novos em janelas abertas depois da instalacao.
)
echo ------------------------------------------------------------
echo.
pause
exit /b 1

REM ============================================================
REM  Acrescenta ao PATH os locais padrao de instalacao.
REM  Chamado APENAS depois de instalar algo, para que o programa
REM  recem-instalado seja reconhecido nesta mesma janela.
REM  Nao copiamos o PATH inteiro do registro: a variavel crescia
REM  alem do limite do Windows e entradas do fim da lista sumiam.
REM ============================================================
:ACRESCENTAR_CAMINHOS
if exist "%ProgramFiles%\nodejs\node.exe" set "PATH=%PATH%;%ProgramFiles%\nodejs"
if exist "%APPDATA%\npm\npx.cmd" set "PATH=%PATH%;%APPDATA%\npm"
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  if exist "%%D\python.exe" set "PATH=!PATH!;%%D;%%D\Scripts"
)
for /d %%D in ("%ProgramFiles%\Python3*") do (
  if exist "%%D\python.exe" set "PATH=!PATH!;%%D;%%D\Scripts"
)
exit /b
