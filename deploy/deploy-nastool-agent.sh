#!/bin/bash
# ============================================================
# NASTool Agent 一键部署脚本 v2.1
# 目标设备: 192.168.1.123 (或其他 Linux 设备)
# 使用方式: bash deploy-nastool-agent.sh [options]
# 示例:
#   bash deploy-nastool-agent.sh --relay http://localhost:8888 --device-id my-device --group prod
#   bash deploy-nastool-agent.sh --help
# ============================================================

set -e

# 彩色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 默认配置
RELAY_URL="http://120.77.249.3:18888"
DEVICE_ID="nvidia-01"
DEVICE_NAME="NVIDIA Workstation"
DEVICE_TYPE="nvidia"
GROUP="prod"
AGENT_KEY=""
INSTALL_DIR="$HOME/nastool-agent"
TEST_MODE=false

# 解析命令行参数
show_help() {
    echo "NASTool Agent 部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --relay URL         Relay服务器URL (默认: $RELAY_URL)"
    echo "  --device-id ID      设备ID (默认: $DEVICE_ID)"
    echo "  --device-name NAME  设备名称 (默认: $DEVICE_NAME)"
    echo "  --device-type TYPE  设备类型 (默认: $DEVICE_TYPE)"
    echo "  --group GROUP       设备组 (默认: $GROUP)"
    echo "  --agent-key KEY     Agent密钥"
    echo "  --install-dir DIR   安装目录 (默认: $INSTALL_DIR)"
    echo "  --test              测试模式 (不启动服务)"
    echo "  --help              显示此帮助信息"
    echo ""
    echo "环境变量:"
    echo "  NASTOOL_RELAY_URL   同 --relay"
    echo "  NASTOOL_DEVICE_ID   同 --device-id"
    echo "  NASTOOL_DEVICE_NAME 同 --device-name"
    echo "  NASTOOL_DEVICE_TYPE 同 --device-type"
    echo "  NASTOOL_GROUP       同 --group"
    echo "  NASTOOL_AGENT_KEY   同 --agent-key"
    echo "  NASTOOL_INSTALL_DIR 同 --install-dir"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --relay)
            RELAY_URL="$2"
            shift 2
            ;;
        --device-id)
            DEVICE_ID="$2"
            shift 2
            ;;
        --device-name)
            DEVICE_NAME="$2"
            shift 2
            ;;
        --device-type)
            DEVICE_TYPE="$2"
            shift 2
            ;;
        --group)
            GROUP="$2"
            shift 2
            ;;
        --agent-key)
            AGENT_KEY="$2"
            shift 2
            ;;
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --test)
            TEST_MODE=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            ;;
    esac
done

# 从环境变量读取配置（如果命令行参数未指定）
RELAY_URL=${NASTOOL_RELAY_URL:-$RELAY_URL}
DEVICE_ID=${NASTOOL_DEVICE_ID:-$DEVICE_ID}
DEVICE_NAME=${NASTOOL_DEVICE_NAME:-$DEVICE_NAME}
DEVICE_TYPE=${NASTOOL_DEVICE_TYPE:-$DEVICE_TYPE}
GROUP=${NASTOOL_GROUP:-$GROUP}
AGENT_KEY=${NASTOOL_AGENT_KEY:-$AGENT_KEY}
INSTALL_DIR=${NASTOOL_INSTALL_DIR:-$INSTALL_DIR}

# ===== Step 1: 检查系统 =====
log_info "============================================"
log_info "  NASTool Agent 一键部署 v2.1"
log_info "============================================"
log_info ""
log_info "[1/6] 检查系统环境..."

OS_TYPE=$(uname -s)
if [ "$OS_TYPE" != "Linux" ]; then
    log_error "此脚本仅支持 Linux 系统"
    exit 1
fi

log_info "系统: $(uname -s) $(uname -r)"
log_info "架构: $(uname -m)"
log_info "主机: $(hostname)"
log_info "安装目录: $INSTALL_DIR"

# ===== Step 2: 检查/安装 Python3 =====
log_info ""
log_info "[2/6] 检查 Python3..."

