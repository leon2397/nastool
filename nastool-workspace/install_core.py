# -*- coding: utf-8 -*-
"""Jetson 快速安装脚本 v3 - 直接上传安装"""
import paramiko
import os

def main():
    local_dir = r"D:\project\nastool7\nastool-v4.0.0"
    host = '192.168.1.123'
    user = 'nvidia'
    password = 'nvidia'

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password, timeout=60)
    sftp = ssh.open_sftp()

    # 上传单个模块 nastool-core（最小的开始）
    module = "nastool-core"
    print(f"上传 {module}...")

    # 先删除旧目录
    try:
        sftp.rmdir(f"/home/nvidia/nastool-v4.0.0/{module}")
    except:
        pass

    # 递归上传
    def upload_dir(sftp, local_path, remote_path):
        try:
            sftp.mkdir(remote_path)
        except:
            pass
        for item in os.listdir(local_path):
            local_item = os.path.join(local_path, item)
            remote_item = os.path.join(remote_path, item)
            if os.path.isdir(local_item):
                upload_dir(sftp, local_item, remote_item)
            else:
                sftp.put(local_item, remote_item)

    upload_dir(sftp, os.path.join(local_dir, module), f"/home/nvidia/nastool-v4.0.0/{module}")
    print(f"  上传完成")

    # 安装 nastool-core
    print(f"安装 {module}...")
    stdin, stdout, stderr = ssh.exec_command(f'cd /home/nvidia/nastool-v4.0.0/{module} && pip3 install --user . 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if 'Successfully' in out or err == '':
        print(f"  安装成功")
    else:
        print(f"  {out[:200]}")
        if err:
            print(f"  错误: {err[:200]}")

    # 验证
    print("验证...")
    stdin, stdout, stderr = ssh.exec_command('python3 -c "import nastool_core; print(nastool_core.__version__)"')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    print(f"  nastool_core: {out if out else 'FAILED'}")

    sftp.close()
    ssh.close()

if __name__ == "__main__":
    main()
