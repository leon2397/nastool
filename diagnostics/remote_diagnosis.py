#!/usr/bin/env python3
"""
NASTool 远程诊断测试脚本
通过SSH在目标设备上执行完整诊断测试
"""
import paramiko

# 设备配置
HOST = "192.168.1.103"
PORT = 22
USERNAME = "root"
PASSWORD = "linaro123"

def run_remote_diagnosis():
    """执行远程诊断"""
    print("="*60)
    print("    NASTool V4.1 远程诊断测试 - 昇腾设备")
    print("="*60)
    print(f"\n目标设备: {HOST}")
    print(f"用户名: {USERNAME}")
    print()
    
    # 建立SSH连接
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=HOST,
            port=PORT,
            username=USERNAME,
            password=PASSWORD,
            timeout=15,
            allow_agent=False,
            look_for_keys=False
        )
        print("✓ SSH连接成功")
        
        # 创建临时目录
        stdin, stdout, stderr = client.exec_command("mkdir -p /tmp/nastool_test")
        stdout.read()
        
        # 上传所有模块
        print("正在上传诊断模块...")
        sftp = client.open_sftp()
        
        # 上传每个模块
        modules = ['nastool-common', 'nastool-core', 'nastool-adapters', 
                   'nastool-cli', 'nastool-reporters', 'nastool-fixes']
        
        for module in modules:
            local_path = f"D:/project/nastool7/{module}"
            remote_path = f"/tmp/nastool_test/{module}"
            client.exec_command(f"mkdir -p {remote_path}")
            
            for root, dirs, files in os.walk(local_path):
                for file in files:
                    if file.endswith('.py'):
                        local_file = os.path.join(root, file)
                        rel_path = os.path.relpath(local_file, local_path)
                        remote_file = os.path.join(remote_path, rel_path)
                        sftp.put(local_file, remote_file)
        
        sftp.close()
        print("✓ 诊断模块已上传")
        
        # 执行诊断
        print("\n正在执行完整诊断...")
        cmd = """cd /tmp/nastool_test && PYTHONPATH="/tmp/nastool_test/nastool-cli:/tmp/nastool_test/nastool-common:/tmp/nastool_test/nastool-core:/tmp/nastool_test/nastool-adapters:/tmp/nastool_test/nastool-reporters:/tmp/nastool_test/nastool-fixes" python3 nastool-cli/nastool_cli/main.py --full --no-color"""
        
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        # 输出结果
        print("\n" + "="*60)
        print("诊断结果:")
        print("="*60)
        if output:
            print(output)
        if error:
            print("错误输出:", error)
        
        # 清理
        client.exec_command("rm -rf /tmp/nastool_test")
        client.close()
        
        print("\n✓ 诊断完成")
        return True
        
    except Exception as e:
        print(f"✗ 诊断失败: {e}")
        return False

if __name__ == "__main__":
    import os
    run_remote_diagnosis()
