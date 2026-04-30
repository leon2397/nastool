# -*- coding: utf-8 -*-
"""Jetson网络检查脚本"""
import paramiko
import time

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.123', username='nvidia', password='nvidia', timeout=30)

    print("检查网络接口...")
    stdin, stdout, stderr = ssh.exec_command('ip addr show 2>&1')
    time.sleep(1)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out if out else err)

    print("\n检查路由...")
    stdin, stdout, stderr = ssh.exec_command('ip route 2>&1')
    time.sleep(1)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out if out else err)

    print("\n测试网关...")
    stdin, stdout, stderr = ssh.exec_command('ping -c 2 192.168.1.1 2>&1')
    time.sleep(3)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out if out else err)

    print("\n测试外网...")
    stdin, stdout, stderr = ssh.exec_command('ping -c 2 8.8.8.8 2>&1')
    time.sleep(3)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out if out else err)

    print("\nDNS配置...")
    stdin, stdout, stderr = ssh.exec_command('cat /etc/resolv.conf 2>&1')
    time.sleep(1)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out if out else err)

    ssh.close()
    print("\n检查完成")

if __name__ == "__main__":
    main()
