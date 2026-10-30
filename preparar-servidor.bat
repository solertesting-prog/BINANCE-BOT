@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar servidor - Valorize Bot
if not exist venv (echo Primero ejecuta instalar.bat & pause & exit /b 1)
echo ================================================
echo   Preparar el servidor de Valorize Bot
echo ================================================
echo.
venv\Scripts\python deploy\generar_cloud_init.py
echo.
echo Siguiente paso: sigue SERVIDOR.md (crear el servidor y pegar el texto).
pause
