@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" >nul 2>&1 && set "PY=python"
if not defined PY (
  echo Python 3 est introuvable.
  pause
  exit /b 1
)
%PY% -m figcraft_export export
pause
