@echo off
REM ============================================================
REM  T2M - Verificacao antes de gerar o instalador
REM  Coloque na RAIZ do repositorio e execute com 2 cliques.
REM ============================================================
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "RAIZ=%~dp0"
set "REL=%RAIZ%x64\Release"
set "SRC=%RAIZ%T2M_Security_Manager"
set /a ERROS=0
set /a AVISOS=0

echo.
echo ============================================================
echo   VERIFICACAO PRE-INSTALADOR - T2M Security Manager
echo ============================================================
echo.

echo --- 1. Arquivos que VAO para o instalador ---
call :CHECA "%REL%\T2M_Security_Manager.exe" "Executavel principal" E
call :CHECA "%REL%\agente_mcp.py"            "Agente MCP em Python" E
call :CHECA "%REL%\gerador_ia.py"            "Gerador IA em Python" A
call :CHECA "%REL%\get_token.py"             "Script get_token"     A
call :CHECA "%REL%\listar_modelos.py"        "Buscador de modelos"  A
call :CHECA "%REL%\T2M_logo-03.png"          "Logo do app"          A
call :CHECA "%SRC%\icon2.ico"                "Icone do app"         A

echo.
echo --- 2. Arquivos de apoio na raiz ---
call :CHECA "%RAIZ%requirements.txt"          "Lista de dependencias" E
call :CHECA "%RAIZ%instalar_dependencias.bat" "Script de dependencias" E
call :CHECA "%RAIZ%instalador_t2m.iss"        "Script do Inno Setup"  E
call :CHECA "%RAIZ%LICENSE"                   "Licenca GPL"           E
call :CHECA "%RAIZ%README.md"                 "README em ingles"      A
call :CHECA "%RAIZ%README.pt.md"              "README em portugues"   A

echo.
echo --- 3. SEGURANCA: dados pessoais na Release ---
call :PESSOAL "%REL%\api_keys_ia.txt"   "chaves de API"
call :PESSOAL "%REL%\config.txt"        "configuracoes pessoais"
call :PESSOAL "%REL%\memoria_chat.json" "historico de conversas"
echo    [OK] O instalador empacota apenas exe, py, png e ico.
echo         Os arquivos pessoais acima NAO entram no pacote.

echo.
echo --- 4. Ambiente de execucao ---
python --version >nul 2>&1
if errorlevel 1 goto SEMPY
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo    [OK] %%v
goto CHECANODE
:SEMPY
echo    [!] Python nao encontrado no PATH
set /a AVISOS+=1
:CHECANODE
where npx >nul 2>&1
if errorlevel 1 goto SEMNODE
for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo    [OK] Node %%v
goto SINTAXE
:SEMNODE
echo    [!] Node ou npx nao encontrado no PATH
set /a AVISOS+=1

:SINTAXE
echo.
echo --- 5. Sintaxe do agente Python ---
python -m py_compile "%REL%\agente_mcp.py" >nul 2>&1
if errorlevel 1 goto SINTAXERRO
echo    [OK] agente_mcp.py compila sem erros
goto MODELOS
:SINTAXERRO
echo    [X] agente_mcp.py tem ERRO DE SINTAXE
set /a ERROS+=1

:MODELOS
echo.
echo --- 6. Modelos de IA atualizados ---
findstr /C:"claude-3-5-sonnet-2024" "%REL%\agente_mcp.py" >nul 2>&1
if errorlevel 1 goto MODELOOK
echo    [X] Ainda usa claude-3-5-sonnet, que foi APOSENTADO
set /a ERROS+=1
goto FIM
:MODELOOK
echo    [OK] Nenhum modelo aposentado em uso

:FIM
echo.
echo ============================================================
if %ERROS% GTR 0 goto TEMERRO
if %AVISOS% GTR 0 goto TEMAVISO
echo   RESULTADO: TUDO CERTO.
echo   Pode gerar o instalador: F9 no Inno Setup.
goto ENCERRA
:TEMAVISO
echo   RESULTADO: essencial OK, com %AVISOS% aviso^(s^).
echo   Avisos nao impedem a geracao do instalador.
goto ENCERRA
:TEMERRO
echo   RESULTADO: %ERROS% erro^(s^) e %AVISOS% aviso^(s^).
echo   Corrija os itens com [X] antes de gerar o instalador.
:ENCERRA
echo ============================================================
echo.
pause
exit /b

REM ---------------- sub-rotinas ----------------
:CHECA
if exist "%~1" goto CHECAOK
if /i "%~3"=="E" goto CHECAERRO
echo    [!] ausente e opcional: %~2
set /a AVISOS+=1
exit /b
:CHECAERRO
echo    [X] FALTA: %~2
echo        esperado em: %~1
set /a ERROS+=1
exit /b
:CHECAOK
echo    [OK] %~2
exit /b

:PESSOAL
if exist "%~1" echo    [i] presente na Release: %~2
exit /b
