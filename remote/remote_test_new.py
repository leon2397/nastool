#!/usr/bin/env python3
"""对新设备进行远程测试"""

import paramiko
import socket

def test_device(host, user, password):
    """测试单个设备"""
    print(f'\n📡 测试设备: {host}')
    
    # 检查SSH端口
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, 22))
    sock.close()
    
    if result != 0:
        print('❌ SSH端口关闭')
        return False
    
    print('✅ SSH端口开放')
    
    # 尝试SSH连接
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f'🔌 尝试连接...')
        client.connect(host, username=user, password=password, timeout=10)
        print('✅ 连接成功!')
        
        # 执行诊断命令
        commands = [
            ('系统信息', 'uname -a'),
            ('操作系统', 'cat /etc/os-release | grep PRETTY_NAME'),
            ('CPU信息', 'cat /proc/cpuinfo | grep "model name" | head -1'),
            ('内存信息', 'free -h | head -2'),
            ('磁盘信息', 'df -h / | head -2'),
            ('网络接口', 'ip addr show | grep -E "^[0-9]|inet " | head -10'),
            ('路由表', 'ip route show | head -5'),
            ('Ping测试', 'ping -c 3 www.baidu.com')
        ]
        
        for name, cmd in commands:
            print(f'\n--- {name} ---')
            try:
                stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
                output = stdout.read().decode('utf-8', errors='ignore').strip()
                error = stderr.read().decode('utf-8', errors='ignore').strip()
                if output:
                    print(output)
                if error:
                    print(f'警告: {error}')
            except Exception as e:
                print(f'执行失败: {e}')
        
        client.close()
        return True
        
    except paramiko.AuthenticationException:
        print('❌ 认证失败')
        return False
    except Exception as e:
        print(f'❌ 连接错误: {e}')
        return False

def main():
    print('='*60)
    print('🚀 NASTool v4.2 远程设备测试')
    print('='*60)
    
    user = 'root'
    password = 'linaro123'
    
    # 测试发现的设备（排除网关）
    devices = ['192.168.1.100', '192.168.1.104']
    
    for host in devices:
        success = test_device(host, user, password)
        if success:
            print(f'\n🎉 {host} 测试完成!')
            break
    
    print('\n' + '='*60)
    print('✅ 远程测试完成')
    print('='*60)

if __name__ == '__main__':
    main()
