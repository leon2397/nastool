#!/usr/bin/env python3
import paramiko
import os

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

# 创建依赖目录
client.exec_command("mkdir -p /root/tool/dep/lib")

sftp = client.open_sftp()

# 从本地Python环境复制依赖
local_python_lib = "C:/Users/Administrator/AppData/Local/Programs/Python/Python310/Lib/site-packages"

# 需要复制的包
packages = ['pydantic', 'pydantic_core', 'rich', 'requests', 'psutil', 'paramiko']

print("复制依赖库...")
for pkg in packages:
    local_path = os.path.join(local_python_lib, pkg)
    remote_path = f"/root/tool/dep/lib/{pkg}"
    
    if os.path.exists(local_path):
        print(f"复制 {pkg}...")
        # 创建远程目录
        client.exec_command(f"mkdir -p {remote_path}")
        
        # 递归复制
        for root, dirs, files in os.walk(local_path):
            for file in files:
                local_file = os.path.join(root, file)
                rel_path = os.path.relpath(local_file, local_path)
                remote_file = f"{remote_path}/{rel_path}"
                sftp.put(local_file, remote_file)
        print(f"✓ {pkg} 复制完成")
    else:
        print(f"✗ {pkg} 不存在")

sftp.close()
client.close()

print("\n✓ 依赖复制完成")
