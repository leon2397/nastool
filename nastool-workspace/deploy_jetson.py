# -*- coding: utf-8 -*-
"""
Jetson Xavier NX 部署脚本 - nastool v4.0.0
用于在 Jetson 设备上部署 nastool v4.0.0 模块化版本

使用方法：
    python deploy_jetson.py --host 192.168.1.123 --user nvidia

依赖：
    pip install paramiko
"""

import argparse
import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path


def run_local_command(cmd, timeout=30):
    """运行本地命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timeout"
    except Exception as e:
        return -1, "", str(e)


def create_deployment_script():
    """创建在 Jetson 上运行的部署脚本"""
    return '''#!/bin/bash
# nastool v4.0.0 Jetson 部署脚本
# 此脚本在 Jetson 设备上运行

set -e

echo "========== nastool v4.0.0 Jetson 部署脚本 ==========""
echo "开始时间: $(date)"

# 1. 检查 Python 版本
echo "[1/7] 检查 Python 版本..."
python3 --version || { echo "Python3 未安装"; exit 1; }

# 2. 创建 nastool 目录
echo "[2/7] 创建安装目录..."
NASTOOL_DIR="$HOME/nastool-v4.0.0"
mkdir -p "$NASTOOL_DIR"
cd "$NASTOOL_DIR"

# 3. 安装依赖
echo "[3/7] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv libopenblas-base || true

# 4. 创建 Python 虚拟环境（推荐但可选）
# echo "[4/7] 创建虚拟环境..."
# python3 -m venv venv
# source venv/bin/activate

# 5. 安装 nastool 模块（ editable 模式）
echo "[4/7] 安装 nastool v4.0.0 模块..."
pip3 install --user -e nastool-common -q || true
pip3 install --user -e nastool-core -q || true
pip3 install --user -e nastool-adapters -q || true
pip3 install --user -e nastool-reporters -q || true
pip3 install --user -e nastool-fixes -q || true
pip3 install --user -e nastool-cli -q || true

# 6. 配置 PATH（如果需要）
echo "[5/7] 检查 nastool 命令..."
if command -v nastool &> /dev/null; then
    echo "nastool 命令已可用: $(which nastool)"
else
    echo "WARNING: nastool 命令不在 PATH 中"
    echo "请添加以下内容到 ~/.bashrc:"
    echo 'export PATH="$HOME/.local/bin:$PATH"'
fi

# 7. 验证安装
echo "[6/7] 验证安装..."
python3 -c "import nastool_core; print(f'nastool_core 版本: {nastool_core.__version__}')" 2>/dev/null || echo "nastool_core 导入失败"
python3 -c "import nastool_adapters; print(f'nastool_adapters 版本: {nastool_adapters.__version__}')" 2>/dev/null || echo "nastool_adapters 导入失败"

# 8. CUDA 环境配置
echo "[7/7] CUDA 环境检查..."
if [ -f /usr/local/cuda/bin/nvcc ]; then
    echo "CUDA 已安装: /usr/local/cuda"
elif [ -f /usr/local/cuda-11.4/bin/nvcc ]; then
    echo "CUDA 11.4 已安装: /usr/local/cuda-11.4"
    echo "请在 ~/.bashrc 中添加: export PATH=/usr/local/cuda-11.4/bin:$PATH"
else
    echo "CUDA 未在标准路径中找到"
fi

echo ""
echo "========== 部署完成 =========="
echo "结束时间: $(date)"
echo ""
echo "常用命令："
echo "  nastool --version          # 查看版本"
echo "  nastool --mock healthy     # Mock 测试"
echo "  nastool --full            # 真实设备检测"
echo ""
echo "如果 nastool 命令找不到，请运行："
echo '  export PATH="$HOME/.local/bin:$PATH"'
echo "或重新登录终端"
'''


def create_scp_script(host, user, local_path, remote_path, password=None):
    """创建 SCP 上传脚本"""
    script = f'''#!/bin/bash
# SCP 上传脚本 - 将本地文件上传到 Jetson
# 主机: {user}@{host}
# 本地路径: {local_path}
# 远程路径: {remote_path}

set -e

SCP_CMD="scp"
if [ -n "{password}" ]; then
    # 使用 sshpass（如果可用）
    if command -v sshpass &> /dev/null; then
        SCP_CMD="sshpass -p '{password}' scp"
    else
        echo "WARNING: sshpass 未安装，密码将被忽略"
    fi
fi

$SCP_CMD -r {local_path} {user}@{host}:{remote_path}
echo "上传完成: {local_path} -> {user}@{host}:{remote_path}"
'''


def deploy_to_jetson(host, user, password=None, key_file=None):
    """部署 nastool 到 Jetson 设备"""
    print(f"准备部署 nastool v4.0.0 到 Jetson ({user}@{host})...")

    # 1. 生成部署脚本
    script_content = create_deployment_script()
    script_path = os.path.join(tempfile.gettempdir(), "nastool_deploy_jetson.sh")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    print(f"[1/3] 部署脚本已生成: {script_path}")

    # 2. 上传部署脚本到 Jetson
    print(f"[2/3] 上传部署脚本到 Jetson...")
    if password:
        upload_cmd = f'sshpass -p "{password}" scp -o StrictHostKeyChecking=no {script_path} {user}@{host}:~/nastool_deploy.sh'
    elif key_file:
        upload_cmd = f'scp -i "{key_file}" -o StrictHostKeyChecking=no {script_path} {user}@{host}:~/nastool_deploy.sh'
    else:
        upload_cmd = f'scp -o StrictHostKeyChecking=no {script_path} {user}@{host}:~/nastool_deploy.sh'

    ret, out, err = run_local_command(upload_cmd, timeout=60)
    if ret != 0:
        print(f"上传失败: {err}")
        return False

    print(f"[3/3] 在 Jetson 上执行部署脚本...")
    ssh_cmd = f'ssh -o StrictHostKeyChecking=no {user}@{host} "chmod +x ~/nastool_deploy.sh && bash ~/nastool_deploy.sh"'
    if password:
        ssh_cmd = f'sshpass -p "{password}" ' + ssh_cmd

    ret, out, err = run_local_command(ssh_cmd, timeout=600)
    print(out)
    if err:
        print(f"警告/错误: {err}")

    return ret == 0


def main():
    parser = argparse.ArgumentParser(description="Jetson nastool v4.0.0 部署脚本")
    parser.add_argument("--host", default="192.168.1.123", help="Jetson IP 地址")
    parser.add_argument("--user", default="nvidia", help="Jetson 用户名")
    parser.add_argument("--password", help="SSH 密码（可选，建议使用密钥）")
    parser.add_argument("--key", help="SSH 密钥文件路径（可选）")
    parser.add_argument("--local-dir", default=None, help="本地 nastool 目录路径")

    args = parser.parse_args()

    print("=" * 60)
    print(" nastool v4.0.0 Jetson 部署工具")
    print("=" * 60)

    # 检查本地 nastool 目录
    if args.local_dir:
        nastool_dir = args.local_dir
    else:
        # 尝试查找 nastool 目录
        possible_dirs = [
            os.path.join(os.path.dirname(__file__), "..", "nastool-v4.0.0"),
            os.path.join(os.getcwd(), "nastool-v4.0.0"),
            "D:\\project\\nastool7\\nastool-v4.0.0",
        ]
        nastool_dir = None
        for d in possible_dirs:
            if os.path.exists(d):
                nastool_dir = d
                break

    if not nastool_dir or not os.path.exists(nastool_dir):
        print(f"错误: 找不到 nastool-v4.0.0 目录")
        print(f"请使用 --local-dir 指定本地 nastool 目录")
        return 1

    print(f"本地 nastool 目录: {nastool_dir}")

    # 部署到 Jetson
    success = deploy_to_jetson(
        host=args.host,
        user=args.user,
        password=args.password,
        key_file=args.key
    )

    if success:
        print("\n部署成功!")
        print(f"现在可以在 Jetson 上运行: ssh {args.user}@{args.host}")
        print("然后执行: nastool --version 或 nastool --mock healthy")
    else:
        print("\n部署失败，请检查错误信息")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
