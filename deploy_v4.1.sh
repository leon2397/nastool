#!/bin/bash
# ============================================================
# NASTool V4.1 部署脚本
# 目标设备: 192.168.1.123
# 部署目录: ~/nastool
# ============================================================

set -e

# 彩色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

TARGET_HOST="192.168.1.123"
TARGET_USER="nvidia"
DEPLOY_DIR="~/nastool"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

log_step "============================================"
log_step "  NASTool V4.1 部署脚本"
log_step "============================================"
log_info "目标设备: ${TARGET_HOST}"
log_info "部署目录: ${DEPLOY_DIR}"
log_info "本地目录: ${LOCAL_DIR}"

# Step 1: 检查连接
log_step "[1/6] 检查目标设备连接..."
if ! ping -c 1 -W 2 ${TARGET_HOST} > /dev/null 2>&1; then
    log_error "无法连接到目标设备 ${TARGET_HOST}"
    exit 1
fi
log_info "目标设备可连接"

# Step 2: 备份旧版本
log_step "[2/6] 备份旧版本..."
ssh ${TARGET_USER}@${TARGET_HOST} "
    if [ -d ${DEPLOY_DIR} ]; then
        BACKUP_DIR=~/nastool-backup-\$(date +%Y%m%d_%H%M%S)
        mv ${DEPLOY_DIR} \${BACKUP_DIR}
        echo \"已备份旧版本到: \${BACKUP_DIR}\"
    fi
    mkdir -p ${DEPLOY_DIR}
" || {
    log_error "备份失败"
    exit 1
}
log_info "备份完成"

# Step 3: 复制核心模块
log_step "[3/6] 复制核心模块到目标设备..."

# 需要部署的模块
MODULES=(
    "nastool-common"
    "nastool-core"
    "nastool-adapters"
    "nastool-cli"
    "nastool-reporters"
    "nastool-fixes"
)

for module in "${MODULES[@]}"; do
    if [ -d "${LOCAL_DIR}/${module}" ]; then
        log_info "复制 ${module}..."
        scp -r "${LOCAL_DIR}/${module}" ${TARGET_USER}@${TARGET_HOST}:${DEPLOY_DIR}/ > /dev/null 2>&1
    else
        log_warn "模块 ${module} 不存在，跳过"
    fi
done

log_info "核心模块复制完成"

# Step 4: 复制测试和部署文件
log_step "[4/6] 复制测试和部署文件..."

# 复制测试脚本
if [ -d "${LOCAL_DIR}/tests" ]; then
    scp -r "${LOCAL_DIR}/tests" ${TARGET_USER}@${TARGET_HOST}:${DEPLOY_DIR}/ > /dev/null 2>&1
    log_info "复制 tests/"
fi

# 复制部署脚本
if [ -d "${LOCAL_DIR}/deploy" ]; then
    scp -r "${LOCAL_DIR}/deploy" ${TARGET_USER}@${TARGET_HOST}:${DEPLOY_DIR}/ > /dev/null 2>&1
    log_info "复制 deploy/"
fi

# 复制文档
if [ -d "${LOCAL_DIR}/docs" ]; then
    scp -r "${LOCAL_DIR}/docs" ${TARGET_USER}@${TARGET_HOST}:${DEPLOY_DIR}/ > /dev/null 2>&1
    log_info "复制 docs/"
fi

# 复制数据文件
if [ -d "${LOCAL_DIR}/data" ]; then
    scp -r "${LOCAL_DIR}/data" ${TARGET_USER}@${TARGET_HOST}:${DEPLOY_DIR}/ > /dev/null 2>&1
    log_info "复制 data/"
fi

log_info "附加文件复制完成"

# Step 5: 创建启动脚本
log_step "[5/6] 创建启动脚本..."

ssh ${TARGET_USER}@${TARGET_HOST} "cat > ${DEPLOY_DIR}/run.sh << 'EOFSCRIPT'
#!/bin/bash
# NASTool V4.1 启动脚本

SCRIPT_DIR=\"\$(cd \"\$(dirname \"\$0\")\" && pwd)\"
cd \"\$SCRIPT_DIR\"

# 设置 Python 路径
export PYTHONPATH=\"\${SCRIPT_DIR}/nastool-cli:\${SCRIPT_DIR}/nastool-common:\${SCRIPT_DIR}/nastool-core:\${SCRIPT_DIR}/nastool-reporters:\${SCRIPT_DIR}/nastool-fixes:\${SCRIPT_DIR}/nastool-adapters\"

# 运行 CLI
python3 -m nastool_cli.main \"\$@\"
EOFSCRIPT
chmod +x ${DEPLOY_DIR}/run.sh"

# 创建快速诊断脚本
ssh ${TARGET_USER}@${TARGET_HOST} "cat > ${DEPLOY_DIR}/diagnose.sh << 'EOFSCRIPT'
#!/bin/bash
# NASTool V4.1 快速诊断脚本

cd \"\$(dirname \"\$0\")\"
./run.sh diagnose \"\$@\"
EOFSCRIPT
chmod +x ${DEPLOY_DIR}/diagnose.sh"

# 创建版本检查脚本
ssh ${TARGET_USER}@${TARGET_HOST} "cat > ${DEPLOY_DIR}/version.sh << 'EOFSCRIPT'
#!/bin/bash
# NASTool V4.1 版本检查脚本

cd \"\$(dirname \"\$0\")\"
./run.sh --version
EOFSCRIPT
chmod +x ${DEPLOY_DIR}/version.sh"

log_info "启动脚本创建完成"

# Step 6: 验证部署
log_step "[6/6] 验证部署..."

ssh ${TARGET_USER}@${TARGET_HOST} "
    cd ${DEPLOY_DIR}
    echo \"=== 部署文件列表 ===\"
    ls -la
    echo \"\"
    echo \"=== 模块检查 ===\"
    for dir in nastool-common nastool-core nastool-adapters nastool-cli nastool-reporters nastool-fixes; do
        if [ -d \"\${dir}\" ]; then
            echo \"[OK] \${dir}\"
        else
            echo \"[MISSING] \${dir}\"
        fi
    done
    echo \"\"
    echo \"=== 版本信息 ===\"
    ./version.sh 2>/dev/null || echo \"版本检查需要安装依赖\"
"

log_step "============================================"
log_step "  NASTool V4.1 部署完成！"
log_step "============================================"
log_info "部署目录: ${DEPLOY_DIR}"
log_info ""
log_info "使用方法:"
log_info "  ssh ${TARGET_USER}@${TARGET_HOST}"
log_info "  cd ${DEPLOY_DIR}"
log_info ""
log_info "  # 查看版本"
log_info "  ./version.sh"
log_info ""
log_info "  # 运行诊断"
log_info "  ./diagnose.sh"
log_info ""
log_info "  # 使用完整功能"
log_info "  ./run.sh --help"
log_info ""
log_step "============================================"
