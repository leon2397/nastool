#!/usr/bin/env python3
import paramiko
import time

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

print("重新安装 cryptography 和 paramiko...")

cmd = "pip3 install --force-reinstall cryptography paramiko"
stdin, stdout, stderr = client.exec_command(cmd, timeout=180)

while not stdout.channel.exit_status_ready():
    if stdout.channel.recv_ready():
        output = stdout.channel.recv(4096).decode('utf-8', errors='ignore')
        print(output, end='')
    time.sleep(2)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f"\n错误: {error}")

# 验证
print("\n验证安装...")
cmd = "python3 -c \"import paramiko; print('paramiko ok')\""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode())
if stderr.read():
    print(f"错误: {stderr.read().decode()}")

client.close()
print("\n✓ 完成")
