# -*- coding: utf-8 -*-
"""检查构建依赖问题"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.123', username='nvidia', password='nvidia', timeout=30)

    print("1. 检查构建依赖...")
    stdin, stdout, stderr = ssh.exec_command('pip3 install --user build wheel setuptools -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if 'Successfully' in out:
        print("  构建依赖安装成功")
    else:
        print("  构建依赖安装失败:")
        print(out[:300])
        if err:
            print("  错误:", err[:300])

    print("\n2. 检查nastool-core目录结构...")
    stdin, stdout, stderr = ssh.exec_command('ls -la ~/nastool-v4.0.0/nastool-core/ 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out[:300])

    print("\n3. 检查pyproject.toml...")
    stdin, stdout, stderr = ssh.exec_command('cat ~/nastool-v4.0.0/nastool-core/pyproject.toml 2>&1 | head -20')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out)

    print("\n4. 尝试直接安装（跳过构建依赖）...")
    stdin, stdout, stderr = ssh.exec_command('cd ~/nastool-v4.0.0/nastool-core && pip3 install --user --no-build-isolation . 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if 'Successfully' in out:
        print("  安装成功")
    else:
        print("  安装失败:")
        print(out[:300])
        if err:
            print("  错误:", err[:300])

    print("\n5. 验证安装...")
    stdin, stdout, stderr = ssh.exec_command('python3 -c "import nastool_core; print(nastool_core.__version__)" 2>&1')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    print(f"  nastool_core 版本: {out if out else '导入失败'}")

    ssh.close()

if __name__ == "__main__":
    main()
