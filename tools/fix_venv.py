#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

# 检查并修复虚拟环境
print("检查虚拟环境...")
stdin, stdout, stderr = client.exec_command("ls /root/tool/dep/")
output = stdout.read().decode()
print("目录内容:", output)

# 重新创建虚拟环境
print("\n重新创建虚拟环境...")
cmd = "python3 -m venv /root/tool/dep/venv --without-pip"
stdin, stdout, stderr = client.exec_command(cmd)
stdout.read()
error = stderr.read().decode()
print("错误:", error)

# 手动安装pip
print("\n安装pip...")
cmd = "curl https://bootstrap.pypa.io/get-pip.py | python3"
stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
stdout.read()
error = stderr.read().decode()
if "Successfully installed" in error:
    print("✓ pip安装成功")
else:
    print("错误:", error[:300])

# 使用pip安装依赖到指定目录
print("\n安装依赖到本地目录...")
cmd = "pip install paramiko requests psutil --target /root/tool/dep/lib"
stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
stdout.read()
error = stderr.read().decode()
if "Successfully installed" in error:
    print("✓ 依赖安装成功")
else:
    print("错误:", error[:300])

client.close()
print("\n修复完成")
