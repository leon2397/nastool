#!/usr/bin/env python3
"""对192.168.1.100进行远程测试"""

import paramiko
import socket

def main():
    host = '192.168.1.100'
    print(f'='*60)
    print(f'🔌 远程测试: {host}')
    print('='*60)
    
    # 检查SSH端口
    print('\n[1/3] 检查SSH端口...')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, 22))
    sock.close()
    
    if result == 0:
        print('✅ SSH端口开放')
        
        # 尝试SSH连接
        print('\n[2/3] 尝试SSH连接...')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        passwords = ['linaro123', 'root', 'password', 'admin', 'huawei', 'ascend']
        
        success_pwd = None
        for pwd in passwords:
            try:
                print(f'  尝试密码: {pwd}...')
                client.connect(host, username='root', password=pwd, timeout=5)
                success_pwd = pwd
                break
            except paramiko.AuthenticationException:
                continue
            except Exception as e:
                print(f'  ❌ 连接错误: {e}')
                break
        
        if success_pwd:
            print(f'✅ 连接成功! 密码: {success_pwd}')
            
            # 执行远程诊断
            print('\n[3/3] 执行远程网络诊断...')
            
            commands = [
                ('系统信息', 'uname -a'),
                ('操作系统', 'cat /etc/os-release | grep PRETTY_NAME'),
                ('CPU信息', 'cat /proc/cpuinfo | grep "model name" | head -1'),
                ('内存信息', 'free -h'),
                ('磁盘信息', 'df -h /'),
                ('网络接口', 'ip addr show | head -20'),
                ('路由表', 'ip route show'),
                ('Ping测试', 'ping -c 3 www.baidu.com')
            ]
            
            for name, cmd in commands:
                print(f'\n--- {name} ---')
                try:
                    stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
                    output = stdout.read().decode('utf-8', errors='ignore')
                    error = stderr.read().decode('utf-8', errors='ignore')
                    if output:
                        print(output.strip())
                    if error:
                        print(f'警告: {error.strip()}')
                except Exception as e:
                    print(f'执行失败: {e}')
            
            client.close()
            print('\n✅ 远程测试完成!')
        else:
            print('❌ 所有密码尝试失败，请提供正确密码')
    else:
        print('❌ SSH端口关闭')
        print('⚠️ 无法进行远程测试，请确保设备开启SSH服务')
    
    print('='*60)

if __name__ == '__main__':
    main()
