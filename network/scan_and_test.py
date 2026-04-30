#!/usr/bin/env python3
"""扫描并测试局域网设备"""

import subprocess
import platform
import socket
import paramiko

def scan_network():
    """扫描局域网设备"""
    print('🔍 正在扫描局域网内设备...')
    
    if platform.system() == 'Windows':
        ping_cmd = 'ping -n 1 -w 500'
    else:
        ping_cmd = 'ping -c 1 -W 1'
    
    available_hosts = []
    for i in range(100, 110):
        ip = f'192.168.1.{i}'
        try:
            result = subprocess.run(f'{ping_cmd} {ip}', shell=True, capture_output=True, timeout=2)
            if result.returncode == 0:
                available_hosts.append(ip)
                print(f'✅ {ip}')
        except:
            pass
    
    return available_hosts

def check_ssh_port(host):
    """检查SSH端口"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, 22))
    sock.close()
    return result == 0

def test_ssh_connection(host):
    """测试SSH连接"""
    passwords = ['linaro123', 'root', 'password', 'admin', 'test']
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    for pwd in passwords:
        try:
            client.connect(host, username='root', password=pwd, timeout=5)
            client.close()
            return pwd
        except paramiko.AuthenticationException:
            continue
        except Exception as e:
            print(f'⚠️ 连接错误: {e}')
            return None
    
    return None

if __name__ == '__main__':
    hosts = scan_network()
    
    if not hosts:
        print('❌ 未发现可用设备')
        exit(1)
    
    print(f'\n发现 {len(hosts)} 个设备')
    
    for host in hosts:
        print(f'\n📡 测试设备: {host}')
        
        if check_ssh_port(host):
            print('✅ SSH端口开放')
            
            pwd = test_ssh_connection(host)
            if pwd:
                print(f'🎉 连接成功! 密码: {pwd}')
                
                # 执行远程网络测试
                print('\n📊 执行远程网络诊断...')
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(host, username='root', password=pwd)
                
                # 执行网络测试命令
                commands = [
                    ('网络接口', 'ip addr show | head -20'),
                    ('Ping测试', 'ping -c 3 www.baidu.com'),
                    ('DNS解析', 'nslookup www.baidu.com 2>/dev/null | head -5')
                ]
                
                for name, cmd in commands:
                    print(f'\n--- {name} ---')
                    stdin, stdout, stderr = client.exec_command(cmd)
                    print(stdout.read().decode('utf-8', errors='ignore'))
                
                client.close()
            else:
                print('❌ 所有密码都失败')
        else:
            print('❌ SSH端口关闭')
