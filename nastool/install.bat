@echo off

REM === UTF-8 MODE ===
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

REM nastool Windows 一键安装

setlocal enabledelayedexpansion

set VERSION=3.0.7
set INSTALL_DIR=%USERPROFILE%\nastool

echo.
echo ========================================
echo    nastool v%VERSION% 安装程序
echo    ARM NAS 设备诊断工具
echo ========================================
echo.

REM 检测 Python
echo 检测 Python...
where python >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python
    echo 请先安装 Python 3.8 或更高版本
    echo 下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python: %PYTHON_VERSION%

REM 创建安装目录
echo 创建安装目录: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM 复制文件（假设当前目录就是安装包）
echo 复制文件...
xcopy /E /I /Y "%~dp0*" "%INSTALL_DIR%\" >nul 2>&1

REM 创建桌面快捷方式
echo 创建快捷方式...
set SCRIPT="%TEMP%\createshortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\nastool.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%INSTALL_DIR%\start.bat" >> %SCRIPT%
echo oLink.WorkingDirectory = "%INSTALL_DIR%" >> %SCRIPT%
echo oLink.Description = "nastool - NAS 诊断工具" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript //nologo %SCRIPT%
del %SCRIPT%

REM 添加到 PATH
echo 添加到 PATH...
setx PATH "%PATH%;%INSTALL_DIR%" >nul 2>&1

echo.
echo ========================================
echo          安装完成！
echo ========================================
echo.
echo 安装目录: %INSTALL_DIR%
echo.
echo 快速开始:
echo   1. 双击桌面 "nastool" 图标
echo   2. 或运行: cd %INSTALL_DIR% ^&^& start.bat
echo.
echo 查看帮助:
echo   python arm_diagnose.py --help
echo.

pause
