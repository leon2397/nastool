#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

commands = [
    "which conda",
    "which apt-get",
    "which dpkg",
    "python3 --version",
    "ls /usr/lib/python3/dist-packages/",
    "pip3 --version 2>/dev/null || echo 'pip3 not found'",
    "apt-cache search python3-pydantic 2>/dev/null || echo 'apt-cache search failed'",
]

print("检查设备环境...")
for cmd in commands:
    print(f"\n执行: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode('utf-8', errors='ignore').strip()
    error = stderr.read().decode('utf-8', errors='ignore').strip()
    if output:
        print(output)
    if error:
        print(f"错误: {error}")

client.close()
