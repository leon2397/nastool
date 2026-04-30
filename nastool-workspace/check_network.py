# -*- coding: utf-8 -*-
"""检查并修复Jetson网络"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.123', username='nvidia', password='nvidia', timeout=30)

    print("1. 检查网络接口状态...")
    stdin, stdout, stderr = ssh.exec_command('ip addr show')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n2. 检查路由表...")
    stdin, stdout, stderr = ssh.exec_command('ip route')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n3. 测试本地网关连通性...")
    stdin, stdout, stderr = ssh.exec_command('ping -c 2 192.168.1.1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n4. 测试DNS连通性...")
    stdin, stdout, stderr = ssh.exec_command('ping -c 2 8.8.8.8')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n5. 检查DNS配置...")
    stdin, stdout, stderr = ssh.exec_command('cat /etc/resolv.conf')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n6. 检查/etc/network/interfaces...")
    stdin, stdout, stderr = ssh.exec_command('cat /etc/network/interfaces 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n7. 检查NetworkManager状态...")
    stdin, stdout, stderr = ssh.exec_command('systemctl status NetworkManager 2>&1 | head -10')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    ssh.close()

if __name__ == "__main__":
    main()
