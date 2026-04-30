#!/usr/bin/env python3
import paramiko
import json

# 设备配置
HOST = "192.168.1.102"
PORT = 22
USERNAME = "root"
PASSWORD = "linaro123"

def connect():
    """建立SSH连接"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=HOST,
            port=PORT,
            username=USERNAME,
            password=PASSWORD,
            timeout=15,
            allow_agent=False,
            look_for_keys=False
        )
        print("✓ SSH连接成功")
        return client
    except Exception as e:
        print(f"✗ SSH连接失败: {e}")
        return None

def execute_command(client, command, desc=""):
    """执行命令并返回结果"""
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        error = stderr.read().decode('utf-8', errors='ignore').strip()
        return output, error
    except Exception as e:
        return "", str(e)

def run_diagnosis(client):
    """执行完整诊断"""
    print("\n" + "="*60)
    print("         NASTool 昇腾设备远程诊断测试")
    print("="*60)
    
    tests = [
        ("uname -a", "系统信息"),
        ("cat /etc/os-release", "操作系统"),
        ("cat /proc/cpuinfo | head -20", "CPU信息"),
        ("free -h", "内存信息"),
        ("df -h", "磁盘信息"),
        ("npu-smi info", "NPU信息"),
        ("python3 --version", "Python版本"),
        ("pip list 2>/dev/null | head -10", "已安装包"),
    ]
    
    results = []
    for cmd, desc in tests:
        print(f"\n{desc}:")
        print("-" * 30)
        output, error = execute_command(client, cmd)
        if output:
            print(output)
        if error:
            print(f"警告: {error}")
        results.append({"test": desc, "result": output if output else error})
    
    return results

def main():
    client = connect()
    if not client:
        print("无法连接到设备，测试终止")
        return
    
    try:
        results = run_diagnosis(client)
        
        # 保存结果到文件
        with open("test_results_ascend.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("\n✓ 测试结果已保存到 test_results_ascend.json")
        
    finally:
        client.close()
        print("✓ SSH连接已关闭")

if __name__ == "__main__":
    main()
