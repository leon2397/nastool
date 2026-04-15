#!/bin/bash
# nastool 一键安装脚本
# 用法: curl -fsSL https://your-domain/nastool/install.sh | bash

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 版本
VERSION="3.0.7"
DOWNLOAD_URL="https://你的域名/nastool/nastool-v3.0.7.tar.gz"

# 安装目录
INSTALL_DIR="$HOME/nastool"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║     nastool v${VERSION} 安装程序            ║"
echo "║     ARM NAS 设备诊断工具               ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# 检测系统
echo -e "${YELLOW}检测系统环境...${NC}"
ARCH=$(uname -m)
OS=$(uname -s)

if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" && "$ARCH" != "arm64" ]]; then
    echo -e "${RED}警告: 此工具专为 ARM 设备设计${NC}"
    echo "当前架构: $ARCH"
    read -p "是否继续安装? (y/n): " CONTINUE
    if [[ "$CONTINUE" != "y" ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}系统: $OS $ARCH${NC}"

# 检测 Python
echo -e "${YELLOW}检测 Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}错误: 未找到 Python${NC}"
    echo "请先安装 Python 3.8 或更高版本"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}Python: $PYTHON_VERSION${NC}"

# 安装依赖
echo -e "${YELLOW}安装依赖...${NC}"
$PYTHON_CMD -m pip install --user pyyaml psutil 2>/dev/null || {
    echo -e "${YELLOW}部分依赖安装失败，继续安装...${NC}"
}

# 创建安装目录
echo -e "${YELLOW}创建安装目录...${NC}"
mkdir -p "$INSTALL_DIR"

# 下载
echo -e "${YELLOW}下载 nastool...${NC}"
if command -v curl &> /dev/null; then
    curl -fsSL "$DOWNLOAD_URL" -o /tmp/nastool.tar.gz
elif command -v wget &> /dev/null; then
    wget -q "$DOWNLOAD_URL" -O /tmp/nastool.tar.gz
else
    echo -e "${RED}错误: 需要 curl 或 wget${NC}"
    exit 1
fi

# 解压
echo -e "${YELLOW}解压安装...${NC}"
tar -xzf /tmp/nastool.tar.gz -C "$INSTALL_DIR" --strip-components=1

# 设置权限
chmod +x "$INSTALL_DIR/start.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/"*.sh 2>/dev/null || true

# 清理
rm -f /tmp/nastool.tar.gz

# 创建快捷命令
echo -e "${YELLOW}创建快捷命令...${NC}"
cat > "$HOME/.nastool.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
$PYTHON_CMD arm_diagnose.py "\$@"
EOF
chmod +x "$HOME/.nastool.sh"

# 添加到 PATH
if ! grep -q "nastool" "$HOME/.bashrc" 2>/dev/null; then
    echo "" >> "$HOME/.bashrc"
    echo "# nastool shortcut" >> "$HOME/.bashrc"
    echo "alias nastool='$HOME/.nastool.sh'" >> "$HOME/.bashrc"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          安装完成！                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}安装目录:${NC} $INSTALL_DIR"
echo ""
echo -e "${YELLOW}快速开始:${NC}"
echo "  cd $INSTALL_DIR"
echo "  ./start.sh"
echo ""
echo -e "${YELLOW}或使用快捷命令:${NC}"
echo "  source ~/.bashrc"
echo "  nastool"
echo ""
echo -e "${YELLOW}查看帮助:${NC}"
echo "  nastool --help"
echo ""
