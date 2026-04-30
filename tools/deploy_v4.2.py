#!/usr/bin/env python3
"""
NASTool v4.2 一键部署脚本
支持本地部署和远程部署
"""

import os
import sys
import argparse
import subprocess
import shutil
import platform
from pathlib import Path

# 添加项目路径到PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nastool_common.utils.offline_deps import OfflineDependencyManager

def parse_args():
    parser = argparse.ArgumentParser(description='NASTool v4.2 一键部署脚本')
    parser.add_argument('--target', '-t', default='local', 
                        help='部署目标: local(本地) 或 remote(远程)')
    parser.add_argument('--host', '-H', default=None, help='远程主机IP')
    parser.add_argument('--user', '-u', default='root', help='远程主机用户名')
    parser.add_argument('--password', '-P', default=None, help='远程主机密码')
    parser.add_argument('--port', '-p', default=22, type=int, help='SSH端口')
    parser.add_argument('--install-dir', '-d', default='/root/tool', 
                        help='安装目录')
    parser.add_argument('--mode', '-m', default='quick', 
                        choices=['quick', 'full'], help='部署模式')
    parser.add_argument('--skip-deps', action='store_true', help='跳过依赖安装')
    return parser.parse_args()

def deploy_local(args):
    """本地部署"""
    print("🚀 开始本地部署 NASTool v4.2")
    
    install_dir = Path(args.install_dir)
    install_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建目录结构
    create_directory_structure(install_dir)
    
    # 复制核心模块
    copy_modules(install_dir)
    
    # 安装依赖
    if not args.skip_deps:
        install_dependencies(install_dir)
    
    # 创建启动脚本
    create_run_script(install_dir)
    
    # 创建卸载脚本
    create_uninstall_script(install_dir)
    
    print(f"\n✅ 本地部署完成!")
    print(f"📂 安装目录: {install_dir}")
    print(f"🚀 启动命令: cd {install_dir} && ./run.sh")

def deploy_remote(args):
    """远程部署"""
    if not args.host:
        print("❌ 远程部署需要指定 --host 参数")
        sys.exit(1)
    
    print(f"🚀 开始远程部署到 {args.host}")
    
    try:
        import paramiko
    except ImportError:
        print("⚠️ 需要安装 paramiko 库")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'paramiko'], check=True)
        import paramiko
    
    # 连接远程主机
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(
            hostname=args.host,
            port=args.port,
            username=args.user,
            password=args.password,
            timeout=30
        )
        print("✅ SSH连接成功")
        
        # 创建远程目录结构
        exec_command(client, f"mkdir -p {args.install_dir}/{{bin,dep,log,temp,test_case,doc}}")
        
        # 上传核心模块
        upload_modules(client, args.install_dir)
        
        # 安装依赖
        if not args.skip_deps:
            install_remote_dependencies(client, args.install_dir)
        
        # 创建启动脚本
        create_remote_run_script(client, args.install_dir)
        
        # 创建卸载脚本
        create_remote_uninstall_script(client, args.install_dir)
        
        print(f"\n✅ 远程部署完成!")
        print(f"📂 安装目录: {args.install_dir}")
        print(f"🚀 启动命令: ssh {args.user}@{args.host} 'cd {args.install_dir} && ./run.sh'")
        
    finally:
        client.close()

def create_directory_structure(base_dir):
    """创建目录结构"""
    dirs = ['bin', 'dep', 'log', 'temp', 'test_case', 'doc']
    for d in dirs:
        (base_dir / d).mkdir(exist_ok=True)
        print(f"📂 创建目录: {base_dir / d}")

def copy_modules(base_dir):
    """复制核心模块"""
    project_root = Path(os.path.dirname(os.path.abspath(__file__)))
    modules = [
        'nastool-cli',
        'nastool-core', 
        'nastool-adapters',
        'nastool-common',
        'nastool-fixes',
        'nastool-reporters'
    ]
    
    target_bin = base_dir / 'bin'
    
    for module in modules:
        src = project_root / module
        dst = target_bin / module
        
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"📦 复制模块: {module}")
        else:
            print(f"⚠️ 模块不存在: {module}")

def upload_modules(client, remote_dir):
    """上传模块到远程主机"""
    sftp = client.open_sftp()
    project_root = Path(os.path.dirname(os.path.abspath(__file__)))
    modules = [
        'nastool-cli',
        'nastool-core', 
        'nastool-adapters',
        'nastool-common',
        'nastool-fixes',
        'nastool-reporters'
    ]
    
    for module in modules:
        src = project_root / module
        dst = f"{remote_dir}/bin/{module}"
        
        if src.exists():
            # 检查目录是否存在，如果不存在则创建
            try:
                sftp.stat(dst)
            except FileNotFoundError:
                sftp.mkdir(dst)
            upload_directory(sftp, src, dst)
            print(f"📦 上传模块: {module}")
        else:
            print(f"⚠️ 模块不存在: {module}")
    
    sftp.close()

def upload_directory(sftp, local_dir, remote_dir):
    """递归上传目录"""
    local_dir = Path(local_dir)
    for item in local_dir.iterdir():
        remote_item = f"{remote_dir}/{item.name}"
        if item.is_dir():
            # 检查目录是否存在，如果不存在则创建
            try:
                sftp.stat(remote_item)
            except FileNotFoundError:
                sftp.mkdir(remote_item)
            upload_directory(sftp, item, remote_item)
        else:
            sftp.put(str(item), remote_item)

