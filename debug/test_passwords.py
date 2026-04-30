#!/usr/bin/env python3
"""测试不同密码连接设备"""

import paramiko

def test_passwords(host, user, passwords):
    """尝试不同密码连接"""
    for pwd in passwords:
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, username=user, password=pwd, timeout=5)
            print(f'✅ 成功! 密码: {pwd}')
            client.close()
            return pwd
        except paramiko.AuthenticationException:
            print(f'❌ 密码 "{pwd}" 失败')
        except Exception as e:
            print(f'⚠️ 连接错误: {e}')
            return None
    return None

if __name__ == '__main__':
    host = '192.168.1.102'
    user = 'root'
    
    passwords = [
        'root', 'password', 'test', 'admin', 
        'huawei', 'ascend', 'linaro123', 
        '123456', '12345678', 'admin123',
        'root123', 'password123', 'test123'
    ]
    
    print(f'🔍 尝试连接到 {host}...')
    success_pwd = test_passwords(host, user, passwords)
    
    if success_pwd:
        print(f'\n🎉 找到正确密码: {success_pwd}')
    else:
        print('\n⚠️ 未找到正确密码')
