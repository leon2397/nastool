#!/usr/bin/env python3
"""
远程设备诊断脚本
"""

import paramiko
import sys

def remote_diagnose(host, user, password, mode='network'):
    """在远程设备上执行诊断"""
    
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
        
        # 执行网络诊断
        print(f"\n🔍 执行{mode}诊断...")
        
        # 设置Python路径
        python_path = '/root/tool/bin/nastool-cli:/root/tool/bin/nastool-core:/root/tool/bin/nastool-adapters:/root/tool/bin/nastool-common:/root/tool/bin/nastool-fixes:/root/tool/bin/nastool-reporters'
        
        if mode == 'network':
            cmd = f'''export PYTHONPATH="{python_path}" && cd /root/tool && python3 << 'PYEOF'
import sys
sys.path.insert(0, '/root/tool/bin/nastool-core')
from nastool_core.checks.network.network_status_checker import NetworkStatusChecker
c = NetworkStatusChecker()
c.run_full_diagnosis()
print(c.generate_report())
PYEOF'''
        elif mode == 'hardware':
            cmd = f'''export PYTHONPATH="{python_path}" && cd /root/tool && python3 << 'PYEOF'
import sys
sys.path.insert(0, '/root/tool/bin/nastool-core')
from nastool_core.checks.ai.ascend_checker import AscendChecker
c = AscendChecker()
c.run_full_check()
print(c.generate_report())
PYEOF'''
        else:
            cmd = f'''export PYTHONPATH="{python_path}" && cd /root/tool && python3 << 'PYEOF'
import sys
sys.path.insert(0, '/root/tool/bin/nastool-core')
from nastool_core.quick_diagnose import QuickDiagnose
d = QuickDiagnose('quick')
results = d.run()
print(d.generate_report())
PYEOF'''
        
        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        if output:
            print(output)
        
        if error:
            print("⚠️ 警告信息:")
            print(error)
        
        # 获取系统信息
        print("\n📊 系统信息:")
        stdin, stdout, stderr = client.exec_command('uname -a && cat /etc/os-release | grep PRETTY_NAME')
        sys_info = stdout.read().decode('utf-8', errors='ignore')
        print(sys_info)
        
        # 获取网络接口信息
        print("\n📡 网络接口:")
        stdin, stdout, stderr = client.exec_command('ip addr show | grep -E "^[0-9]|inet "')
        net_info = stdout.read().decode('utf-8', errors='ignore')
        print(net_info)
        
        print("\n✅ 诊断完成!")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python remote_diagnose.py <host> [mode]")
        print("  mode: network(默认) | hardware | quick")
        sys.exit(1)
    
    host = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'network'
    
    remote_diagnose(host, 'root', 'linaro123', mode)
