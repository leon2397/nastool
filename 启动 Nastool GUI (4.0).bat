@echo off
chcp 65001 >nul

:: 设置 4.0 版本的模块路径
set BASE_PATH=%~dp0
set ADAPTERS_PATH=%BASE_PATH%\nastool-v4.0.0\nastool-adapters
set CORE_PATH=%BASE_PATH%\nastool-v4.0.0\nastool-core
set COMMON_PATH=%BASE_PATH%\nastool-v4.0.0\nastool-common
set FIXES_PATH=%BASE_PATH%\nastool-v4.0.0\nastool-fixes
set REPORTERS_PATH=%BASE_PATH%\nastool-reporters

:: 设置 PYTHONPATH
set PYTHONPATH=%ADAPTERS_PATH%;%CORE_PATH%;%COMMON_PATH%;%FIXES_PATH%;%REPORTERS_PATH%;%BASE_PATH%

:: 启动 GUI
cd /d %BASE_PATH%
python -m nastool_gui
pause
