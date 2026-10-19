@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "DIR=%~dp0"
set "DIR=%DIR:~0,-1%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([Environment]::GetFolderPath('Startup')+'\Valorize Bot.lnk'); $s.TargetPath='%DIR%\venv\Scripts\pythonw.exe'; $s.Arguments='panel.py --no-browser'; $s.WorkingDirectory='%DIR%'; $s.IconLocation='%DIR%\assets\bot.ico'; $s.Save()"
echo Arranque automatico ACTIVADO: el panel se abrira solo (en segundo plano) al encender el PC.
echo Si el bot estaba en marcha, continuara automaticamente.
if not "%1"=="silencioso" pause
