#!/usr/bin/env python3
import paramiko
import socket

# 设备配置
HOST = "192.168.1.102"
PORT = 22
USERNAME = "root"
PASSWORD = "linaro123"

print("尝试连接到设备:", HOST)
print("用户名:", USERNAME)
print("密码:", "*" * len(PASSWORD))
print()

# 先测试端口是否开放
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((HOST, PORT))
    sock.close()
    if result == 0:
        print("✓ 端口", PORT, "是开放的")
    else:
        print("✗ 端口", PORT, "是关闭的")
        exit(1)
except Exception as e:
    print("✗ 端口检测失败:", e)
    exit(1)

# 尝试SSH连接
try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # 启用详细日志
    paramiko.util.log_to_file("ssh_debug.log")
    
    print("正在尝试SSH连接...")
    client.connect(
        hostname=HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD,
        timeout=15,
        allow_agent=False,
        look_for_keys=False,
        banner_timeout=30
    )
    print("✓ SSH连接成功!")
    
    # 执行命令
    stdin, stdout, stderr = client.exec_command("whoami")
    print("当前用户:", stdout.read().decode().strip())
    
    client.close()
    
except paramiko.AuthenticationException:
    print("✗ 认证失败 - 用户名或密码错误")
except paramiko.SSHException as e:
    print("✗ SSH协议错误:", e)
except socket.timeout:
    print("✗ 连接超时")
except Exception as e:
    print("✗ 连接失败:", type(e).__name__, "-", e)

print("\n详细日志已保存到 ssh_debug.log")
