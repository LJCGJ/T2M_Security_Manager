@echo off
REM ============================================================
REM  T2M - Conectar ao Claude Desktop
REM
REM  Existe para o atalho ter o que abrir. Um atalho apontando
REM  direto para o .py fecha a janela antes de a pessoa ler o
REM  resultado - e o resultado E a funcionalidade aqui: dizer o
REM  que esta pronto e o que falta.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 goto SEMPYTHON

python conectar_claude.py %*
echo.
pause
exit /b

:SEMPYTHON
echo.
echo  [X] Python nao encontrado no PATH.
echo      O servidor do T2M para o Claude Desktop e escrito em Python.
echo      Use o atalho "Preparar ambiente" no menu Iniciar, ou instale
echo      o Python 3.10+ de https://www.python.org/downloads/
echo.
pause
exit /b
