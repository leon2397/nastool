#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

# 检查目录结构
print("远程目录结构:")
commands = [
    "ls -la /root/tool/",
    "ls -la /root/tool/bin/",
    "ls -la /root/tool/bin/nastool-cli/",
    "ls -la /root/tool/bin/nastool-cli/nastool_cli/",
]

for cmd in commands:
    print(f"\n{cmd}:")
    print("-" * 40)
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode().strip()
    print(output)

# 尝试直接运行
print("\n\n尝试直接运行:")
cmd = "cd /root/tool/bin/nastool-cli && PYTHONPATH=/root/tool/bin/nastool-cli:/root/tool/bin/nastool-common:/root/tool/bin/nastool-core:/root/tool/bin/nastool-adapters:/root/tool/bin/nastool-reporters:/root/tool/bin/nastool-fixes python3 -c \"import nastool_cli; print('OK')\""
print(f"命令: {cmd[:100]}...")
stdin, stdout, stderr = client.exec_command(cmd)
output = stdout.read().decode()
error = stderr.read().decode()
print("输出:", output)
print("错误:", error)

client.close()
