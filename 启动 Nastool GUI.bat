@echo off
chcp 65001 >nul
set PYTHONPATH=%~dp0
cd /d %~dp0
python -m nastool_gui
pause
