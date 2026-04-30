#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

# 更新启动脚本
run_sh = """#!/bin/bash
TOOL_DIR="/root/tool"

echo "=================================="
echo "  NASTool 测试工具 v4.1"
echo "  昇腾设备诊断测试"
echo "=================================="

# 设置PYTHONPATH（包含本地依赖）
export PYTHONPATH="$TOOL_DIR/dep/lib:$TOOL_DIR/bin/nastool-cli:$TOOL_DIR/bin/nastool-common:$TOOL_DIR/bin/nastool-core:$TOOL_DIR/bin/nastool-adapters:$TOOL_DIR/bin/nastool-reporters:$TOOL_DIR/bin/nastool-fixes"

# 使用系统Python运行
cd $TOOL_DIR/bin/nastool-cli
python3 -m nastool_cli.main --full --no-color

# 保存JSON结果
mkdir -p $TOOL_DIR/log
python3 -m nastool_cli.main --full --json --no-color -o $TOOL_DIR/log/diagnosis_result.json

echo ""
echo "✅ 测试完成！"
echo "结果已保存到: $TOOL_DIR/log/"
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

sftp = client.open_sftp()
with sftp.file('/root/tool/run.sh', 'w') as f:
    f.write(run_sh)
client.exec_command("chmod +x /root/tool/run.sh")

sftp.close()
client.close()

print("✓ 启动脚本已更新")
