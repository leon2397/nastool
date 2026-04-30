@echo off
chcp 65001 >nul

:: 硬编码路径设置
set "BASE_PATH=D:\project\nastool7"
set "ADAPTERS_PATH=%BASE_PATH%\nastool-v4.0.0\nastool-adapters"
set "CORE_PATH=%BASE_PATH%\nastool-v4.0.0\nastool-core"
set "COMMON_PATH=%BASE_PATH%\nastool-v4.0.0\nastool-common"
set "FIXES_PATH=%BASE_PATH%\nastool-v4.0.0\nastool-fixes"
set "REPORTERS_PATH=%BASE_PATH%\nastool-reporters"

:: 设置 PYTHONPATH
set "PYTHONPATH=%ADAPTERS_PATH%;%CORE_PATH%;%COMMON_PATH%;%FIXES_PATH%;%REPORTERS_PATH%;%BASE_PATH%"

:: 显示设置信息
echo 基础路径: %BASE_PATH%
echo 适配器路径: %ADAPTERS_PATH%
echo 核心路径: %CORE_PATH%
echo 公共路径: %COMMON_PATH%
echo 修复路径: %FIXES_PATH%
echo 报告路径: %REPORTERS_PATH%
echo PYTHONPATH: %PYTHONPATH%
echo.

:: 进入 nastool_gui 目录
cd /d "%BASE_PATH%\nastool_gui"

:: 启动 GUI
echo 启动 NASTool GUI...
python __main__.py
pause
