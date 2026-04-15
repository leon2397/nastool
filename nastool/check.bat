@echo off

REM === UTF-8 MODE ===
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

REM nastool 快速诊断 - Windows 批处理脚本
REM 版本: 3.0.6

echo ================================================
echo    nastool v3.0.6 - 快速诊断
echo ================================================
echo.

python arm_diagnose.py --quick

echo.
echo ================================================
echo 诊断完成！
echo.
echo 更多选项：
echo   fix.bat     - 自动修复问题
echo   report.bat  - 生成 HTML 报告
echo   monitor.bat - 启动监控
echo ================================================
pause
