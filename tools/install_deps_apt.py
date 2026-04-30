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
print("    使用 apt-get 安装 Python 依赖")
print("="*60)

# 需要安装的包
packages = [
    'python3-pydantic',
    'python3-rich',
    'python3-psutil',
    'python3-requests',
    'python3-paramiko',
]

for pkg in packages:
    print(f"\n安装 {pkg}...")
    cmd = f"apt-get install -y {pkg}"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
    
    # 实时输出进度
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            output = stdout.channel.recv(4096).decode('utf-8', errors='ignore')
            # 只显示最后几行
            lines = output.split('\n')
            if len(lines) > 5:
                print('\n'.join(lines[-5:]), end='')
            else:
                print(output, end='')
        time.sleep(2)
    
    # 获取剩余输出
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    if output:
        print(output[-500:] if len(output) > 500 else output)
    if error:
        print(f"\n警告: {error[-300:] if len(error) > 300 else error}")
    
    print(f"✓ {pkg} 安装完成")

client.close()
print("\n" + "="*60)
print("所有依赖安装完成！")
print("="*60)
