@echo off

REM === UTF-8 MODE ===
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

REM nastool 一键启动 - Windows 批处理脚本
REM 版本: 3.0.6

:menu
cls
echo.
echo  ================================================================
echo     nastool v3.0.6 - ARM 设备诊断工具
echo  ================================================================
echo.
echo   请选择操作：
echo.
echo   [1] 快速检查     - 30秒快速诊断（推荐新手）
echo   [2] 完整诊断     - 深度检查所有项目
echo   [3] 自动修复     - 自动修复检测到的问题
echo   [4] 生成报告     - 导出 HTML/JSON 报告
echo   [5] 启动监控     - 持续监控设备状态
echo   [6] 配置向导     - 首次使用配置
echo   [7] 查看帮助     - 显示完整使用说明
echo.
echo   [0] 退出
echo.
echo  ================================================================
set /p choice=请输入选项 [0-6]: 

if "%choice%"=="1" goto check
if "%choice%"=="2" goto full
if "%choice%"=="3" goto fix
if "%choice%"=="4" goto report
if "%choice%"=="5" goto monitor
if "%choice%"=="6" goto setup
if "%choice%"=="7" goto help
if "%choice%"=="0" goto end
goto menu

:check
cls
echo.
echo  执行快速诊断...
echo.
python arm_diagnose.py --quick
pause
goto menu

:full
cls
echo.
echo  执行完整诊断...
echo.
python arm_diagnose.py --full
pause
goto menu

:fix
cls
echo.
echo  执行自动修复...
echo.
python arm_diagnose.py --fix --auto
pause
goto menu

:report
cls
echo.
echo  生成诊断报告...
echo.
set REPORT_FILE=report_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%.html
set REPORT_FILE=%REPORT_FILE: =0%
python arm_diagnose.py --output %REPORT_FILE% --format html
echo.
echo  报告已生成: %REPORT_FILE%
pause
goto menu

:monitor
cls
echo.
echo  启动监控模式...
echo  按 Ctrl+C 停止
echo.
python arm_diagnose.py --monitor
goto menu

:setup
cls
echo.
echo  启动配置向导...
echo.
python arm_diagnose.py --setup
pause
goto menu

:help
cls
echo.
echo  ================================================================
echo   使用说明
echo  ================================================================
echo.
echo  命令行用法：
echo    python arm_diagnose.py              # 快速诊断
echo    python arm_diagnose.py --full       # 完整诊断
echo    python arm_diagnose.py --fix        # 修复问题
echo    python arm_diagnose.py --output report.html --format html
echo.
echo  快捷脚本：
echo    check.bat    - 快速诊断
echo    fix.bat      - 自动修复
echo    report.bat   - 生成报告
echo    monitor.bat  - 启动监控
echo.
echo  更多信息请查看 README.md
echo.
pause
goto menu

:end
echo.
echo  感谢使用 nastool！
echo.
timeout /t 2 >nul
