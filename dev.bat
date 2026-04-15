@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

if "%1"=="" goto help
if "%1"=="test" goto test
if "%1"=="lint" goto lint
if "%1"=="run" goto run
if "%1"=="status" goto status
if "%1"=="commit" goto commit
goto help

:test
echo [TEST] Running pytest...
cd /d D:\armtool415\nastool
if "%2"=="" (
    python -m pytest tests/ -v --tb=short %3 %4 %5
) else (
    python -m pytest tests/%2 -v --tb=short %3 %4 %5
)
goto end

:lint
echo [LINT] Running ruff...
cd /d D:\armtool415\nastool
python -m ruff check . --fix
goto end

:run
echo [RUN] Running arm_diagnose...
cd /d D:\armtool415\nastool
if "%2"=="" (
    python arm_diagnose.py --parallel 2 --no-progress
) else (
    python arm_diagnose.py %2 %3 %4 %5 %6 %7 %8
)
goto end

:status
echo [STATUS] Git status...
cd /d D:\armtool415
git status --short
echo.
echo [VERSION]
type VERSION.txt
goto end

:commit
cd /d D:\armtool415
git add -A
if "%2"=="" (
    git commit -m "update: %date% %time:~0,5%"
) else (
    git commit -m "%2"
)
goto end

:help
echo.
echo   nastools dev commands:
echo   ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
echo   dev test          Run all tests
echo   dev test X        Run specific test file
echo   dev lint          Run ruff linter
echo   dev run           Run arm_diagnose --parallel 2
echo   dev run [args]    Run with custom args
echo   dev status        Git status + version
echo   dev commit [msg]  Stage all + commit
echo.

:end
