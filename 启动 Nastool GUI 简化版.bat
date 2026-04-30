@echo off
chcp 65001 >nul

:: 进入 nastool_gui 目录
cd /d "%~dp0\nastool_gui"

:: 启动 GUI
python __main__.py
pause
