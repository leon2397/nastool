# -*- coding: utf-8 -*-
"""
scripts/deploy.py — NAS 部署与修复脚本（v1.1 安全底线版）

v1.1 实施后，所有修复通过 nastool fixes/ 执行。
本文件保留：NAS 部署脚本、回滚脚本、备份管理脚本。
"""

# ══════════════════════════════════════════════════════════════════
# 核心常量
# ══════════════════════════════════════════════════════════════════

BACKUP_DIR = "/opt/ai-nas/backups"  # 备份存放目录
INSTALL_DIR = "/opt/ai-nas"  # 安装目录
SERVICE_NAME = "ai-nas-arm"  # systemd 服务名

# ══════════════════════════════════════════════════════════════════
# DNS 修复脚本（v1.1 安全底线：只追加，绝不覆盖）
# ══════════════════════════════════════════════════════════════════

DNS_FIX_SCRIPT = r"""
# DNS 修复脚本（追加模式）
# 安全底线：只追加 nameserver，绝不覆盖 /etc/resolv.conf
# 返回码：0=已追加，1=已有无需修改，2=无权限，3=其他错误

RESOLV="/etc/resolv.conf"
PRIMARY_NS="8.8.8.8"
SECONDARY_NS="223.5.5.5"

# 检查是否有写权限
if [ ! -w "$RESOLV" ] 2>/dev/null; then
    echo "ERROR: 无写权限，请使用 sudo 运行"
    exit 2
fi

# 检查是否已有 8.8.8.8
if grep -qE "nameserver\s+$PRIMARY_NS" "$RESOLV" 2>/dev/null; then
    echo "OK: DNS 8.8.8.8 已存在，无需修改"
    exit 1
fi

# 备份现有文件（v1.1 安全底线）
BACKUP_DIR="/opt/ai-nas/backups"
mkdir -p "$BACKUP_DIR"
BAK="$BACKUP_DIR/resolv.conf.bak.$(date +%Y%m%d%H%M%S)"
cp "$RESOLV" "$BAK"
echo "INFO: 已备份 $RESOLV → $BAK"

# 安全追加：只追加不覆盖
{
    echo ""
    echo "# Added by nastools $(date +%Y-%m-%d)"
    echo "nameserver $PRIMARY_NS"
    echo "nameserver $SECONDARY_NS"
} >> "$RESOLV"

# 验证写入成功
if grep -qE "nameserver\s+$PRIMARY_NS" "$RESOLV" 2>/dev/null; then
    echo "OK: DNS 已追加 8.8.8.8 和 223.5.5.5"
    echo "INFO: 如需回退，运行: sudo cp $BAK $RESOLV"
    exit 0
else
    echo "ERROR: 写入失败"
    exit 3
fi
"""

# ══════════════════════════════════════════════════════════════════
# DNS 回滚脚本（v1.1 安全底线：一键回退）
# ══════════════════════════════════════════════════════════════════

DNS_ROLLBACK_SCRIPT = r"""
# DNS 回滚脚本：恢复最近一次备份的 resolv.conf
BAK_DIR="/opt/ai-nas/backups"
LATEST=$(ls -t "$BAK_DIR"/resolv.conf.bak.* 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
    echo "ERROR: 未找到 resolv.conf 备份文件"
    exit 1
fi
if [ ! -w "/etc/resolv.conf" ] 2>/dev/null; then
    echo "ERROR: 无写权限，请使用 sudo"
    exit 2
fi
cp "$LATEST" /etc/resolv.conf
echo "OK: DNS 已回退至 $LATEST"
"""

# ══════════════════════════════════════════════════════════════════
# NAS 主服务部署脚本（v1.1 安全底线：完整备份 + 回滚支持）
# ══════════════════════════════════════════════════════════════════

