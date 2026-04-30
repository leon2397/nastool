#!/usr/bin/env python3
"""远程设备网络诊断测试（无需部署）"""

import paramiko
import sys

def test_remote_network(host, user, password):
    """测试远程设备网络状态"""
    
    print(f"🔌 连接到远程设备 {host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(
            hostname=host,
            port=22,
            username=user,
            password=password,
            timeout=30
        )
        print("✅ SSH连接成功")
        
        # 执行网络诊断命令
        print("\n" + "="*60)
        print("📊 网络诊断报告")
        print("="*60)
        
        # 1. 网络接口状态
        print("\n[1/6] 网络接口状态:")
        stdin, stdout, stderr = client.exec_command('ip addr show')
        print(stdout.read().decode('utf-8', errors='ignore'))
        
        # 2. 路由表
        print("\n[2/6] 路由表:")
        stdin, stdout, stderr = client.exec_command('ip route show')
        print(stdout.read().decode('utf-8', errors='ignore'))
        
        # 3. Ping测试
        print("\n[3/6] Ping测试 (baidu.com):")
        stdin, stdout, stderr = client.exec_command('ping -c 5 www.baidu.com')
        print(stdout.read().decode('utf-8', errors='ignore'))
        
        # 4. DNS解析
        print("\n[4/6] DNS解析测试:")
        stdin, stdout, stderr = client.exec_command('nslookup www.huawei.com 2>/dev/null || host www.huawei.com 2>/dev/null || dig www.huawei.com +short 2>/dev/null')
        print(stdout.read().decode('utf-8', errors='ignore'))
        
        # 5. 网络统计
        print("\n[5/6] 网络统计:")
        stdin, stdout, stderr = client.exec_command('netstat -s | head -20')
        print(stdout.read().decode('utf-8', errors='ignore'))
        
        # 6. 端口监听
        print("\n[6/6] 端口监听状态:")
        stdin, stdout, stderr = client.exec_command('ss -tlnp')
        print(stdout.read().decode('utf-8', errors='ignore'))
        
        print("\n" + "="*60)
        print("✅ 网络诊断完成!")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python remote_test.py <host> <user> <password>")
        sys.exit(1)
    
    host = sys.argv[1]
    user = sys.argv[2]
    password = sys.argv[3]
    
    test_remote_network(host, user, password)
