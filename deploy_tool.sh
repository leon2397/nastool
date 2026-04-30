#!/bin/bash
# NASTool 昇腾设备测试部署脚本
# 单目录隔离方案 - 不污染系统

TOOL_DIR="/root/tool"

echo "=================================="
echo "  NASTool 测试工具部署"
echo "  所有文件将安装到: $TOOL_DIR"
echo "  卸载: rm -rf $TOOL_DIR"
echo "=================================="

# 创建目录结构
mkdir -p $TOOL_DIR/{test_case,bin,dep,log,temp,doc}

# 创建一键卸载脚本
cat > $TOOL_DIR/uninstall.sh << 'EOF'
#!/bin/bash
TOOL_DIR="/root/tool"

echo "=================================="
echo "  测试工具 - 一键卸载"
echo "  所有文件将被彻底删除"
echo "  系统不会留下任何痕迹"
echo "=================================="

read -p "确定卸载？(y/n): " ans
if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    rm -rf $TOOL_DIR
    echo "✅ 卸载完成！系统已恢复初始状态。"
else
    echo "❌ 取消卸载。"
fi
EOF
chmod +x $TOOL_DIR/uninstall.sh

# 创建虚拟环境
echo "创建Python虚拟环境..."
python3 -m venv $TOOL_DIR/dep/venv

# 激活虚拟环境并安装依赖
echo "安装依赖..."
source $TOOL_DIR/dep/venv/bin/activate
pip install paramiko requests psutil

# 上传NASTool模块
echo "上传NASTool模块..."
git clone https://github.com/your-repo/nastool.git $TOOL_DIR/bin/nastool || {
    # 如果git不可用，直接复制本地文件
    echo "Git不可用，使用本地文件..."
    mkdir -p $TOOL_DIR/bin/nastool
    # 这里可以添加scp或其他方式上传
}

# 创建启动脚本
cat > $TOOL_DIR/run.sh << 'EOF'
#!/bin/bash
TOOL_DIR="/root/tool"

echo "=================================="
echo "  NASTool 测试工具"
echo "  设备诊断测试"
echo "=================================="

# 激活虚拟环境
source $TOOL_DIR/dep/venv/bin/activate

# 运行诊断
cd $TOOL_DIR/bin/nastool
python -m nastool_cli.main --full

# 保存结果
mkdir -p $TOOL_DIR/log
python -m nastool_cli.main --full --json -o $TOOL_DIR/log/diagnosis_result.json

echo ""
echo "✅ 测试完成！"
echo "结果已保存到: $TOOL_DIR/log/"
EOF
chmod +x $TOOL_DIR/run.sh

# 创建BUG记录文件
cat > $TOOL_DIR/doc/bug_list.md << 'EOF'
# NASTool 昇腾设备测试 BUG 记录

## 测试环境
- 设备型号: Ascend 310B1 (davinci-mini)
- 操作系统: Ubuntu 22.04 LTS
- 架构: aarch64
- 测试版本: NASTool v4.1

## BUG列表

| 编号 | 严重等级 | 描述 | 发现时间 | 状态 |
|------|---------|------|---------|------|
| BUG-001 | | | | 待确认 |
| BUG-002 | | | | 待确认 |

## 备注

EOF

echo ""
echo "✅ 部署完成！"
echo ""
echo "使用方法:"
echo "  cd $TOOL_DIR"
echo "  ./run.sh          # 运行测试"
echo "  ./uninstall.sh    # 一键卸载"
echo ""
echo "测试结果保存在: $TOOL_DIR/log/"
echo "BUG记录文件: $TOOL_DIR/doc/bug_list.md"
