# -*- coding: utf-8 -*-
"""Jetson 状态快速检查"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.123', username='nvidia', password='nvidia', timeout=30)

    print("检查 nastool-v4.0.0 目录内容:")
    stdin, stdout, stderr = ssh.exec_command('ls -la ~/nastool-v4.0.0/ 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n检查 nastool-core 是否存在:")
    stdin, stdout, stderr = ssh.exec_command('ls -la ~/nastool-v4.0.0/nastool-core/ 2>&1 | head -10')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n检查 setup.py 是否存在:")
    stdin, stdout, stderr = ssh.exec_command('test -f ~/nastool-v4.0.0/nastool-core/setup.py && echo "存在" || echo "不存在"')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    print(f"setup.py: {out}")

    print("\n检查 pyproject.toml 是否存在:")
    stdin, stdout, stderr = ssh.exec_command('test -f ~/nastool-v4.0.0/nastool-core/pyproject.toml && echo "存在" || echo "不存在"')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    print(f"pyproject.toml: {out}")

    print("\n检查 nastool-core 的父目录内容 (应该包含 nastool-core):")
    stdin, stdout, stderr = ssh.exec_command('ls ~/nastool-v4.0.0/ 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    ssh.close()

if __name__ == "__main__":
    main()
