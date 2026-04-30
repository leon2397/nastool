#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

print("使用apt-get安装pip...")
cmd = "apt-get update && apt-get install -y python3-pip"
stdin, stdout, stderr = client.exec_command(cmd, timeout=300)

# 实时输出
import time
while not stdout.channel.exit_status_ready():
    if stdout.channel.recv_ready():
        output = stdout.channel.recv(4096).decode('utf-8', errors='ignore')
        print(output[-1000:], end='')  # 只显示最后1000字符
    time.sleep(2)

output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')
print(output[-500:] if len(output) > 500 else output)
if error:
    print("\n错误:", error[-500:] if len(error) > 500 else error)

client.close()
print("\n✓ 安装完成")
