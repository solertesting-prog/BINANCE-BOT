@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist venv (echo Primero ejecuta instalar.bat & pause & exit /b 1)
call venv\Scripts\activate.bat
echo El bot se esta ejecutando. NO cierres esta ventana.
echo Para pararlo pulsa Ctrl + C.
echo.
python bot.py
pause
