#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

# 测试 pydantic 是否可用
cmd = "python3 -c \"from pydantic import BaseModel; print('pydantic ok')\""
print("测试 pydantic...")
stdin, stdout, stderr = client.exec_command(cmd)
output = stdout.read().decode().strip()
error = stderr.read().decode().strip()
print(f"输出: {output}")
if error:
    print(f"错误: {error}")

# 检查系统中是否有 typing_extensions
cmd = "python3 -c \"import typing_extensions; print('typing_extensions ok')\""
print("\n测试 typing_extensions...")
stdin, stdout, stderr = client.exec_command(cmd)
output = stdout.read().decode().strip()
error = stderr.read().decode().strip()
print(f"输出: {output}")
if error:
    print(f"错误: {error}")

# 检查系统 Python 路径
cmd = "python3 -c \"import sys; print('\\n'.join(sys.path))\""
print("\nPython 路径:")
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode())

client.close()
