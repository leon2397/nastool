# -*- coding: utf-8 -*-
"""Jetson 安装加速脚本"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.123', username='nvidia', password='nvidia', timeout=30)

    print("1. 检查当前安装状态...")
    # 检查是否有pip进程在运行
    stdin, stdout, stderr = ssh.exec_command('ps aux | grep pip3 | grep -v grep')
    out = stdout.read().decode('utf-8', errors='replace')
    if out.strip():
        print("  发现正在运行的 pip3 进程，需要中断")
        # 中断pip进程
        stdin, stdout, stderr = ssh.exec_command('pkill -f pip3')
        print("  已中断 pip3 进程")
    else:
        print("  没有运行的 pip3 进程")

    print("\n2. 测试网络连接...")
    stdin, stdout, stderr = ssh.exec_command('ping -c 3 pypi.org')
    out = stdout.read().decode('utf-8', errors='replace')
    if '0% packet loss' in out:
        print("  网络连接正常")
    else:
        print("  网络连接可能有问题:")
        print(out[:200])

    print("\n3. 清理pip缓存...")
    stdin, stdout, stderr = ssh.exec_command('pip3 cache purge 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    print("  完成")

    print("\n4. 配置国内pip源并安装依赖...")
    # 安装主要依赖
    stdin, stdout, stderr = ssh.exec_command('pip3 install --user pydantic requests paramiko -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if 'Successfully' in out:
        print("  依赖安装成功")
    else:
        print("  依赖安装失败:")
        print(out[:300])
        if err:
            print("  错误:", err[:300])

    print("\n5. 使用国内源安装nastool-core...")
    stdin, stdout, stderr = ssh.exec_command('cd ~/nastool-v4.0.0/nastool-core && pip3 install --user . -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if 'Successfully' in out:
        print("  nastool-core 安装成功")
    else:
        print("  nastool-core 安装失败:")
        print(out[:300])
        if err:
            print("  错误:", err[:300])

    print("\n6. 验证安装...")
    stdin, stdout, stderr = ssh.exec_command('python3 -c "import nastool_core; print(nastool_core.__version__)" 2>&1')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    print(f"  nastool_core 版本: {out if out else '导入失败'}")

    ssh.close()

if __name__ == "__main__":
    main()
