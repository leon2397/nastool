#!/bin/bash
# nastool 一键部署脚本
# 用法: ./deploy.sh <nas_ip> <nas_user> <nas_type>
# 示例: ./deploy.sh 192.168.1.100 admin synology

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 参数检查
if [ $# -lt 2 ]; then
    echo -e "${YELLOW}用法:${NC}"
    echo "  ./deploy.sh <nas_ip> <nas_user> [nas_type]"
    echo ""
    echo -e "${YELLOW}示例:${NC}"
    echo "  ./deploy.sh 192.168.1.100 admin synology"
    echo "  ./deploy.sh 192.168.1.101 admin qnap"
    echo "  ./deploy.sh 192.168.1.123 nvidia jetson"
    exit 1
fi

NAS_IP=$1
NAS_USER=$2
NAS_TYPE=${3:-"synology"}

# 发布包路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RELEASE_DIR="$(dirname "$SCRIPT_DIR")/_releases"

# 找最新的发布包
LATEST_RELEASE=$(ls -t "$RELEASE_DIR"/nastool-v3.0.7-*.zip 2>/dev/null | head -1)

if [ -z "$LATEST_RELEASE" ]; then
    echo -e "${RED}错误: 未找到发布包${NC}"
    echo "请先运行: python arm_diagnose.py --build-release"
    exit 1
fi

RELEASE_NAME=$(basename "$LATEST_RELEASE" .zip)
RELEASE_ZIP="$LATEST_RELEASE"

echo -e "${GREEN}=== nastool 部署脚本 ===${NC}"
echo ""
echo "NAS IP:     $NAS_IP"
echo "NAS 用户:   $NAS_USER"
echo "NAS 类型:   $NAS_TYPE"
echo "发布包:     $RELEASE_ZIP"
echo ""

# 测试连接
echo -e "${YELLOW}测试 SSH 连接...${NC}"
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$NAS_USER@$NAS_IP" "echo OK" 2>/dev/null; then
    echo -e "${RED}SSH 连接失败${NC}"
    echo "请确保:"
    echo "  1. NAS 设备在线"
    echo "  2. SSH 服务已启用"
    echo "  3. 用户名密码正确"
    exit 1
fi
echo -e "${GREEN}SSH 连接成功${NC}"
echo ""

# 上传发布包
echo -e "${YELLOW}上传发布包...${NC}"
REMOTE_DIR="/tmp/nastool-deploy"
ssh "$NAS_USER@$NAS_IP" "mkdir -p $REMOTE_DIR"
scp "$RELEASE_ZIP" "$NAS_USER@$NAS_IP:$REMOTE_DIR/"
echo -e "${GREEN}上传完成${NC}"
echo ""

# 解压并安装
echo -e "${YELLOW}解压并安装...${NC}"
ssh "$NAS_USER@$NAS_IP" << EOF
    set -e
    cd $REMOTE_DIR
    unzip -o "$RELEASE_NAME.zip"
    
    # 创建安装目录
    INSTALL_DIR="\$HOME/nastool"
    rm -rf "\$INSTALL_DIR"
    mv "$RELEASE_NAME" "\$INSTALL_DIR"
    
    # 清理临时文件
    rm -rf $REMOTE_DIR
    
    echo ""
    echo "安装目录: \$INSTALL_DIR"
    echo ""
    echo "运行命令:"
    echo "  cd \$INSTALL_DIR"
    echo "  python3 arm_diagnose.py --nas $NAS_TYPE"
EOF

echo ""
echo -e "${GREEN}=== 部署完成 ===${NC}"
echo ""
echo "SSH 登录并运行:"
echo "  ssh $NAS_USER@$NAS_IP"
echo "  cd ~/nastool"
echo "  python3 arm_diagnose.py --nas $NAS_TYPE"
