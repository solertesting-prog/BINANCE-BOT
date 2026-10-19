@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================================
echo   Instalacion del bot de trading
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
echo [1/4] Creando el entorno virtual...
if not exist venv python -m venv venv
call venv\Scripts\activate.bat
echo [2/4] Instalando las piezas del bot (1-2 minutos)...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo [ERROR] Fallo al instalar. Copia el mensaje de arriba y pregunta a Claude.
  pause
  exit /b 1
)
echo [3/4] Creando el archivo de configuracion .env...
if not exist .env (copy .env.example .env >nul) else (echo      Ya existia, no se toca.)
echo [4/4] Comprobando que todo funciona...
python -m pytest tests -q
echo.
echo ================================================
echo   Si arriba pone "9 passed", la instalacion esta lista.
echo   Siguiente paso: doble clic en backtest.bat
echo ================================================
pause
