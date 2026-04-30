#!/usr/bin/env python3
"""
NASTool V4.1 昇腾设备完整测试
通过SSH远程执行完整诊断
"""
import paramiko
import os

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

def upload_files(sftp, local_dir, remote_dir):
    """上传目录到远程"""
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = os.path.join(remote_dir, item)
        if os.path.isdir(local_path):
            sftp.mkdir(remote_path)
            upload_files(sftp, local_path, remote_path)
        elif item.endswith('.py'):
            sftp.put(local_path, remote_path)

def main():
    print("="*60)
    print("    NASTool V4.1 昇腾设备完整测试")
    print("="*60)
    print(f"\n目标设备: {HOST}")
    print()
    
    try:
        # 连接
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=HOST, username=USERNAME, password=PASSWORD, timeout=15)
        print("✓ SSH连接成功")
        
        # 创建临时目录
        client.exec_command("rm -rf /tmp/nastool_test && mkdir -p /tmp/nastool_test")
        
        # 上传模块
        print("\n正在上传NASTool模块...")
        sftp = client.open_sftp()
        modules = ['nastool-common', 'nastool-core', 'nastool-adapters', 
                   'nastool-cli', 'nastool-reporters', 'nastool-fixes']
        
        for module in modules:
            local_path = os.path.join("D:/project/nastool7", module)
            remote_path = f"/tmp/nastool_test/{module}"
            sftp.mkdir(remote_path)
            upload_files(sftp, local_path, remote_path)
        sftp.close()
        print("✓ 模块上传完成")
        
        # 执行完整诊断
        print("\n正在执行完整诊断...")
        cmd = """
cd /tmp/nastool_test && \
PYTHONPATH="/tmp/nastool_test/nastool-cli:/tmp/nastool_test/nastool-common:/tmp/nastool_test/nastool-core:/tmp/nastool_test/nastool-adapters:/tmp/nastool_test/nastool-reporters:/tmp/nastool_test/nastool-fixes" \
python3 -c "
import sys
sys.path.insert(0, '/tmp/nastool_test/nastool-cli')
sys.path.insert(0, '/tmp/nastool_test/nastool-common')
sys.path.insert(0, '/tmp/nastool_test/nastool-core')
sys.path.insert(0, '/tmp/nastool_test/nastool-adapters')
sys.path.insert(0, '/tmp/nastool_test/nastool-reporters')
sys.path.insert(0, '/tmp/nastool_test/nastool-fixes')

from nastool_cli.main import main
main(['--full', '--no-color'])
"
"""
        stdin, stdout, stderr = client.exec_command(cmd, timeout=180)
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        # 保存结果
        with open("ascend_test_result.txt", "w", encoding="utf-8") as f:
            f.write("诊断输出:\n")
            f.write("="*60 + "\n")
            f.write(output)
            if error:
                f.write("\n错误输出:\n")
                f.write("="*60 + "\n")
                f.write(error)
        
        print("\n" + "="*60)
        print("诊断结果摘要:")
        print("="*60)
        
        # 提取关键信息
        if output:
            # 打印部分结果
            lines = output.split('\n')
            for i, line in enumerate(lines[:50]):
                print(line)
            if len(lines) > 50:
                print(f"... (共 {len(lines)} 行，完整结果已保存)")
        
        if error:
            print("\n错误信息:")
            print(error[:500])
        
        # 清理
        client.exec_command("rm -rf /tmp/nastool_test")
        client.close()
        
        print("\n✓ 测试完成，结果已保存到 ascend_test_result.txt")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