def install_dependencies(base_dir):
    """安装依赖"""
    dep_manager = OfflineDependencyManager(str(base_dir / 'dep'))
    
    # 先尝试离线安装
    installed, skipped = dep_manager.install_deps_from_offline()
    print(f"\n📦 离线依赖安装完成")
    
    # 设置环境
    dep_manager.setup_env()
    
    return installed

def install_remote_dependencies(client, remote_dir):
    """在远程主机安装依赖"""
    # 检查pip是否可用
    exec_command(client, "pip3 install --upgrade pip")
    
    # 安装核心依赖
    deps = [
        "paramiko>=3.0",
        "pyusb>=1.2",
        "requests>=2.28",
        "websocket-client>=1.0",
        "pydantic>=2.0",
        "rich>=13.0",
        "psutil>=5.9",
        "typing-extensions>=4.0",
        "packaging>=21.0"
    ]
    
    for dep in deps:
        exec_command(client, f"pip3 install {dep}")
    
    print("✅ 依赖安装完成")

def create_run_script(base_dir):
    """创建启动脚本"""
    script = f"""#!/bin/bash
cd "{base_dir}"

# 设置PYTHONPATH
export PYTHONPATH="{base_dir}/bin/nastool-cli:{base_dir}/bin/nastool-core:{base_dir}/bin/nastool-adapters:{base_dir}/bin/nastool-common:{base_dir}/bin/nastool-fixes:{base_dir}/bin/nastool-reporters:{base_dir}/dep/site-packages"

# 设置路径
export PATH="{base_dir}/bin:$PATH"

# 创建日志目录
mkdir -p log

# 执行诊断
echo "🚀 启动 NASTool 诊断..."
python3 -m nastool_cli.main diagnose --output log/diagnosis_result.json

echo "✅ 诊断完成! 结果已保存到 log/diagnosis_result.json"
"""
    
    run_script = base_dir / 'run.sh'
    run_script.write_text(script)
    run_script.chmod(0o755)
    print(f"📜 创建启动脚本: {run_script}")

def create_uninstall_script(base_dir):
    """创建卸载脚本"""
    script = f"""#!/bin/bash
TOOL_DIR="{base_dir}"

echo "=================================="
echo "  NASTool v4.2 - 一键卸载"
echo "  所有文件将被彻底删除"
echo "  系统不会留下任何痕迹"
echo "=================================="

read -p "确定卸载? (y/n): " ans
if [ "$ans" = "y" ]; then
    rm -rf $TOOL_DIR
    echo "✅ 卸载完成! 系统已恢复初始状态。"
else
    echo "❌ 取消卸载。"
fi
"""
    
    uninstall_script = base_dir / 'uninstall.sh'
    uninstall_script.write_text(script)
    uninstall_script.chmod(0o755)
    print(f"📜 创建卸载脚本: {uninstall_script}")

def create_remote_run_script(client, remote_dir):
    """在远程主机创建启动脚本"""
    script = f"""#!/bin/bash
cd "{remote_dir}"

# 设置PYTHONPATH
export PYTHONPATH="{remote_dir}/bin/nastool-cli:{remote_dir}/bin/nastool-core:{remote_dir}/bin/nastool-adapters:{remote_dir}/bin/nastool-common:{remote_dir}/bin/nastool-fixes:{remote_dir}/bin/nastool-reporters"

# 设置路径
export PATH="{remote_dir}/bin:$PATH"

# 创建日志目录
mkdir -p log

# 执行诊断
echo "🚀 启动 NASTool 诊断..."
python3 -m nastool_cli.main diagnose --output log/diagnosis_result.json

echo "✅ 诊断完成! 结果已保存到 log/diagnosis_result.json"
"""
    
    exec_command(client, f"cat > {remote_dir}/run.sh << 'EOF'\n{script}\nEOF")
    exec_command(client, f"chmod +x {remote_dir}/run.sh")
    print(f"📜 创建远程启动脚本")

def create_remote_uninstall_script(client, remote_dir):
    """在远程主机创建卸载脚本"""
    script = f"""#!/bin/bash
TOOL_DIR="{remote_dir}"

echo "=================================="
echo "  NASTool v4.2 - 一键卸载"
echo "  所有文件将被彻底删除"
echo "  系统不会留下任何痕迹"
echo "=================================="

read -p "确定卸载? (y/n): " ans
if [ "$ans" = "y" ]; then
    rm -rf $TOOL_DIR
    echo "✅ 卸载完成! 系统已恢复初始状态。"
else
    echo "❌ 取消卸载。"
fi
"""
    
    exec_command(client, f"cat > {remote_dir}/uninstall.sh << 'EOF'\n{script}\nEOF")
    exec_command(client, f"chmod +x {remote_dir}/uninstall.sh")
    print(f"📜 创建远程卸载脚本")

def exec_command(client, cmd):
    """执行远程命令"""
    stdin, stdout, stderr = client.exec_command(cmd)
    stdout.channel.recv_exit_status()
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

def main():
    args = parse_args()
    
    print("="*60)
    print("    NASTool v4.2 一键部署脚本")
    print("="*60)
    
    if args.target == 'local':
        deploy_local(args)
    elif args.target == 'remote':
        deploy_remote(args)
    else:
        print(f"❌ 未知部署目标: {args.target}")
        sys.exit(1)

if __name__ == "__main__":
    main()