NAS_DEPLOY_SCRIPT = r"""#!/bin/bash
# nastools v1.1 — NAS 部署脚本（含安全底线）
#   • 部署前自动备份（时间戳命名，可回滚）
#   • 检测已有系统：有则确认+备份，无则直接安装
#   • 服务注册 + 启动验证
set -e

# ══════════════════════════════════════════════════════════════════
# 参数
# ══════════════════════════════════════════════════════════════════
NAS_PORT="${port:-8000}"
NAS_DATA="${data_dir:-/nas}"

BACKUP_DIR="/opt/ai-nas/backups"
INSTALL_DIR="/opt/ai-nas"
mkdir -p "$BACKUP_DIR" "$NAS_DATA"/{photos,albums,thumbnails,temp}

echo "═══════════════════════════════════════"
echo " nastools v1.1 — NAS 部署"
echo "═══════════════════════════════════════"
echo "  端口:     $NAS_PORT"
echo "  数据目录: $NAS_DATA"
echo "  备份目录: $BACKUP_DIR"
echo ""

# ══════════════════════════════════════════════════════════════════
# 步骤 1：从后端下载新版 arm_server.py
# ══════════════════════════════════════════════════════════════════
echo "[1/5] 检查后端更新源..."
if curl -s --connect-timeout 8 http://120.77.249.3:8000/api/health > /dev/null 2>&1; then
    echo "      后端在线，下载新版 arm_server.py..."
    curl -s --connect-timeout 30 -o /tmp/arm_server_new.py \
        http://120.77.249.3:8000/api/arm/backend/download
    if [ -s /tmp/arm_server_new.py ]; then
        NEW_AVAILABLE=1
        echo "      新版下载成功 ($(wc -c < /tmp/arm_server_new.py) bytes)"
    else
        NEW_AVAILABLE=0
        echo "      新版文件为空，跳过更新"
    fi
else
    echo "      后端不可达（离线环境），跳过下载"
    NEW_AVAILABLE=0
fi

# ══════════════════════════════════════════════════════════════════
# 步骤 2：安装目录初始化
# ══════════════════════════════════════════════════════════════════
echo "[2/5] 初始化安装目录..."
mkdir -p "$INSTALL_DIR"

# ══════════════════════════════════════════════════════════════════
# 步骤 3：v1.1 安全底线 — 部署前自动备份（最关键）
# ══════════════════════════════════════════════════════════════════
echo "[3/5] 部署前备份检查..."
declare -a BACKUPS_MADE=()

backup_file() {
    local src="$1"
    if [ -f "$src" ]; then
        local ts=$(date +%Y%m%d%H%M%S)
        local bkp="${src}.bak.${ts}"
        cp "$src" "$bkp"
        BACKUPS_MADE+=("$bkp")
        echo "      ✓ 已备份: $src → $bkp ($(stat -c%s "$src" 2>/dev/null || stat -f%z "$src") bytes)"
    fi
}

if [ -f "$INSTALL_DIR/arm_server.py" ]; then
    echo "      检测到已有安装，准备备份..."
    backup_file "$INSTALL_DIR/arm_server.py"
    [ -f "$INSTALL_DIR/config.yaml" ] && backup_file "$INSTALL_DIR/config.yaml"
    [ -f "$INSTALL_DIR/ai-nas-arm.env" ] && backup_file "$INSTALL_DIR/ai-nas-arm.env"
    [ -f "/etc/systemd/system/ai-nas-arm.service" ] && backup_file "/etc/systemd/system/ai-nas-arm.service"
    echo "      共备份 ${#BACKUPS_MADE[@]} 个文件"
    echo "      → 回退命令: sudo nastools-rollback.sh"
else
    echo "      新安装，无需备份"
fi

# ══════════════════════════════════════════════════════════════════
# 步骤 4：安装文件
# ══════════════════════════════════════════════════════════════════
echo "[4/5] 安装文件..."

if [ "$NEW_AVAILABLE" = "1" ]; then
    cp /tmp/arm_server_new.py "$INSTALL_DIR/arm_server.py"
    echo "      ✓ arm_server.py 已更新"
else
    if [ -f "$INSTALL_DIR/arm_server.py" ]; then
        echo "      ✓ 保留现有 arm_server.py（离线模式）"
    else
        echo "      ✗ 错误：无 arm_server.py 且后端不可达，无法部署"
        exit 1
    fi
fi

# 写入环境配置
cat > "$INSTALL_DIR/ai-nas-arm.env" <<EOF
NAS_PORT=$NAS_PORT
NAS_DATA=$NAS_DATA
NASTOOL_VERSION=1.1
DEPLOYED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BACKUP_DIR=$BACKUP_DIR
EOF
echo "      ✓ ai-nas-arm.env 已写入"

# ══════════════════════════════════════════════════════════════════
# 步骤 5：systemd 服务注册
# ══════════════════════════════════════════════════════════════════
echo "[5/5] 注册 systemd 服务..."
if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
    echo "      服务正在运行，先停止..."
    systemctl stop $SERVICE_NAME || true
fi

cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=AI-NAS ARM Media Manager (nastools v1.1)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/ai-nas-arm.env
ExecStartPre=/bin/bash -c 'sleep 2'
ExecStart=/usr/bin/python3 $INSTALL_DIR/arm_server.py --port $NAS_PORT --nas-path $NAS_DATA
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

# 等待启动验证
sleep 3
if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
    IP=$(ip route get 1.2.3.4 2>/dev/null | grep -oP 'src \K[\d.]+' || hostname -I | awk '{print $1}')
    echo ""
    echo "═══════════════════════════════════════"
    echo " ✓ NAS 部署成功！"
    echo "═══════════════════════════════════════"
    echo "  访问地址: http://$IP:$NAS_PORT"
    echo "  备份目录: $BACKUP_DIR"
    echo "  备份文件: ${BACKUPS_MADE[*]:-（新安装）}"
    echo ""
    echo "  管理命令:"
    echo "    sudo systemctl status $SERVICE_NAME   # 查看状态"
    echo "    sudo systemctl restart $SERVICE_NAME # 重启"
    echo "    sudo nastools-rollback.sh            # 回滚（需指定备份文件）"
    echo "    sudo nastools-uninstall.sh           # 卸载"
else
    echo ""
    echo "  ⚠ 服务启动失败，查看日志: sudo journalctl -u $SERVICE_NAME -n 20"
    exit 1
fi
"""

