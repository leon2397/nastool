#!/bin/bash
# nastools ARM Agent 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 默认配置
CONFIG_FILE="${CONFIG_FILE:-config.yaml}"
RELAY_URL="${RELAY_URL:-}"
AGENT_KEY="${AGENT_KEY:-}"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 需要 Python 3"
    exit 1
fi

# 检查依赖
pip3 install -q websockets pyyaml 2>/dev/null || true

# 构建参数
ARGS=""
[ -n "$RELAY_URL" ] && ARGS="$ARGS --relay-url $RELAY_URL"
[ -n "$AGENT_KEY" ] && ARGS="$ARGS --agent-key $AGENT_KEY"

# 启动
exec python3 agent.py --config "$CONFIG_FILE" $ARGS "$@"
