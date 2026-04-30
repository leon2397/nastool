#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

# 检查系统Python
commands = [
    "which python3",
    "python3 --version",
    "which pip3",
    "pip3 --version",
    "ls /root/tool/dep/venv/bin/"
]

for cmd in commands:
    print(f"\n{cmd}:")
    print("-" * 40)
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    if output:
        print(output)
    if error:
        print(f"错误: {error}")

client.close()