# ══════════════════════════════════════════════════════════════════
# 回滚脚本（v1.1 安全底线：一键回退）
# ══════════════════════════════════════════════════════════════════

NAS_ROLLBACK_SCRIPT = r"""#!/bin/bash
# nastools v1.1 — 一键回滚脚本
# 用法: sudo bash nastools-rollback.sh [备份文件路径]
# 不带参数则列出可用备份

BACKUP_DIR="/opt/ai-nas/backups"
INSTALL_DIR="/opt/ai-nas"
SERVICE="ai-nas-arm"

echo "═══════════════════════════════════════"
echo " nastools v1.1 — 一键回滚"
echo "═══════════════════════════════════════"

if [ -z "$1" ]; then
    echo "用法: sudo bash nastools-rollback.sh <备份文件>"
    echo ""
    echo "可用 arm_server.py 备份（按时间倒序）:"
    ls -lt "$BACKUP_DIR"/arm_server.py.bak.* 2>/dev/null | awk '{print "  " $6, $7, $8, $9, $10}'
    echo ""
    echo "可用 resolv.conf 备份:"
    ls -lt "$BACKUP_DIR"/resolv.conf.bak.* 2>/dev/null | awk '{print "  " $6, $7, $8, $9, $10}'
    exit 0
fi

BAK="$1"
if [ ! -f "$BAK" ]; then
    echo "ERROR: 备份文件不存在: $BAK"
    exit 1
fi

echo "将还原: $BAK"
read -p "确认回滚? (y/N): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "已取消"
    exit 0
fi

if echo "$BAK" | grep -q "arm_server"; then
    cp "$BAK" "$INSTALL_DIR/arm_server.py"
    echo "✓ arm_server.py 已还原"
    systemctl restart $SERVICE 2>/dev/null && echo "✓ 服务已重启" || echo "⚠ 服务重启失败，请手动检查"
elif echo "$BAK" | grep -q "resolv"; then
    cp "$BAK" /etc/resolv.conf
    echo "✓ DNS 已还原"
else
    cp "$BAK" "$INSTALL_DIR/"
    echo "✓ 文件已还原"
fi

echo ""
echo "✓ 回滚完成"
"""

# ══════════════════════════════════════════════════════════════════
# 卸载脚本（v1.1 安全底线：保留数据，可选清数据）
# ══════════════════════════════════════════════════════════════════

NAS_UNINSTALL_SCRIPT = r"""#!/bin/bash
# nastools v1.1 — 安全卸载脚本
#   • 默认：停止服务 + 删除程序，保留 /opt/ai-nas 和数据
#   • --all：删除所有内容（含数据，不可恢复）

SERVICE="ai-nas-arm"
INSTALL_DIR="/opt/ai-nas"

echo "═══════════════════════════════════════"
echo " nastools v1.1 — 安全卸载"
echo "═══════════════════════════════════════"

# 停止服务
if systemctl is-active --quiet $SERVICE 2>/dev/null; then
    echo "停止服务..."
    systemctl stop $SERVICE || true
    systemctl disable $SERVICE 2>/dev/null || true
    rm -f /etc/systemd/system/$SERVICE.service
    systemctl daemon-reload
fi

if [ "$1" = "--all" ]; then
    echo ""
    echo "⚠ 警告: 将删除所有内容，包括数据目录"
    read -p "确认删除? (输入大写 YES 确认): " CONFIRM
    if [ "$CONFIRM" = "YES" ]; then
        rm -rf /opt/ai-nas
        echo "✓ 已删除全部内容"
    else
        echo "已取消"
    fi
else
    echo ""
    echo "默认模式：保留 /opt/ai-nas（程序）和数据目录"
    echo "如需完全删除，使用: sudo bash nastools-uninstall.sh --all"
fi

echo ""
echo "✓ 卸载完成"
"""


# ══════════════════════════════════════════════════════════════════
# FIX_SCRIPTS — GUI 修复按钮调用字典
# 注意：v1.1 后所有检测类修复走 nastool fixes/（execute_fix）
#       本字典仅用于 DNS 追加（nastool fixes/config_dns 对应）
# ══════════════════════════════════════════════════════════════════

FIX_SCRIPTS = {
    # (script, title, risk_warning)
    "config_dns": (
        DNS_FIX_SCRIPT,
        "修复 DNS（追加模式）",
        "⚠ 低风险：仅追加 nameserver，已有配置不受影响",
    ),
    "dns_rollback": (
        DNS_ROLLBACK_SCRIPT,
        "回滚 DNS",
        "⚠ 低风险：恢复 resolv.conf 备份",
    ),
    "deploy_nas": (
        NAS_DEPLOY_SCRIPT,
        "部署 NAS 系统",
        "🔴 极高风险：覆盖程序文件 + 重启服务，请提前备份",
    ),
    "rollback_nas": (
        NAS_ROLLBACK_SCRIPT,
        "回滚 NAS 版本",
        "🟠 高风险：替换 arm_server.py",
    ),
    "uninstall_nas": (
        NAS_UNINSTALL_SCRIPT,
        "安全卸载 NAS",
        "🟠 高风险：停止并移除服务",
    ),
}
