@echo off

REM === UTF-8 MODE ===
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

REM nastool 一键部署脚本 (Windows)
REM 用法: deploy.bat <nas_ip> <nas_user> <nas_type>
REM 示例: deploy.bat 192.168.1.100 admin synology

setlocal enabledelayedexpansion

REM 参数检查
if "%~3"=="" (
    echo 用法:
    echo   deploy.bat ^<nas_ip^> ^<nas_user^> ^<nas_type^>
    echo.
    echo 示例:
    echo   deploy.bat 192.168.1.100 admin synology
    echo   deploy.bat 192.168.1.101 admin qnap
    echo   deploy.bat 192.168.1.123 nvidia jetson
    exit /b 1
)

set NAS_IP=%~1
set NAS_USER=%~2
set NAS_TYPE=%~3

REM 发布包路径
set SCRIPT_DIR=%~dp0
set RELEASE_DIR=%SCRIPT_DIR%..\_releases

REM 找最新的发布包
set LATEST_RELEASE=
for /f "delims=" %%i in ('dir /b /o-n "%RELEASE_DIR%\nastool-v3.0.7-*.zip" 2^>nul') do (
    set LATEST_RELEASE=%%i
    goto :found
)

echo 错误: 未找到发布包
echo 请先运行: python arm_diagnose.py --build-release
exit /b 1

:found
set RELEASE_ZIP=%RELEASE_DIR%\%LATEST_RELEASE%

echo === nastool 部署脚本 ===
echo.
echo NAS IP:     %NAS_IP%
echo NAS 用户:   %NAS_USER%
echo NAS 类型:   %NAS_TYPE%
echo 发布包:     %RELEASE_ZIP%
echo.

REM 测试连接
echo 测试 SSH 连接...
ssh -o ConnectTimeout=5 -o BatchMode=yes %NAS_USER%@%NAS_IP% "echo OK" 2>nul
if errorlevel 1 (
    echo SSH 连接失败
    echo 请确保:
    echo   1. NAS 设备在线
    echo   2. SSH 服务已启用
    echo   3. 用户名密码正确
    exit /b 1
)
echo SSH 连接成功
echo.

REM 上传发布包
echo 上传发布包...
set REMOTE_DIR=/tmp/nastool-deploy
ssh %NAS_USER%@%NAS_IP% "mkdir -p %REMOTE_DIR%"
scp "%RELEASE_ZIP%" %NAS_USER%@%NAS_IP%:%REMOTE_DIR%/
echo 上传完成
echo.

REM 解压并安装
echo 解压并安装...
for /f "tokens=*" %%i in ("%LATEST_RELEASE%") do set RELEASE_NAME=%%~ni

ssh %NAS_USER%@%NAS_IP% "cd %REMOTE_DIR% && unzip -o %LATEST_RELEASE% && mkdir -p ~/nastool && rm -rf ~/nastool && mv %RELEASE_NAME% ~/nastool && rm -rf %REMOTE_DIR%"

echo.
echo === 部署完成 ===
echo.
echo SSH 登录并运行:
echo   ssh %NAS_USER%@%NAS_IP%
echo   cd ~/nastool
echo   python3 arm_diagnose.py --nas %NAS_TYPE%
