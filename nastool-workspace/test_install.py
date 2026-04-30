# -*- coding: utf-8 -*-
"""Jetson 安装测试"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.123', username='nvidia', password='nvidia', timeout=30)

    print("安装 nastool-core...")
    stdin, stdout, stderr = ssh.exec_command('cd ~/nastool-v4.0.0/nastool-core && pip3 install --user . 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out)
    if err:
        print("STDERR:", err[:300])

    print("\n验证 nastool_core...")
    stdin, stdout, stderr = ssh.exec_command('python3 -c "import nastool_core; print(nastool_core.__version__)" 2>&1')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    print(f"结果: {out if out else '导入失败'}")

    ssh.close()

if __name__ == "__main__":
    main()
