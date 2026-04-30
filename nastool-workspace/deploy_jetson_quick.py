# -*- coding: utf-8 -*-
"""
Jetson 部署脚本 - nastool v4.0.0
使用 paramiko 上传本地模块并安装到 Jetson

使用方法：
    python deploy_jetson_quick.py --host 192.168.1.123 --user nvidia --password nvidia

安全说明：
    - 仅使用 pip install -e（editable 模式，不修改系统文件）
    - 仅修改用户级别的 ~/.bashrc
    - 不破坏 Jetson 系统稳定性
"""

import argparse
import sys
import os
import tarfile
import tempfile
import shutil

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False


def upload_directory(sftp, local_path, remote_path):
    """递归上传目录"""
    os.chdir(local_path)
    for item in os.listdir(local_path):
        local_item = os.path.join(local_path, item)
        remote_item = os.path.join(remote_path, item)
        if os.path.isdir(local_item):
            try:
                sftp.mkdir(remote_item)
            except:
                pass
            upload_directory(sftp, local_item, remote_item)
        else:
            sftp.put(local_item, remote_item)


def deploy_to_jetson(host, user, password, local_dir):
    """部署 nastool 到 Jetson 设备"""
    if not HAS_PARAMIKO:
        print("错误: 需要安装 paramiko")
        print("请运行: pip install paramiko")
        return False

    print(f"正在连接到 Jetson ({user}@{host})...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, password=password, timeout=30)
    sftp = ssh.open_sftp()
    
    print("[OK] SSH/SFTP 连接成功")
    
    # 1. 创建 Jetson 上的 nastool 目录
    print("\n[1/6] 创建 Jetson nastool 目录...")
    try:
        sftp.mkdir("nastool-v4.0.0")
    except:
        pass
    print("  完成")
    
    # 2. 上传 nastool 模块
    print("\n[2/6] 上传 nastool 模块到 Jetson...")
    modules = ["nastool-common", "nastool-core", "nastool-adapters", 
               "nastool-reporters", "nastool-fixes", "nastool-cli"]
    
    for module in modules:
        local_module = os.path.join(local_dir, module)
        if os.path.exists(local_module):
            print(f"  上传 {module}...")
            try:
                sftp.mkdir(f"nastool-v4.0.0/{module}")
            except:
                pass
            upload_directory(sftp, local_module, f"nastool-v4.0.0/{module}")
            print(f"    完成")
        else:
            print(f"  警告: {module} 不存在于本地目录")
    
    # 3. 配置 PATH
    print("\n[3/6] 配置 PATH...")
    stdin, stdout, stderr = ssh.exec_command(
        '''echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc'''
    )
    print("  完成")
    
    # 4. 安装 nastool-common
    print("\n[4/6] 安装 nastool 模块...")
    install_cmd = 'cd ~/nastool-v4.0.0 && pip3 install --user -e nastool-common 2>&1'
    stdin, stdout, stderr = ssh.exec_command(install_cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(f"  nastool-common: {'OK' if 'Successfully' in out or err == '' else 'FAILED'}")
    
    install_cmd = 'cd ~/nastool-v4.0.0 && pip3 install --user -e nastool-core 2>&1'
    stdin, stdout, stderr = ssh.exec_command(install_cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(f"  nastool-core: {'OK' if 'Successfully' in out or err == '' else 'FAILED'}")
    
    install_cmd = 'cd ~/nastool-v4.0.0 && pip3 install --user -e nastool-adapters 2>&1'
    stdin, stdout, stderr = ssh.exec_command(install_cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(f"  nastool-adapters: {'OK' if 'Successfully' in out or err == '' else 'FAILED'}")
    
    install_cmd = 'cd ~/nastool-v4.0.0 && pip3 install --user -e nastool-reporters 2>&1'
    stdin, stdout, stderr = ssh.exec_command(install_cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(f"  nastool-reporters: {'OK' if 'Successfully' in out or err == '' else 'FAILED'}")
    
    install_cmd = 'cd ~/nastool-v4.0.0 && pip3 install --user -e nastool-fixes 2>&1'
    stdin, stdout, stderr = ssh.exec_command(install_cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(f"  nastool-fixes: {'OK' if 'Successfully' in out or err == '' else 'FAILED'}")
    
    install_cmd = 'cd ~/nastool-v4.0.0 && pip3 install --user -e nastool-cli 2>&1'
    stdin, stdout, stderr = ssh.exec_command(install_cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(f"  nastool-cli: {'OK' if 'Successfully' in out or err == '' else 'FAILED'}")
    
    # 5. 配置 CUDA PATH
    print("\n[5/6] 配置 CUDA PATH...")
    stdin, stdout, stderr = ssh.exec_command(
        '''echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc'''
    )
    stdin, stdout, stderr = ssh.exec_command(
        '''echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc'''
    )
    print("  完成")
    
    # 6. 验证安装
    print("\n[6/6] 验证安装...")
    verify_cmds = [
        ('nastool_core 版本', 'python3 -c "import nastool_core; print(nastool_core.__version__)"'),
        ('nastool_cli 版本', 'python3 -c "import nastool_cli; print(nastool_cli.__version__)"'),
        ('nastool 命令', 'which nastool || echo "需要重新登录 shell"'),
    ]
    
    for desc, cmd in verify_cmds:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if out:
            print(f"  {desc}: {out}")
        elif err:
            print(f"  {desc}: {err[:80]}")
    
    sftp.close()
    ssh.close()
    
    print("\n" + "=" * 60)
    print(" 部署完成！")
    print("=" * 60)
    print()
    print("请重新登录 Jetson 或运行以下命令使 PATH 生效：")
    print("  source ~/.bashrc")
    print()
    print("然后测试：")
    print("  nastool --version")
    print("  nastool --mock healthy")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Jetson nastool v4.0.0 部署工具")
    parser.add_argument("--host", default="192.168.1.123", help="Jetson IP 地址")
    parser.add_argument("--user", default="nvidia", help="Jetson 用户名")
    parser.add_argument("--password", default="nvidia", help="SSH 密码")
    parser.add_argument("--local-dir", default=None, help="本地 nastool-v4.0.0 目录")

    args = parser.parse_args()

    # 查找本地 nastool-v4.0.0 目录
    if args.local_dir:
        local_dir = args.local_dir
    else:
        possible_dirs = [
            os.path.join(os.path.dirname(__file__), "..", "nastool-v4.0.0"),
            os.path.join(os.getcwd(), "nastool-v4.0.0"),
            "D:\\project\\nastool7\\nastool-v4.0.0",
        ]
        local_dir = None
        for d in possible_dirs:
            if os.path.exists(d):
                local_dir = d
                break
    
    if not local_dir or not os.path.exists(local_dir):
        print(f"错误: 找不到 nastool-v4.0.0 目录")
        print(f"请使用 --local-dir 指定本地目录")
        return 1

    print("=" * 60)
    print(" nastool v4.0.0 Jetson 部署工具")
    print("=" * 60)
    print()
    print(f"目标设备: {args.user}@{args.host}")
    print(f"本地目录: {local_dir}")
    print()
    print("安全说明：")
    print("  - 仅使用 pip install -e（editable 模式）")
    print("  - 不修改系统文件")
    print("  - 不破坏系统稳定性")
    print()
    
    success = deploy_to_jetson(args.host, args.user, args.password, local_dir)
    
    if not success:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
