@echo off
chcp 65001 >nul
powershell -NoProfile -Command "Remove-Item -ErrorAction SilentlyContinue ([Environment]::GetFolderPath('Startup')+'\Valorize Bot.lnk')"
echo Arranque automatico DESACTIVADO.
pause
