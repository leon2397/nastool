#!/usr/bin/env python3
"""简化版远程诊断"""
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

# 直接执行命令
commands = [
    "uname -a",
    "cat /etc/os-release | head -5",
    "free -h",
    "df -h",
    "npu-smi info 2>/dev/null || echo 'NPU info not available'",
    "python3 --version",
    "ls /usr/local/Ascend 2>/dev/null || echo 'Ascend not found'"
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

print("="*60)
print("    昇腾设备快速诊断")
print("="*60)

for cmd in commands:
    print(f"\n{cmd}:")
    print("-" * 40)
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    if output:
        print(output.strip())
    if error:
        print(f"错误: {error.strip()}")

client.close()
print("\n" + "="*60)
