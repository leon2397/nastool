#!/usr/bin/env python3
"""测试SSH连接的不同参数"""

import paramiko
import socket

def test_ssh_connection(host, user, password):
    """测试SSH连接"""
    print(f'🔍 尝试连接到 {host}...')
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # 尝试不同的连接参数
        print('尝试标准连接...')
        client.connect(
            hostname=host,
            port=22,
            username=user,
            password=password,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        print('✅ 连接成功!')
        return client
        
    except paramiko.AuthenticationException:
        print('❌ 认证失败')
        return None
    except paramiko.SSHException as e:
        print(f'❌ SSH错误: {e}')
        return None
    except socket.timeout:
        print('❌ 连接超时')
        return None
    except Exception as e:
        print(f'❌ 未知错误: {e}')
        return None

if __name__ == '__main__':
    host = '192.168.1.102'
    user = 'root'
    
    # 尝试不同的密码
    passwords = ['root', 'linaro123', 'password', 'admin', 'test']
    
    for pwd in passwords:
        print(f'\n尝试密码: {pwd}')
        client = test_ssh_connection(host, user, pwd)
        if client:
            try:
                # 执行简单命令测试
                stdin, stdout, stderr = client.exec_command('uname -a')
                result = stdout.read().decode('utf-8')
                print(f'系统信息: {result}')
                client.close()
                print(f'\n🎉 成功连接! 密码: {pwd}')
                break
            except:
                pass
        else:
            print(f'密码 {pwd} 失败')
