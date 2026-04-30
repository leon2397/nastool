#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

# 检查测试结果文件
print("检查测试结果...")
cmd = "ls -la /root/tool/log/"
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode())

# 检查目录结构
print("\n检查目录结构...")
cmd = "ls -la /root/tool/"
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode())

# 检查卸载脚本
print("检查卸载脚本...")
cmd = "cat /root/tool/uninstall.sh"
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode())

client.close()
