# -*- coding: utf-8 -*-
"""Jetson 状态检查脚本"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.123', username='nvidia', password='nvidia', timeout=10)

    commands = [
        ('nastool_core 版本', 'python3 -c "import nastool_core; print(nastool_core.__version__)" 2>&1'),
        ('nastool_cli 版本', 'python3 -c "import nastool_cli; print(nastool_cli.__version__)" 2>&1'),
        ('nastool 路径', 'which nastool 2>&1'),
        ('nastool 目录', 'ls -la ~/nastool-v4.0.0 2>&1 | head -10'),
        ('.local/bin 目录', 'ls -la ~/.local/bin 2>&1 | head -10'),
        ('PATH 环境变量', 'echo $PATH'),
    ]

    for desc, cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        print(f"{desc}:")
        print(f"  stdout: {out}")
        if err:
            print(f"  stderr: {err}")
        print()

    ssh.close()

if __name__ == "__main__":
    main()
