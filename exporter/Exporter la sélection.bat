@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul && (py -3 -m figcraft_export export && goto :done)
where python >nul 2>nul && (python -m figcraft_export export & goto :done)
echo Python 3 est introuvable.
:done
pause
