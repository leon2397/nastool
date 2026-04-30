# -*- coding: utf-8 -*-
"""简化安装脚本"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.123', username='nvidia', password='nvidia', timeout=30)

    print("检查当前状态...")
    stdin, stdout, stderr = ssh.exec_command('ls -la ~/nastool-v4.0.0/nastool-core/ 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n检查pip版本...")
    stdin, stdout, stderr = ssh.exec_command('pip3 --version')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n尝试使用 --no-build-isolation 安装...")
    stdin, stdout, stderr = ssh.exec_command('cd ~/nastool-v4.0.0/nastool-core && pip3 install --user --no-build-isolation . 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out[:500])

    print("\n验证安装...")
    stdin, stdout, stderr = ssh.exec_command('python3 -c "import nastool_core; print(nastool_core.__version__)" 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    ssh.close()

if __name__ == "__main__":
    main()
