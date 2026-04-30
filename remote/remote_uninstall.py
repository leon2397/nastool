#!/usr/bin/env python3
"""远程卸载昇腾设备上的NASTool"""

import paramiko
import sys

def uninstall_remote(host, user, password):
    """在远程设备上卸载NASTool"""
    
    print(f'\n📡 连接到设备: {host}')
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(
            hostname=host,
            port=22,
            username=user,
            password=password,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30
        )
        print('✅ SSH连接成功')
        
        # 检查root目录下的tool目录
        print('\n🔍 检查root目录...')
        stdin, stdout, stderr = client.exec_command('ls -la /root/')
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output)
        
        # 检查tool目录是否存在
        stdin, stdout, stderr = client.exec_command('ls -la /root/tool 2>&1')
        result = stdout.read().decode('utf-8', errors='ignore')
        
        if 'No such file or directory' in result:
            print('⚠️ /root/tool 目录不存在')
            return
        
        print('\n📂 发现tool目录，准备删除...')
        
        # 删除tool目录
        print('🗑️ 删除 /root/tool 目录...')
        stdin, stdout, stderr = client.exec_command('rm -rf /root/tool')
        stdout.read()  # 等待命令完成
        
        # 验证删除结果
        print('🔍 验证删除结果...')
        stdin, stdout, stderr = client.exec_command('ls -la /root/tool 2>&1')
        result = stdout.read().decode('utf-8', errors='ignore')
        
        if 'No such file or directory' in result:
            print('✅ /root/tool 目录已删除')
        else:
            print('❌ 删除失败')
        
    except paramiko.AuthenticationException:
        print('❌ 认证失败，请检查用户名/密码')
    except paramiko.SSHException as e:
        print(f'❌ SSH连接错误: {e}')
    except Exception as e:
        print(f'❌ 错误: {e}')
    finally:
        client.close()

def main():
    print('='*60)
    print('🗑️ NASTool 远程卸载')
    print('='*60)
    
    host = '192.168.1.104'
    user = 'root'
    password = 'linaro123'
    
    print(f'目标设备: {host}')
    print(f'用户名: {user}')
    print()
    
    uninstall_remote(host, user, password)
    
    print('\n' + '='*60)
    print('✅ 操作完成')
    print('='*60)

if __name__ == '__main__':
    main()
