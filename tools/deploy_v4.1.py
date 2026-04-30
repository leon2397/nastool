#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NASTool V4.1 部署脚本
目标设备: 192.168.1.123
部署目录: ~/nastool
"""

import subprocess
import sys
import os
from pathlib import Path

TARGET_HOST = "192.168.1.123"
TARGET_USER = "nvidia"
DEPLOY_DIR = "~/nastool"
LOCAL_DIR = Path(__file__).parent

def log_info(msg):
    print(f"[INFO] {msg}")

def log_warn(msg):
    print(f"[WARN] {msg}")

def log_error(msg):
    print(f"[ERROR] {msg}")

def log_step(msg):
    print(f"[STEP] {msg}")

def run_ssh(cmd, check=True):
    """在远程设备上执行 SSH 命令"""
    full_cmd = ['ssh', f'{TARGET_USER}@{TARGET_HOST}', cmd]
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        log_error(f"SSH 命令失败: {cmd}")
        log_error(f"错误: {result.stderr}")
        return None
    return result.stdout

def run_scp(source, dest, recursive=False):
    """执行 SCP 复制"""
    cmd = ['scp']
    if recursive:
        cmd.append('-r')
    cmd.extend([source, f'{TARGET_USER}@{TARGET_HOST}:{dest}'])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def main():
    log_step("============================================")
    log_step("  NASTool V4.1 部署脚本")
    log_step("============================================")
    log_info(f"目标设备: {TARGET_HOST}")
    log_info(f"部署目录: {DEPLOY_DIR}")
    log_info(f"本地目录: {LOCAL_DIR}")

    # Step 1: 检查连接
    log_step("[1/6] 检查目标设备连接...")
    result = subprocess.run(['ping', '-n', '1', '-w', '2000', TARGET_HOST], capture_output=True)
    if result.returncode != 0:
        log_error(f"无法连接到目标设备 {TARGET_HOST}")
        sys.exit(1)
    log_info("目标设备可连接")

    # Step 2: 备份旧版本
    log_step("[2/6] 备份旧版本...")
    backup_cmd = 'if [ -d ~/nastool ]; then BACKUP_DIR=~/nastool-backup-$(date +%Y%m%d_%H%M%S); mv ~/nastool ${BACKUP_DIR}; echo "已备份到: ${BACKUP_DIR}"; fi; mkdir -p ~/nastool'
    output = run_ssh(backup_cmd, check=False)
    if output:
        log_info(output.strip())
    log_info("备份完成")

    # Step 3: 复制核心模块
    log_step("[3/6] 复制核心模块到目标设备...")
    
    MODULES = [
        "nastool-common",
        "nastool-core",
        "nastool-adapters",
        "nastool-cli",
        "nastool-reporters",
        "nastool-fixes"
    ]

    for module in MODULES:
        module_path = LOCAL_DIR / module
        if module_path.exists():
            log_info(f"复制 {module}...")
            if not run_scp(str(module_path), DEPLOY_DIR, recursive=True):
                log_warn(f"复制 {module} 可能有问题")
        else:
            log_warn(f"模块 {module} 不存在，跳过")

    log_info("核心模块复制完成")

    # Step 4: 复制测试和部署文件
    log_step("[4/6] 复制测试和部署文件...")
    
    DIRS = ["tests", "deploy", "docs", "data"]
    for dir_name in DIRS:
        dir_path = LOCAL_DIR / dir_name
        if dir_path.exists():
            log_info(f"复制 {dir_name}/")
            run_scp(str(dir_path), DEPLOY_DIR, recursive=True)

    log_info("附加文件复制完成")

    # Step 5: 创建启动脚本
    log_step("[5/6] 创建启动脚本...")

    # 创建 run.sh
    run_script = '''#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="${SCRIPT_DIR}/nastool-cli:${SCRIPT_DIR}/nastool-common:${SCRIPT_DIR}/nastool-core:${SCRIPT_DIR}/nastool-reporters:${SCRIPT_DIR}/nastool-fixes:${SCRIPT_DIR}/nastool-adapters"
python3 -m nastool_cli.main "$@"
'''

    # 创建 diagnose.sh
    diagnose_script = '''#!/bin/bash
cd "$(dirname "$0")"
./run.sh diagnose "$@"
'''

    # 创建 version.sh
    version_script = '''#!/bin/bash
cd "$(dirname "$0")"
./run.sh --version
'''

    # 使用 echo 创建远程脚本
    scripts = {
        "run.sh": run_script,
        "diagnose.sh": diagnose_script,
        "version.sh": version_script
    }

    for script_name, content in scripts.items():
        # 使用 base64 编码避免转义问题
        import base64
        encoded = base64.b64encode(content.encode()).decode()
        create_cmd = f'echo "{encoded}" | base64 -d > ~/nastool/{script_name} && chmod +x ~/nastool/{script_name}'
        run_ssh(create_cmd, check=False)

    log_info("启动脚本创建完成")

    # Step 6: 验证部署
    log_step("[6/6] 验证部署...")

    verify_cmd = 'cd ~/nastool && echo "=== 文件列表 ===" && ls -la && echo "" && echo "=== 模块检查 ===" && for dir in nastool-common nastool-core nastool-adapters nastool-cli nastool-reporters nastool-fixes; do if [ -d "$dir" ]; then echo "[OK] $dir"; else echo "[MISSING] $dir"; fi; done && echo "" && echo "=== 脚本检查 ===" && for script in run.sh diagnose.sh version.sh; do if [ -x "$script" ]; then echo "[OK] $script"; else echo "[MISSING] $script"; fi; done'
    output = run_ssh(verify_cmd, check=False)
    if output:
        print(output)

    log_step("============================================")
    log_step("  NASTool V4.1 部署完成！")
    log_step("============================================")
    log_info(f"部署目录: {DEPLOY_DIR}")
    log_info("")
    log_info("使用方法:")
    log_info(f"  ssh {TARGET_USER}@{TARGET_HOST}")
    log_info(f"  cd {DEPLOY_DIR}")
    log_info("")
    log_info("  # 查看版本")
    log_info("  ./version.sh")
    log_info("")
    log_info("  # 运行诊断")
    log_info("  ./diagnose.sh")
    log_info("")
    log_info("  # 使用完整功能")
    log_info("  ./run.sh --help")
    log_info("")
    log_step("============================================")

if __name__ == "__main__":
    main()
