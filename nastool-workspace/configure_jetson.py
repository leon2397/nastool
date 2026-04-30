# -*- coding: utf-8 -*-
"""
Jetson 环境配置脚本 - 自动配置 CUDA PATH 和验证 GPU 检测
用于解决 BUG-010 (nvcc 不在 PATH) 和 BUG-011 (nvidia-smi 不存在)

使用方法：
    python configure_jetson.py --host 192.168.1.123 --user nvidia

或在 Jetson 本地运行：
    python configure_jetson.py --local
"""

import argparse
import sys
import os
import subprocess
import tempfile


def run_command(cmd, timeout=30, host=None, user=None, password=None):
    """运行命令（本地或远程）"""
    if host and user:
        ssh_cmd = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{host}'
        if password:
            ssh_cmd = f'sshpass -p "{password}" ' + ssh_cmd
        full_cmd = f'{ssh_cmd} "{cmd}"'
    else:
        full_cmd = cmd

    try:
        result = subprocess.run(
            full_cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timeout"
    except Exception as e:
        return -1, "", str(e)


def create_jetson_config_script():
    """创建在 Jetson 上运行的配置脚本"""
    return '''#!/bin/bash
# Jetson 环境配置脚本
# 自动配置 CUDA PATH 并验证 GPU 检测

set -e

echo "========== Jetson 环境配置 =========="
echo "开始时间: $(date)"
echo ""

# 1. 检测 CUDA 安装位置
echo "[1/5] 检测 CUDA 安装位置..."
CUDA_PATHS=(
    "/usr/local/cuda"
    "/usr/local/cuda-11.4"
    "/usr/local/cuda-12.2"
)

CUDA_FOUND=""
for path in "${CUDA_PATHS[@]}"; do
    if [ -f "$path/bin/nvcc" ]; then
        CUDA_FOUND="$path"
        echo "找到 CUDA: $path"
        break
    fi
done

if [ -z "$CUDA_FOUND" ]; then
    echo "警告: 未找到 CUDA 安装"
else
    echo "CUDA 路径: $CUDA_FOUND"
fi

# 2. 配置 .bashrc
echo ""
echo "[2/5] 配置 ~/.bashrc..."

BASHRC_LINE="export PATH=$CUDA_FOUND/bin:$PATH"
if [ -n "$CUDA_FOUND" ]; then
    if ! grep -q "$CUDA_FOUND/bin" ~/.bashrc 2>/dev/null; then
        echo "" >> ~/.bashrc
        echo "# CUDA 环境配置 (nastool)" >> ~/.bashrc
        echo "export PATH=$CUDA_FOUND/bin:\\$PATH" >> ~/.bashrc
        echo "export LD_LIBRARY_PATH=$CUDA_FOUND/lib64:\\$LD_LIBRARY_PATH" >> ~/.bashrc
        echo "已添加 CUDA PATH 到 ~/.bashrc"
    else
        echo "CUDA PATH 已配置"
    fi
fi

# 3. 验证 GPU 检测
echo ""
echo "[3/5] 验证 GPU 检测..."

# 检查 nvidia-smi
echo "  - nvidia-smi: $(which nvidia-smi 2>/dev/null || echo '不存在 (Jetson 正常)')"

# 检查 /dev/nvhost-* 设备
echo "  - /dev/nvhost-gpu: $([ -e /dev/nvhost-gpu ] && echo '存在' || echo '不存在')"
echo "  - /dev/nvhost-as-gpu: $([ -e /dev/nvhost-as-gpu ] && echo '存在' || echo '不存在')"

# 检查 tegrastats
echo "  - tegrastats: $(which tegrastats 2>/dev/null || echo '不存在')"

# 检查 /proc/driver/nvidia
echo "  - /proc/driver/nvidia/gpus/: $([ -d /proc/driver/nvidia/gpus/ ] && ls /proc/driver/nvidia/gpus/ 2>/dev/null || echo '不存在')"

# 检查设备树模型
if [ -f /proc/device-tree/model ]; then
    echo "  - 设备型号: $(cat /proc/device-tree/model)"
fi

# 4. 尝试运行 nastool GPU 检测
echo ""
echo "[4/5] 测试 nastool GPU 检测..."
if command -v nastool &> /dev/null; then
    echo "nastool 命令已安装: $(which nastool)"
    # nastool gpu_detected 或类似命令
    nastool --mock healthy 2>/dev/null | head -20 || echo "nastool 运行失败"
elif python3 -c "import nastool_core" 2>/dev/null; then
    echo "nastool_core 模块已安装"
    python3 -c "
from nastool_core.checks.ai.gpu_detected import gpu_detected
from nastool_core.checks.decorators import CheckContext
ctx = CheckContext()
result = gpu_detected(ctx)
print(f'GPU 检测结果: {result.passed}')
print(f'消息: {result.message}')
" 2>/dev/null || echo "GPU 检测模块运行失败"
else
    echo "nastool 未安装，跳过"
fi

# 5. 显示当前 PATH
echo ""
echo "[5/5] 当前 PATH..."
echo "$PATH" | tr ':' '\\n' | head -10

echo ""
echo "========== 配置完成 =========="
echo "结束时间: $(date)"
echo ""
echo "建议操作:"
echo "1. 重新加载 bashrc: source ~/.bashrc"
echo "2. 验证 nvcc: nvcc --version"
echo "3. 运行 nastool: nastool --mock healthy"
'''


def configure_local():
    """本地 Jetson 配置"""
    print("正在配置本地 Jetson 环境...")

    script_content = create_jetson_config_script()
    script_path = os.path.join(tempfile.gettempdir(), "configure_jetson.sh")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    print(f"配置脚本已生成: {script_path}")
    print("正在执行配置脚本...")

    ret, out, err = run_command(f"bash {script_path}", timeout=120)

    print(out)
    if err:
        print(f"警告: {err}")

    return ret == 0


def configure_remote(host, user, password=None):
    """远程 Jetson 配置"""
    print(f"正在配置远程 Jetson 环境 ({user}@{host})...")

    script_content = create_jetson_config_script()
    script_path = os.path.join(tempfile.gettempdir(), "configure_jetson.sh")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    # 上传脚本
    print("[1/2] 上传配置脚本...")
    if password:
        ret, out, err = run_command(f"echo '{password}' | sshpass -p '{password}' scp -o StrictHostKeyChecking=no {script_path} {user}@{host}:~/configure_jetson.sh", timeout=60)
    else:
        ret, out, err = run_command(f"scp -o StrictHostKeyChecking=no {script_path} {user}@{host}:~/configure_jetson.sh", timeout=60)

    if ret != 0:
        print(f"上传失败: {err}")
        return False

    # 执行脚本
    print("[2/2] 执行配置脚本...")
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no {user}@{host} 'chmod +x ~/configure_jetson.sh && bash ~/configure_jetson.sh'"
    if password:
        ssh_cmd = f'sshpass -p "{password}" ' + ssh_cmd

    ret, out, err = run_command(ssh_cmd, timeout=120, host=host, user=user, password=password)

    print(out)
    if err:
        print(f"警告: {err}")

    return ret == 0


def main():
    parser = argparse.ArgumentParser(description="Jetson 环境配置脚本")
    parser.add_argument("--host", default="192.168.1.123", help="Jetson IP 地址")
    parser.add_argument("--user", default="nvidia", help="Jetson 用户名")
    parser.add_argument("--password", help="SSH 密码（可选）")
    parser.add_argument("--local", action="store_true", help="本地 Jetson（不通过 SSH）")

    args = parser.parse_args()

    print("=" * 60)
    print(" Jetson 环境配置工具")
    print(" (解决 BUG-010 nvcc PATH 和 BUG-011 GPU 检测)")
    print("=" * 60)

    if args.local:
        success = configure_local()
    else:
        success = configure_remote(args.host, args.user, args.password)

    if success:
        print("\n配置完成!")
    else:
        print("\n配置失败，请检查错误信息")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