if ! command -v python3 &> /dev/null; then
    log_warn "Python3 未安装，正在安装..."
    if command -v apt &> /dev/null; then
        log_info "使用 apt 安装 Python3..."
        sudo apt update && sudo apt install -y python3 python3-pip python3-venv
    elif command -v yum &> /dev/null; then
        log_info "使用 yum 安装 Python3..."
        sudo yum install -y python3 python3-pip
    elif command -v dnf &> /dev/null; then
        log_info "使用 dnf 安装 Python3..."
        sudo dnf install -y python3 python3-pip
    elif command -v zypper &> /dev/null; then
        log_info "使用 zypper 安装 Python3..."
        sudo zypper install -y python3 python3-pip
    else
        log_error "无法自动安装 Python3，请手动安装后重试"
        exit 1
    fi
fi

PYTHON_VERSION=$(python3 --version 2>&1)
log_info "Python 版本: $PYTHON_VERSION"

# ===== Step 3: 安装依赖 =====
log_info ""
log_info "[3/6] 安装 Python 依赖..."

# 创建 requirements.txt 文件
cat > "$INSTALL_DIR/requirements.txt" << 'EOF'
websocket-client
requests
EOF

# 创建安装目录
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# 安装依赖
log_info "安装依赖包..."
pip3 install --user -r requirements.txt -q 2>/dev/null || pip3 install -r requirements.txt -q
log_info "依赖安装完成"

# ===== Step 4: 生成 agent_key =====
log_info ""
log_info "[4/6] 配置 agent_key..."

if [ -z "$AGENT_KEY" ]; then
    # 直接使用固定的agent_key进行测试
    AGENT_KEY="test-agent-key-${DEVICE_ID}"
    log_warn "未提供 agent_key，使用测试密钥: ${AGENT_KEY}"
else
    log_info "使用提供的 agent_key"
fi

# ===== Step 5: 创建 agent 目录和脚本 =====
log_info ""
log_info "[5/6] 创建 agent 目录和脚本..."

# 下载或创建 agent 脚本
if [ ! -f "nastool_agent.py" ]; then
    log_info "下载 nastool_agent.py..."
    curl -s -o nastool_agent.py "$RELAY_URL/static/nastool_agent.py" 2>/dev/null || {
        log_warn "无法从 Relay 下载，使用本地版本"
        if [ -f "../nastool_agent.py" ]; then
            cp "../nastool_agent.py" .
            log_info "已从本地复制 nastool_agent.py"
        else
            log_error "nastool_agent.py 不存在，无法继续"
            exit 1
        fi
    }
fi

if [ ! -f "nastool_agent.py" ]; then
    log_error "nastool_agent.py 不存在，无法继续"
    exit 1
fi

# 创建配置文件
cat > config.sh << EOF
#!/bin/bash
# Agent 配置文件
export NASTOOL_RELAY_URL="$RELAY_URL"
export NASTOOL_DEVICE_ID="$DEVICE_ID"
export NASTOOL_DEVICE_NAME="$DEVICE_NAME"
export NASTOOL_DEVICE_TYPE="$DEVICE_TYPE"
export NASTOOL_GROUP="$GROUP"
export NASTOOL_AGENT_KEY="$AGENT_KEY"
export NASTOOL_INSTALL_DIR="$INSTALL_DIR"
EOF

log_info "配置文件已创建: config.sh"

# 创建启动脚本
cat > start.sh << 'START_EOF'
#!/bin/bash
cd "$(dirname "$0")"
source config.sh

