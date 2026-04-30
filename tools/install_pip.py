#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

print("安装pip...")
cmd = "curl -s https://bootstrap.pypa.io/get-pip.py | python3"
stdin, stdout, stderr = client.exec_command(cmd, timeout=120)

# 实时输出
import time
while not stdout.channel.exit_status_ready():
    if stdout.channel.recv_ready():
        output = stdout.channel.recv(4096).decode('utf-8', errors='ignore')
        print(output, end='')
    time.sleep(2)

output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')
print(output)
if error:
    print("\n错误:", error)

client.close()
print("\n✓ pip安装完成")
