#!/usr/bin/env python3
"""测试连接远程设备"""

import paramiko

def test_connection():
    host = '192.168.1.102'
    user = 'root'
    
    common_passwords = ['root', 'password', 'test', 'admin', 'huawei', 'ascend', 'linaro123']
    
    print(f'🔍 尝试连接到 {host}...')
    for pwd in common_passwords:
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
    
    print('❌ 所有密码都尝试失败')
    return None

if __name__ == '__main__':
    success_pwd = test_connection()
    if success_pwd:
        print(f'\n🎉 找到正确密码: {success_pwd}')
    else:
        print('\n⚠️ 未找到正确密码，请联系管理员获取设备密码')