# 检查进程是否已运行
if [ -f agent.pid ]; then
    PID=$(cat agent.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Agent 已经在运行 (PID: $PID)"
        exit 1
    fi
    rm -f agent.pid
fi

# 启动 agent
nohup python3 nastool_agent.py \
    --relay "$NASTOOL_RELAY_URL" \
    --key "$NASTOOL_AGENT_KEY" \
    --device-id "$NASTOOL_DEVICE_ID" \
    --device-name "$NASTOOL_DEVICE_NAME" \
    --device-type "$NASTOOL_DEVICE_TYPE" \
    --group "$NASTOOL_GROUP" \
    > agent.log 2>&1 &

# 记录 PID
echo $! > agent.pid
echo "Agent started with PID: $(cat agent.pid)"
echo "日志文件: agent.log"
START_EOF

# 创建停止脚本
cat > stop.sh << 'STOP_EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [ -f agent.pid ]; then
    PID=$(cat agent.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID 2>/dev/null && echo "Agent stopped (PID: $PID)" || echo "Failed to stop agent"
    else
        echo "Agent not running"
    fi
    rm -f agent.pid
else
    echo "No PID file found"
fi
STOP_EOF

# 创建测试脚本
cat > test.sh << 'TEST_EOF'
#!/bin/bash
cd "$(dirname "$0")"
source config.sh
python3 nastool_agent.py \
    --relay "$NASTOOL_RELAY_URL" \
    --key "$NASTOOL_AGENT_KEY" \
    --device-id "$NASTOOL_DEVICE_ID" \
    --once
TEST_EOF

# 创建状态检查脚本
cat > status.sh << 'STATUS_EOF'
#!/bin/bash
cd "$(dirname "$0")"

if [ -f agent.pid ]; then
    PID=$(cat agent.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Agent is running (PID: $PID)"
        echo "Uptime: $(ps -o etimes= -p $PID) seconds"
        return 0
    else
        echo "Agent is not running (stale PID file)"
        rm -f agent.pid
        return 1
    fi
else
    echo "Agent is not running"
    return 1
fi
STATUS_EOF

# 创建日志轮转脚本
cat > rotate_log.sh << 'ROTATE_EOF'
#!/bin/bash
cd "$(dirname "$0")"

# 检查日志文件大小
LOG_FILE="agent.log"
MAX_SIZE=10485760  # 10MB

if [ -f "$LOG_FILE" ]; then
    FILE_SIZE=$(stat -c %s "$LOG_FILE")
    if [ $FILE_SIZE -gt $MAX_SIZE ]; then
        # 备份日志
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        mv "$LOG_FILE" "agent_${TIMESTAMP}.log"
        # 压缩备份
        gzip "agent_${TIMESTAMP}.log"
        echo "Log rotated: agent_${TIMESTAMP}.log.gz"
        # 清理旧备份（保留最近5个）
        ls -t agent_*.log.gz | tail -n +6 | xargs rm -f 2>/dev/null
    fi
fi
ROTATE_EOF

chmod +x start.sh stop.sh test.sh status.sh rotate_log.sh nastool_agent.py

# 创建配置模板
cat > config.example.sh << EOF
#!/bin/bash
# Agent 配置模板
# 复制为 config.sh 并修改相应值

export NASTOOL_RELAY_URL="http://your-relay-server:8888"
export NASTOOL_DEVICE_ID="your-device-id"
export NASTOOL_DEVICE_NAME="Your Device Name"
export NASTOOL_DEVICE_TYPE="nvidia"  # 可选: nvidia, rockchip, raspberry, nas
export NASTOOL_GROUP="prod"
export NASTOOL_AGENT_KEY="your-agent-key-here"
export NASTOOL_INSTALL_DIR="$INSTALL_DIR"
EOF

log_info "配置模板已创建: config.example.sh"

# ===== Step 6: 启动 agent =====
log_info ""
log_info "[6/6] 完成部署..."

if [ "$TEST_MODE" = false ]; then
    log_info ""
    log_info "============================================"
    log_info "  部署完成！"
    log_info "============================================"
    log_info ""
    log_info "Agent 目录: $INSTALL_DIR"
    log_info ""
    log_info "使用方式:"
    log_info ""
    log_info "  # 测试模式 (连接 10 秒后断开)"
    log_info "  cd $INSTALL_DIR && ./test.sh"
    log_info ""
    log_info "  # 正式运行 (后台常驻)"
    log_info "  cd $INSTALL_DIR && ./start.sh"
    log_info ""
    log_info "  # 停止 agent"
    log_info "  cd $INSTALL_DIR && ./stop.sh"
    log_info ""
    log_info "  # 查看状态"
    log_info "  cd $INSTALL_DIR && ./status.sh"
    log_info ""
    log_info "  # 查看日志"
    log_info "  tail -f $INSTALL_DIR/agent.log"
    log_info ""
    log_info "  # 日志轮转"
    log_info "  cd $INSTALL_DIR && ./rotate_log.sh"
    log_info ""
    log_info "============================================"
    log_info ""
    log_info "现在执行测试..."
    cd "$INSTALL_DIR" && ./test.sh
else
    log_info ""
    log_info "============================================"
    log_info "  测试模式部署完成！"
    log_info "============================================"
    log_info ""
    log_info "Agent 目录: $INSTALL_DIR"
    log_info ""
    log_info "配置文件已创建，但未启动服务"
    log_info "请查看 config.sh 并根据需要修改配置"
    log_info ""
    log_info "使用 ./start.sh 启动服务"
    log_info "============================================"
fi

log_info ""
log_info "部署脚本执行完成"
