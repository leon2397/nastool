@echo off
chcp 65001 >nul 2>&1
title nastools - ARM NAS 诊断工具
cd /d "%~dp0"
echo.
echo  ================================================
echo   nastools ARM NAS 诊断与部署工具 v1.1
echo  ================================================
echo.
REM v1.1: 使用模块化包 nastools_pkg/
python nastools_pkg\main.py
if errorlevel 1 (
    echo.
    echo  Python 未安装或出错，请安装 Python 3.8+:
    echo  https://www.python.org/downloads/
    pause
)
