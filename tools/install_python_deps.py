#!/usr/bin/env python3
import paramiko
import time

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

print("="*60)
print("    使用 pip 安装 Python 依赖")
print("="*60)

# 需要安装的包
packages = [
    'pydantic>=2.0',
    'rich',
    'typing_extensions',
    'httpx',
    'anyio',
    'sniffio',
    'wsproto',
]

for pkg in packages:
    print(f"\n安装 {pkg}...")
    cmd = f"pip3 install {pkg}"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=180)
    
    # 实时输出
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            output = stdout.channel.recv(4096).decode('utf-8', errors='ignore')
            lines = output.split('\n')
            if len(lines) > 3:
                print('\n'.join(lines[-3:]), end='')
            else:
                print(output, end='')
        time.sleep(2)
    
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    if output:
        lines = output.split('\n')
        if len(lines) > 2:
            print('\n'.join(lines[-2:]))
        else:
            print(output)
    if error:
        print(f"\n警告: {error[-300:] if len(error) > 300 else error}")
    
    print(f"✓ {pkg} 安装完成")

# 验证安装
print("\n验证安装...")
cmd = "python3 -c \"from pydantic import BaseModel; from rich import print; print('所有依赖安装成功！')\""
stdin, stdout, stderr = client.exec_command(cmd)
output = stdout.read().decode().strip()
error = stderr.read().decode().strip()
if output:
    print(f"✓ {output}")
else:
    print(f"✗ 验证失败: {error}")

client.close()
print("\n" + "="*60)
print("所有依赖安装完成！")
print("="*60)
