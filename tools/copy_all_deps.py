#!/usr/bin/env python3
import paramiko
import os

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

# 本地Python库路径
LOCAL_PYTHON_LIB = r"C:\Users\Administrator\AppData\Local\Programs\Python\Python310\Lib\site-packages"

# 需要复制的依赖包
REQUIRED_PACKAGES = [
    'typing_extensions',
    'rich',
    'psutil',
    'pydantic',
    'pydantic_core',
    'requests',
    'paramiko',
    'idna',
    'charset_normalizer',
    'certifi',
    'urllib3',
    'bcrypt',
    'cryptography',
    'cffi',
    'six',
    'pynacl',
    'socks',
    'async_timeout',
    'attrs',
    'colorama',
    'commonmark',
    'httpcore',
    'httpx',
    'markdown-it-py',
    'mdurl',
    'multidict',
    'outcome',
    'pycparser',
    'pygments',
    'sniffio',
    'sortedcontainers',
    'trio',
    'yarl',
    'h11',
    'h2',
    'hyperframe',
    'hpack',
    'anyio',
    'exceptiongroup',
    'wsproto',
]

def copy_package(sftp, pkg_name):
    """复制单个包"""
    local_path = os.path.join(LOCAL_PYTHON_LIB, pkg_name)
    remote_path = f"/root/tool/dep/lib/{pkg_name}"
    
    if not os.path.exists(local_path):
        print(f"✗ {pkg_name} 不存在")
        return False
    
    try:
        # 创建远程目录
        sftp.mkdir(remote_path)
    except:
        pass  # 目录已存在
    
    print(f"复制 {pkg_name}...")
    for root, dirs, files in os.walk(local_path):
        for file in files:
            local_file = os.path.join(root, file)
            rel_path = os.path.relpath(local_file, local_path)
            remote_file = f"{remote_path}/{rel_path}"
            
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_file)
            try:
                sftp.stat(remote_dir)
            except:
                # 创建多级目录
                parts = remote_dir.split('/')
                current = ''
                for part in parts:
                    current += part + '/'
                    try:
                        sftp.mkdir(current)
                    except:
                        pass
            
            sftp.put(local_file, remote_file)
    
    print(f"✓ {pkg_name} 复制完成")
    return True

def main():
    print("="*60)
    print("    复制依赖库到昇腾设备")
    print("="*60)
    print(f"\n本地Python库路径: {LOCAL_PYTHON_LIB}")
    print(f"远程目标路径: /root/tool/dep/lib/")
    print()
    
    try:
        # 连接设备
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=HOST, username=USERNAME, password=PASSWORD, timeout=15)
        print("✓ SSH连接成功")
        
        # 创建依赖目录
        client.exec_command("mkdir -p /root/tool/dep/lib")
        
        sftp = client.open_sftp()
        
        # 复制所有依赖
        success_count = 0
        fail_count = 0
        
        for pkg in REQUIRED_PACKAGES:
            if copy_package(sftp, pkg):
                success_count += 1
            else:
                fail_count += 1
        
        sftp.close()
        client.close()
        
        print(f"\n" + "="*60)
        print(f"复制完成！")
        print(f"成功: {success_count} 个包")
        print(f"失败: {fail_count} 个包")
        print("="*60)
        
        return success_count > 0
        
    except Exception as e:
        print(f"\n✗ 复制失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
