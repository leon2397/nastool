#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

# 检查pip
print("检查pip...")
commands = [
    "which pip",
    "which pip3",
    "python3 -m pip --version",
]

for cmd in commands:
    print(f"\n{cmd}:")
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    if output:
        print(output)
    if error:
        print(f"错误: {error}")

client.close()
