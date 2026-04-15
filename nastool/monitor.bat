@echo off

REM === UTF-8 MODE ===
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

REM nastool 启动监控 - Windows 批处理脚本
REM 版本: 3.0.6

echo ================================================
echo    nastool v3.0.6 - 启动监控
echo ================================================
echo.
echo 监控模式将在后台运行，定期检查设备状态
echo 按 Ctrl+C 停止监控
echo.

python arm_diagnose.py --monitor
