@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "DIR=%~dp0"
set "DIR=%DIR:~0,-1%"
echo Instalando Valorize Bot...
if not exist .env copy .env.example .env >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Valorize Bot.lnk'); $s.TargetPath='%DIR%\ValorizeBot.exe'; $s.WorkingDirectory='%DIR%'; $s.IconLocation='%DIR%\ValorizeBot.exe'; $s.Description='Valorize Bot'; $s.Save()"
choice /c SN /m "Quieres que Valorize Bot se abra solo al encender el PC"
if errorlevel 2 goto fin
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([Environment]::GetFolderPath('Startup')+'\Valorize Bot.lnk'); $s.TargetPath='%DIR%\ValorizeBot.exe'; $s.Arguments='--no-browser'; $s.WorkingDirectory='%DIR%'; $s.IconLocation='%DIR%\ValorizeBot.exe'; $s.Save()"
:fin
start "" "%DIR%\ValorizeBot.exe"
echo Listo. A partir de ahora usa el icono "Valorize Bot" del escritorio.
pause
