@echo off
REM ============================================================
REM  T2M - Verificacao antes de gerar o instalador
REM  Coloque na RAIZ do repositorio e execute com 2 cliques.
REM
REM  ESTE ARQUIVO SO CHAMA O verificar_instalador.py.
REM
REM  Ate a versao 4.2 a conferencia morava aqui, com a lista de
REM  arquivos escrita a mao. O problema desse desenho apareceu na
REM  pratica: o instalador passou versoes sem levar o
REM  servidor_http_mcp.py e este .bat dizia "TUDO CERTO", porque
REM  ninguem tinha lembrado de acrescentar a linha. Uma lista
REM  escrita a mao so sabe o que alguem lembrou de escrever.
REM
REM  O script Python le a lista do proprio instalador_t2m.iss e
REM  cruza com o que o codigo procura em tempo de execucao. A
REM  pergunta deixou de ser "os arquivos que eu listei estao la?"
REM  e passou a ser "o instalador leva tudo o que o programa vai
REM  pedir?".
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 goto SEMPYTHON

python verificar_instalador.py %*
echo.
pause
exit /b

:SEMPYTHON
echo.
echo  [X] Python nao encontrado no PATH.
echo      Instale Python 3.10 ou superior: https://www.python.org/downloads/
echo      Depois rode este arquivo de novo.
echo.
pause
exit /b
