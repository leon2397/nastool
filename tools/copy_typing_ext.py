#!/usr/bin/env python3
import paramiko
import os

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

LOCAL_PYTHON_LIB = r"C:\Users\Administrator\AppData\Local\Programs\Python\Python310\Lib\site-packages"

# 需要复制的单文件包
FILE_PACKAGES = [
    'typing_extensions.py',
]

# 需要复制的目录包
DIR_PACKAGES = [
    'typing_inspection',
    'sniffio',
    'outcome',
    'sortedcontainers',
    'trio',
    'wsproto',
    'h2',
    'hyperframe',
    'hpack',
    'pynacl',
    'socks',
    'async_timeout',
    'attrs',
    'multidict',
    'yarl',
    'six',
]

def main():
    print("复制缺失的依赖...")
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)
    sftp = client.open_sftp()
    
    # 复制单文件包
    for pkg_file in FILE_PACKAGES:
        local_path = os.path.join(LOCAL_PYTHON_LIB, pkg_file)
        remote_path = f"/root/tool/dep/lib/{pkg_file}"
        if os.path.exists(local_path):
            print(f"复制 {pkg_file}...")
            sftp.put(local_path, remote_path)
            print(f"✓ {pkg_file} 复制完成")
        else:
            print(f"✗ {pkg_file} 不存在")
    
    # 复制目录包
    for pkg_dir in DIR_PACKAGES:
        local_path = os.path.join(LOCAL_PYTHON_LIB, pkg_dir)
        remote_path = f"/root/tool/dep/lib/{pkg_dir}"
        if os.path.exists(local_path):
            print(f"复制 {pkg_dir}...")
            try:
                sftp.mkdir(remote_path)
            except:
                pass
            for root, dirs, files in os.walk(local_path):
                for file in files:
                    local_file = os.path.join(root, file)
                    rel_path = os.path.relpath(local_file, local_path)
                    remote_file = f"{remote_path}/{rel_path}"
                    sftp.put(local_file, remote_file)
            print(f"✓ {pkg_dir} 复制完成")
        else:
            print(f"✗ {pkg_dir} 不存在")
    
    sftp.close()
    client.close()
    print("\n✓ 复制完成")

if __name__ == "__main__":
    main()
