#!/usr/bin/env python3
"""
远程设备卸载脚本
"""

import paramiko
import sys

def uninstall_remote(host, user, password):
    """在远程设备上卸载NASTool"""
    
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
        
        # 检查目录是否存在
        print("\n🔍 检查安装目录...")
        stdin, stdout, stderr = client.exec_command('ls -la /root/tool 2>&1')
        result = stdout.read().decode('utf-8', errors='ignore')
        
        if 'No such file or directory' in result:
            print("⚠️ /root/tool 目录不存在，无需卸载")
            return
        
        print("📂 发现安装目录，开始卸载...")
        
        # 执行卸载脚本
        print("\n🗑️ 执行卸载脚本...")
        stdin, stdout, stderr = client.exec_command('cd /root/tool && ./uninstall.sh', timeout=30)
        
        # 发送确认
        stdin.write('y\n')
        stdin.flush()
        
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        if output:
            print(output)
        if error:
            print("错误:", error)
        
        # 验证卸载结果
        print("\n🔍 验证卸载结果...")
        stdin, stdout, stderr = client.exec_command('ls -la /root/tool 2>&1')
        result = stdout.read().decode('utf-8', errors='ignore')
        
        if 'No such file or directory' in result:
            print("✅ 卸载成功！/root/tool 目录已删除")
        else:
            print("⚠️ 目录仍存在，手动删除中...")
            client.exec_command('rm -rf /root/tool')
            print("✅ 手动删除完成")
        
        print("\n✅ 卸载操作完成！")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python uninstall_remote.py <host>")
        sys.exit(1)
    
    host = sys.argv[1]
    uninstall_remote(host, 'root', 'linaro123')
