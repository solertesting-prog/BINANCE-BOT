@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "DIR=%~dp0"
set "DIR=%DIR:~0,-1%"
title Instalacion - Trading Bot
echo ================================================
echo   Instalacion del Trading Bot
echo ================================================
echo.
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python no esta instalado o no se marco "Add python.exe to PATH".
  echo Instala Python desde https://www.python.org/downloads/ marcando esa casilla
  echo y vuelve a hacer doble clic en este archivo.
  echo.
  pause
  exit /b 1
)
python --version
echo.
echo [1/5] Creando el entorno virtual...
if not exist venv python -m venv venv
call venv\Scripts\activate.bat
echo [2/5] Instalando las piezas del bot (1-2 minutos)...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo [ERROR] Fallo al instalar. Copia el mensaje de arriba y pregunta a Claude.
  pause
  exit /b 1
)
echo [3/5] Preparando el archivo de configuracion .env...
if not exist .env (copy .env.example .env >nul) else (echo      Ya existia, no se toca.)
echo [4/5] Comprobando que todo funciona...
python -m pytest tests -q
if errorlevel 1 (
  echo [AVISO] Algun test ha fallado. Copia el mensaje de arriba y pregunta a Claude.
  pause
)
echo [5/5] Creando el icono "Trading Bot" en el escritorio...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Trading Bot.lnk'); $s.TargetPath='%DIR%\venv\Scripts\pythonw.exe'; $s.Arguments='panel.py'; $s.WorkingDirectory='%DIR%'; $s.IconLocation='%DIR%\assets\bot.ico'; $s.Description='Panel del bot de trading'; $s.Save()"
echo.
echo ================================================
echo   Instalacion terminada.
echo ================================================
echo.
choice /c SN /m "Quieres que el panel se abra solo al encender el PC"
if errorlevel 2 goto fin
call "%DIR%\autoarranque-activar.bat" silencioso
:fin
echo.
echo Abriendo el panel en tu navegador...
start "" "%DIR%\venv\Scripts\pythonw.exe" panel.py
echo A partir de ahora, usa el icono "Trading Bot" del escritorio.
echo.
pause
