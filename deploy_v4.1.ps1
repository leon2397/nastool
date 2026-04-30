# ============================================================
# NASTool V4.1 部署脚本 (PowerShell)
# 目标设备: 192.168.1.123
# 部署目录: ~/nastool
# ============================================================

$TARGET_HOST = "192.168.1.123"
$TARGET_USER = "nvidia"
$DEPLOY_DIR = "~/nastool"
$LOCAL_DIR = $PSScriptRoot

function Write-Info { param([string]$Message) Write-Host "[INFO] $Message" -ForegroundColor Green }
function Write-Warn { param([string]$Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Error { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }
function Write-Step { param([string]$Message) Write-Host "[STEP] $Message" -ForegroundColor Cyan }

Write-Step "============================================"
Write-Step "  NASTool V4.1 部署脚本"
Write-Step "============================================"
Write-Info "目标设备: ${TARGET_HOST}"
Write-Info "部署目录: ${DEPLOY_DIR}"
Write-Info "本地目录: ${LOCAL_DIR}"

# Step 1: 检查连接
Write-Step "[1/6] 检查目标设备连接..."
$pingResult = Test-Connection -ComputerName $TARGET_HOST -Count 1 -Quiet
if (-not $pingResult) {
    Write-Error "无法连接到目标设备 ${TARGET_HOST}"
    exit 1
}
Write-Info "目标设备可连接"

# Step 2: 备份旧版本
Write-Step "[2/6] 备份旧版本..."
$backupCmd = @"
if [ -d ${DEPLOY_DIR} ]; then
    BACKUP_DIR=~/nastool-backup-$(date +%Y%m%d_%H%M%S)
    mv ${DEPLOY_DIR} \${BACKUP_DIR}
    echo "已备份旧版本到: \${BACKUP_DIR}"
fi
mkdir -p ${DEPLOY_DIR}
"@

$backupResult = ssh ${TARGET_USER}@${TARGET_HOST} $backupCmd 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "备份失败: $backupResult"
    exit 1
}
Write-Info $backupResult
Write-Info "备份完成"

# Step 3: 复制核心模块
Write-Step "[3/6] 复制核心模块到目标设备..."

$MODULES = @(
    "nastool-common",
    "nastool-core",
    "nastool-adapters",
    "nastool-cli",
    "nastool-reporters",
    "nastool-fixes"
)

foreach ($module in $MODULES) {
    $modulePath = Join-Path $LOCAL_DIR $module
    if (Test-Path $modulePath -PathType Container) {
        Write-Info "复制 ${module}..."
        scp -r "${modulePath}" ${TARGET_USER}@${TARGET_HOST}:${DEPLOY_DIR}/ 2>&1 | Out-Null
    } else {
        Write-Warn "模块 ${module} 不存在，跳过"
    }
}

Write-Info "核心模块复制完成"

# Step 4: 复制测试和部署文件
Write-Step "[4/6] 复制测试和部署文件..."

$DIRS = @("tests", "deploy", "docs", "data")
foreach ($dir in $DIRS) {
    $dirPath = Join-Path $LOCAL_DIR $dir
    if (Test-Path $dirPath -PathType Container) {
        Write-Info "复制 ${dir}/"
        scp -r "${dirPath}" ${TARGET_USER}@${TARGET_HOST}:${DEPLOY_DIR}/ 2>&1 | Out-Null
    }
}

Write-Info "附加文件复制完成"

# Step 5: 创建启动脚本
Write-Step "[5/6] 创建启动脚本..."

$runScript = @'
#!/bin/bash
# NASTool V4.1 启动脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 设置 Python 路径
export PYTHONPATH="${SCRIPT_DIR}/nastool-cli:${SCRIPT_DIR}/nastool-common:${SCRIPT_DIR}/nastool-core:${SCRIPT_DIR}/nastool-reporters:${SCRIPT_DIR}/nastool-fixes:${SCRIPT_DIR}/nastool-adapters"

# 运行 CLI
python3 -m nastool_cli.main "$@"
'@

$diagnoseScript = @'
#!/bin/bash
# NASTool V4.1 快速诊断脚本

cd "$(dirname "$0")"
./run.sh diagnose "$@"
'@

$versionScript = @'
#!/bin/bash
# NASTool V4.1 版本检查脚本

cd "$(dirname "$0")"
./run.sh --version
'@

# 创建脚本文件
$runScript | ssh ${TARGET_USER}@${TARGET_HOST} "cat > ${DEPLOY_DIR}/run.sh && chmod +x ${DEPLOY_DIR}/run.sh"
$diagnoseScript | ssh ${TARGET_USER}@${TARGET_HOST} "cat > ${DEPLOY_DIR}/diagnose.sh && chmod +x ${DEPLOY_DIR}/diagnose.sh"
$versionScript | ssh ${TARGET_USER}@${TARGET_HOST} "cat > ${DEPLOY_DIR}/version.sh && chmod +x ${DEPLOY_DIR}/version.sh"

Write-Info "启动脚本创建完成"

# Step 6: 验证部署
Write-Step "[6/6] 验证部署..."

$verifyCmd = @"
cd ${DEPLOY_DIR}
echo "=== 部署文件列表 ==="
ls -la
echo ""
echo "=== 模块检查 ==="
for dir in nastool-common nastool-core nastool-adapters nastool-cli nastool-reporters nastool-fixes; do
    if [ -d "\