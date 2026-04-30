@echo off
chcp 65001 >nul
set PYTHONPATH=C:\tools416\nastool_gui
cd /d C:\tools416\nastool_gui
python -c "from gui.app import main; main()"
pause
