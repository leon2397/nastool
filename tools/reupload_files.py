#!/usr/bin/env python3
import paramiko
import os

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

def upload_directory(sftp, local_dir, remote_dir):
    """递归上传目录"""
    # 确保远程目录存在
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        sftp.mkdir(remote_dir)
    
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"  # 使用Linux路径分隔符
        
        if os.path.isdir(local_path):
            upload_directory(sftp, local_path, remote_path)
        elif item.endswith('.py'):
            sftp.put(local_path, remote_path)
            print(f"上传: {local_path} -> {remote_path}")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

sftp = client.open_sftp()

# 删除旧目录
client.exec_command("rm -rf /root/tool/bin")
client.exec_command("mkdir -p /root/tool/bin")

# 重新上传所有模块
modules = ['nastool-common', 'nastool-core', 'nastool-adapters', 
           'nastool-cli', 'nastool-reporters', 'nastool-fixes']

print("重新上传模块...")
for module in modules:
    local_path = f"D:/project/nastool7/{module}"
    remote_path = f"/root/tool/bin/{module}"
    upload_directory(sftp, local_path, remote_path)

sftp.close()
client.close()

print("\n✓ 上传完成")
