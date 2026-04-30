#!/usr/bin/env python3
import paramiko
import time

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

print("="*60)
print("    使用 curl 安装 pip")
print("="*60)

# 下载 get-pip.py
print("\n1. 下载 get-pip.py...")
cmd = "curl -sL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py"
stdin, stdout, stderr = client.exec_command(cmd)
exit_status = stdout.channel.recv_exit_status()
if exit_status == 0:
    print("✓ 下载成功")
else:
    print(f"✗ 下载失败: {stderr.read().decode()}")
    client.close()
    exit(1)

# 安装 pip
print("\n2. 安装 pip...")
cmd = "python3 /tmp/get-pip.py"
stdin, stdout, stderr = client.exec_command(cmd, timeout=180)

# 实时输出
while not stdout.channel.exit_status_ready():
    if stdout.channel.recv_ready():
        output = stdout.channel.recv(4096).decode('utf-8', errors='ignore')
        print(output, end='')
    time.sleep(2)

output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')
print(output)
if error:
    print(f"\n错误: {error}")

# 验证安装
print("\n3. 验证 pip 安装...")
cmd = "pip3 --version"
stdin, stdout, stderr = client.exec_command(cmd)
output = stdout.read().decode().strip()
error = stderr.read().decode().strip()
if output:
    print(f"✓ {output}")
else:
    print(f"✗ 安装失败: {error}")

client.close()
print("\n" + "="*60)
