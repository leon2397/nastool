@echo off

REM === UTF-8 MODE ===
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

REM nastool 生成报告 - Windows 批处理脚本
REM 版本: 3.0.6

echo ================================================
echo    nastool v3.0.6 - 生成报告
echo ================================================
echo.

set REPORT_FILE=report_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%.html
set REPORT_FILE=%REPORT_FILE: =0%

python arm_diagnose.py --output %REPORT_FILE% --format html

echo.
echo ================================================
echo 报告已生成: %REPORT_FILE%
echo.
echo 用浏览器打开查看报告
echo ================================================
pause
