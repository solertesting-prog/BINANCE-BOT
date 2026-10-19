@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Compilar Valorize Bot
echo ================================================
echo   Compilar Valorize Bot a un programa .exe
echo ================================================
echo.
echo Convierte el codigo en un programa compilado para entregar a tus clientes,
echo de forma que no puedan ver ni modificar el codigo (ni saltarse la licencia).
echo.
echo AVISO: la primera vez descarga un compilador y puede tardar entre 20 y 60 minutos.
echo        No cierres esta ventana.
echo.
if not exist venv (echo Primero ejecuta instalar.bat & pause & exit /b 1)
call venv\Scripts\activate.bat
python -c "import licensing,sys; sys.exit(0 if licensing.REQUIRE_LICENSE else 1)"
if errorlevel 1 (
  echo [INFO] Version GRATUITA: REQUIRE_LICENSE = False en licensing.py, no se pedira licencia.
  echo        Para cobrar, ponlo a True y vuelve a compilar.
  goto compilar
)
python -c "import licensing,sys; sys.exit(0 if licensing.STORE_ID else 1)"
if errorlevel 1 (
  echo [AVISO] En licensing.py no has puesto todavia el STORE_ID de tu tienda de Lemon Squeezy.
  echo         Sin el, el programa aceptaria licencias de cualquier tienda. Mira VENTA_LICENCIAS.md
  choice /c SN /m "Compilar de todas formas"
  if errorlevel 2 exit /b 1
)
:compilar
echo [1/3] Instalando el compilador (Nuitka)...
python -m pip install -q nuitka ordered-set zstandard
echo [2/3] Buscando el compilador de C...
set "CCOPT="
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if exist "%VSWHERE%" (
  for /f "usebackq delims=" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "CCOPT=--msvc=latest"
)
if defined CCOPT (
  echo      Usando el compilador de Microsoft - Visual Studio Build Tools.
) else (
  echo      No se encuentra el compilador de Microsoft - Visual Studio Build Tools.
  echo      Se intentara con MinGW, pero si Windows tiene activado el Control inteligente
  echo      de aplicaciones lo bloqueara. Solucion recomendada: instala Build Tools
  echo      siguiendo VENTA_LICENCIAS.md, apartado Si la compilacion falla.
)
echo      Compilando (paciencia)...
python -m nuitka --standalone --assume-yes-for-downloads --windows-console-mode=disable %CCOPT% ^
  --output-dir=build --output-filename=ValorizeBot.exe ^
  --windows-icon-from-ico=assets\bot.ico ^
  --company-name="Valorize" --product-name="Valorize Bot" --file-version=1.0.0.0 --product-version=1.0.0.0 ^
  --include-data-dir=web=web --include-data-dir=assets=assets ^
  --include-data-files=.env.example=.env.example --include-data-files=MANUAL_CLIENTE.md=MANUAL_CLIENTE.md ^
  --include-package=ccxt --nofollow-import-to=ccxt.async_support --nofollow-import-to=ccxt.pro ^
  --nofollow-import-to=pytest --nofollow-import-to=tests ^
  panel.py
if errorlevel 1 (
  echo [ERROR] La compilacion ha fallado. Copia el mensaje de arriba y pregunta a Claude.
  pause
  exit /b 1
)
echo [3/3] Preparando la carpeta para el cliente...
if exist "dist\Valorize Bot" rmdir /s /q "dist\Valorize Bot"
mkdir dist 2>nul
move build\panel.dist "dist\Valorize Bot" >nul
copy /y cliente\instalar-cliente.bat "dist\Valorize Bot\Instalar Valorize Bot.bat" >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\Valorize Bot' -DestinationPath 'dist\ValorizeBot-1.0.zip'"
echo.
echo ================================================
echo   Listo: dist\ValorizeBot-1.0.zip
echo   Ese ZIP es lo que entregas al cliente (subelo a Lemon Squeezy).
echo ================================================
pause
