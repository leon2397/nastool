# -*- coding: utf-8 -*-
"""Jetson 详细状态检查"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.123', username='nvidia', password='nvidia', timeout=30)

    print("检查 nastool-v4.0.0 直接子目录:")
    stdin, stdout, stderr = ssh.exec_command('ls -d ~/nastool-v4.0.0/*/  2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out if out.strip() else "无子目录")

    print("\n检查 nastool-core 内容:")
    stdin, stdout, stderr = ssh.exec_command('ls ~/nastool-v4.0.0/nastool-core/  2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out if out.strip() else "目录为空或不存在")

    print("\n检查 nastool-common 内容:")
    stdin, stdout, stderr = ssh.exec_command('ls ~/nastool-v4.0.0/nastool-common/  2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out if out.strip() else "目录为空或不存在")

    print("\n检查 nastool-core/__init__.py:")
    stdin, stdout, stderr = ssh.exec_command('test -f ~/nastool-v4.0.0/nastool-core/nastool_core/__init__.py && echo "存在" || echo "不存在"')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    print(f"nastool_core/__init__.py: {out}")

    print("\n检查 nastool-core/pyproject.toml:")
    stdin, stdout, stderr = ssh.exec_command('test -f ~/nastool-v4.0.0/nastool-core/pyproject.toml && echo "存在" || echo "不存在"')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    print(f"pyproject.toml: {out}")

    ssh.close()

if __name__ == "__main__":
    main()
