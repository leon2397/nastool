#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

print("执行测试...")
stdin, stdout, stderr = client.exec_command("cd /root/tool && ./run.sh", timeout=180)

# 实时输出
import time
while not stdout.channel.exit_status_ready():
    if stdout.channel.recv_ready():
        output = stdout.channel.recv(1024).decode('utf-8', errors='ignore')
        print(output, end='')
    time.sleep(0.1)

# 获取剩余输出
output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

print(output)
if error:
    print("\n错误输出:", error)

client.close()
