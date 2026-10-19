@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist venv (echo Primero ejecuta instalar.bat & pause & exit /b 1)
call venv\Scripts\activate.bat
python bot.py --status
pause
