# -*- coding: utf-8 -*-
"""Jetson 安装检查和修复脚本 v2"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.123', username='nvidia', password='nvidia', timeout=30)

    # 1. 升级 pip
    print("=" * 60)
    print("1. 升级 pip")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('pip3 install --upgrade pip 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out if out.strip() else "pip 已是最新或升级失败")
    if err and 'error' in err.lower():
        print("警告:", err[:200])

    # 2. 检查目录
    print("\n" + "=" * 60)
    print("2. 检查 nastool 目录")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('ls -la ~/nastool-v4.0.0/ 2>&1 | head -20')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out if out.strip() else "目录为空或不存在")

    # 3. 尝试使用非 editable 模式安装
    print("\n" + "=" * 60)
    print("3. 安装 nastool-common (非 editable)")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('cd ~/nastool-v4.0.0/nastool-common && pip3 install --user . 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out if out.strip() else "安装失败")
    if err and 'error' in err.lower():
        print("错误:", err[:300])

    print("\n" + "=" * 60)
    print("4. 安装 nastool-core (非 editable)")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('cd ~/nastool-v4.0.0/nastool-core && pip3 install --user . 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out if out.strip() else "安装失败")
    if err and 'error' in err.lower():
        print("错误:", err[:300])

    print("\n" + "=" * 60)
    print("5. 安装 nastool-cli (非 editable)")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('cd ~/nastool-v4.0.0/nastool-cli && pip3 install --user . 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out if out.strip() else "安装失败")
    if err and 'error' in err.lower():
        print("错误:", err[:300])

    # 4. 验证安装
    print("\n" + "=" * 60)
    print("6. 验证安装")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('python3 -c "import nastool_core; print(nastool_core.__version__)" 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print("nastool_core:", out.strip() if out.strip() else "FAILED")

    stdin, stdout, stderr = ssh.exec_command('python3 -c "import nastool_cli; print(nastool_cli.__version__)" 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print("nastool_cli:", out.strip() if out.strip() else "FAILED")

    stdin, stdout, stderr = ssh.exec_command('which nastool 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print("nastool path:", out.strip() if out.strip() else "not found")

    # 5. 配置 PATH
    print("\n" + "=" * 60)
    print("7. 配置 PATH")
    print("=" * 60)
    ssh.exec_command('echo "export PATH=$HOME/.local/bin:$PATH" >> ~/.bashrc 2>&1')
    ssh.exec_command('echo "export PATH=/usr/local/cuda/bin:$PATH" >> ~/.bashrc 2>&1')
    print("PATH 配置完成")
    print("请运行: source ~/.bashrc")

    ssh.close()
    print("\n完成!")

if __name__ == "__main__":
    main()
