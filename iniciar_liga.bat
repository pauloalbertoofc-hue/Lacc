@echo off
title LigaHub - Servidor da Liga Academica
cd /d "%~dp0"
echo ======================================================
echo           LIGAHUB - SISTEMA DA LIGA ACADEMICA
echo ======================================================
echo.
echo Iniciando o sistema e abrindo o navegador...
echo.

REM Inicia o servidor Python com o ambiente virtual
.\.venv\Scripts\python run.py

pause

