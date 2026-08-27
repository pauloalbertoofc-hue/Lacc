@echo off
title Enviando LigaHub para o GitHub...
cd /d "%~dp0"
echo ======================================================
echo          ENVIANDO CODIGO PARA O GITHUB (LACC)
echo ======================================================
echo.
echo Conectando ao repositorio https://github.com/pauloalbertoofc-hue/Lacc ...
echo.
git branch -M main
git push -u origin main
echo.
echo ======================================================
echo Codigo enviado com sucesso para o GitHub!
echo ======================================================
pause

