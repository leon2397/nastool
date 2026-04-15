@echo off
REM nastools ARM Agent 启动脚本 (Windows)

cd /d "%~dp0"

REM 默认配置
if not defined CONFIG_FILE set CONFIG_FILE=config.yaml

REM 检查 Python
python3 --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 需要 Python 3
    exit /b 1
)

REM 检查依赖
pip3 install -q websockets pyyaml 2>nul

REM 构建参数
set ARGS=--config %CONFIG_FILE%
if defined RELAY_URL set ARGS=%ARGS% --relay-url %RELAY_URL%
if defined AGENT_KEY set ARGS=%ARGS% --agent-key %AGENT_KEY%

REM 启动
python3 agent.py %ARGS% %*
