@echo off

REM === UTF-8 MODE ===
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

REM nastool 自动修复 - Windows 批处理脚本
REM 版本: 3.0.6

echo ================================================
echo    nastool v3.0.6 - 自动修复
echo ================================================
echo.

python arm_diagnose.py --fix --auto

echo.
echo ================================================
echo 修复完成！
echo.
echo 建议运行 check.bat 再次检查
echo ================================================
pause
