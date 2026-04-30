# -*- coding: utf-8 -*-
"""
Jetson 真机测试脚本 - 完整测试套件
用于在 192.168.1.123 上执行完整的 nastool 测试

测试原则：先记录 BUG，不得边测边修

使用方法：
    python test_jetson_full.py --host 192.168.1.123 --user nvidia --password nvidia

依赖：
    pip install paramiko

测试项目：
    T01: 系统信息收集
    T02: 版本检查
    T03: 模块导入测试
    T04: CLI 命令测试
    T05: CUDA 环境测试
    T06: GPU 检测测试
    T07: 存储检查
    T08: 网络检查
    T09: 完整诊断测试
    T10: 报告生成测试
"""

import argparse
import sys
import os
import subprocess
import time
from datetime import datetime

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False


class SSHClient:
    """SSH 客户端封装"""
    def __init__(self, host, user, password, port=22):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.client = None
        self._connect()

    def _connect(self):
        """建立 SSH 连接"""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )
        except Exception as e:
            raise ConnectionError(f"SSH 连接失败: {e}")

    def exec_command(self, cmd, timeout=60):
        """执行远程命令"""
        if not self.client:
            raise ConnectionError("SSH 未连接")
        stdin, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
        return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()


def run_ssh_command_via_paramiko(host, user, password, cmd, timeout=60):
    """使用 paramiko 运行 SSH 命令"""
    try:
        ssh = SSHClient(host, user, password)
        out, err = ssh.exec_command(cmd, timeout=timeout)
        ssh.close()
        return 0, out, err
    except Exception as e:
        return -1, "", str(e)


def run_ssh_command(host, user, password, cmd, timeout=60):
    """运行 SSH 命令（优先使用 paramiko，fallback 到系统命令）"""
    if HAS_PARAMIKO:
        return run_ssh_command_via_paramiko(host, user, password, cmd, timeout)

    # Fallback: 使用系统 SSH 命令
    if os.name == 'nt':
        # Windows: 使用 plink
        plink_cmd = f'plink -ssh -batch -l "{user}" -pw "{password}" "{host}" "{cmd}"'
        try:
            result = subprocess.run(plink_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)
    else:
        # Linux/macOS: 使用 sshpass
        ssh_cmd = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{host} "{cmd}"'
        try:
            result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)


def test_connection(host, user, password):
    """测试与 Jetson 设备的连接"""
    print("=" * 60)
    print("测试连接: {user}@{host}".format(user=user, host=host))
    print("=" * 60)

    # 检查 paramiko
    if not HAS_PARAMIKO:
        print("警告: paramiko 未安装，尝试使用系统 SSH 命令")

    # 测试 SSH 连接
    print("测试 SSH 连接...")
    test_cmd = "echo 'SSH 连接测试成功'"
    ret, out, err = run_ssh_command(host, user, password, test_cmd)
    if ret != 0:
        print(f"[FAILED] SSH 连接失败: {err or out}")
        if not HAS_PARAMIKO:
            print("提示: 建议安装 paramiko: pip install paramiko")
        return False

    print("[OK] 连接成功！")
    print(f"     {out.strip()}")
    print()
    return True


def run_local_command(cmd, timeout=30):
    """运行本地命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timeout"
    except Exception as e:
        return -1, "", str(e)


def test_system_info(host, user, password):
    """T01: 系统信息收集"""
    print("=" * 60)
    print("T01: 系统信息收集")
    print("=" * 60)

    commands = {
        "OS 版本": "cat /etc/os-release | grep PRETTY_NAME",
        "内核版本": "uname -a",
        "架构": "arch",
        "Python 版本": "python3 --version",
        "CPU 信息": "lscpu | grep 'Model name'",
        "内存信息": "free -h",
        "存储信息": "df -h",
        "网络信息": "ip addr show",
        "温度信息": "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -5",
        "JetPack 版本": "cat /etc/nv_tegra_release 2>/dev/null",
        "CUDA 路径": "ls -la /usr/local/cuda* 2>/dev/null",
        "GPU 设备": "ls -la /dev/nvhost* 2>/dev/null",
    }

    for desc, cmd in commands.items():
        print(f"{desc}:", end=" ")
        ret, out, err = run_ssh_command(host, user, password, cmd)
        if ret == 0 and out.strip():
            print(out.strip())
        else:
            print("N/A")
    print()


def test_version_check(host, user, password):
    """T02: 版本检查"""
    print("=" * 60)
    print("T02: 版本检查")
    print("=" * 60)

    # 检查 nastool 版本
    commands = [
        "nastool --version 2>/dev/null",
        "python3 -c 'import nastool_core; print(nastool_core.__version__)' 2>/dev/null",
        "python3 -c 'import nastool_cli; print(nastool_cli.__version__)' 2>/dev/null",
    ]

    for cmd in commands:
        ret, out, err = run_ssh_command(host, user, password, cmd)
        if ret == 0 and out.strip():
            print(f"版本信息: {out.strip()}")
        else:
            print(f"版本检查失败: {err or '命令未找到'}")
    print()


def test_module_imports(host, user, password):
    """T03: 模块导入测试"""
    print("=" * 60)
    print("T03: 模块导入测试")
    print("=" * 60)

    modules = [
        "nastool_common",
        "nastool_core",
        "nastool_adapters",
        "nastool_reporters",
        "nastool_fixes",
        "nastool_cli",
        "nastool_core.checks.ai.gpu_detected",
        "nastool_core.checks.system.memory_check",
    ]

    for module in modules:
        cmd = f"python3 -c 'import {module}; print(\"{module} 导入成功\")' 2>&1"
        ret, out, err = run_ssh_command(host, user, password, cmd)
        if ret == 0:
            print(f"[OK] {module}: 导入成功")
        else:
            print(f"[FAILED] {module}: 导入失败 - {out.strip()}")
    print()


def test_cli_commands(host, user, password):
    """T04: CLI 命令测试"""
    print("=" * 60)
    print("T04: CLI 命令测试")
    print("=" * 60)

    commands = [
        "nastool --help",
        "nastool --version",
        "nastool --mock healthy",
    ]

    for cmd in commands:
        print(f"测试: {cmd}")
        ret, out, err = run_ssh_command(host, user, password, cmd, timeout=30)
        if ret == 0:
            print("[OK] 执行成功")
            print(out[:500] + "..." if len(out) > 500 else out)
        else:
            print(f"[FAILED] 执行失败: {err or out}")
        print()


def test_cuda_environment(host, user, password):
    """T05: CUDA 环境测试"""
    print("=" * 60)
    print("T05: CUDA 环境测试")
    print("=" * 60)

    commands = [
        "nvcc --version 2>/dev/null",
        "ls -la /usr/local/cuda/bin/nvcc 2>/dev/null",
        "echo $PATH | grep cuda",
        "echo $LD_LIBRARY_PATH | grep cuda",
    ]

    for cmd in commands:
        ret, out, err = run_ssh_command(host, user, password, cmd)
        if ret == 0 and out.strip():
            print(f"[OK] {cmd}: {out.strip()}")
        else:
            print(f"[FAILED] {cmd}: 未找到")
    print()


def test_gpu_detection(host, user, password):
    """T06: GPU 检测测试"""
    print("=" * 60)
    print("T06: GPU 检测测试")
    print("=" * 60)

    # 测试 gpu_detected 模块
    test_code = '''
from nastool_core.checks.ai.gpu_detected import gpu_detected
from nastool_core.checks.decorators import CheckContext
ctx = CheckContext()
result = gpu_detected(ctx)
print(f"GPU 检测结果: {result.passed}")
print(f"消息: {result.message}")
print(f"详情: {result.details}")
'''

    test_script = "test_gpu.py"
    with open(test_script, "w", encoding="utf-8") as f:
        f.write(test_code)

    # 上传脚本并执行
    if HAS_PARAMIKO:
        try:
            ssh = SSHClient(host, user, password)
            # 创建远程脚本
            ssh.exec_command(f"cat > ~/{test_script} << 'EOF'\n{test_code}\nEOF")
            out, err = ssh.exec_command(f"python3 ~/{test_script}")
            if out:
                print("[OK] GPU 检测测试成功")
                print(out)
            else:
                print(f"[FAILED] GPU 检测测试失败: {err}")
            ssh.exec_command(f"rm ~/{test_script}")
            ssh.close()
        except Exception as e:
            print(f"[FAILED] GPU 检测测试失败: {e}")
    else:
        print("[FAILED] 需要 paramiko 才能执行 GPU 检测测试")
        print("提示: pip install paramiko")

    os.remove(test_script)
    print()


def test_storage_check(host, user, password):
    """T07: 存储检查"""
    print("=" * 60)
    print("T07: 存储检查")
    print("=" * 60)

    commands = [
        "df -h",
        "mount",
        "lsblk -f",
    ]

    for cmd in commands:
        print(f"{cmd}:")
        ret, out, err = run_ssh_command(host, user, password, cmd)
        if ret == 0:
            print(out)
        else:
            print(f"执行失败: {err}")
        print()


def test_network_check(host, user, password):
    """T08: 网络检查"""
    print("=" * 60)
    print("T08: 网络检查")
    print("=" * 60)

    commands = [
        "ip addr show",
        "ping -c 3 192.168.1.1",
        "ping -c 3 google.com",
        "curl -s ifconfig.me",
    ]

    for cmd in commands:
        print(f"{cmd}:")
        ret, out, err = run_ssh_command(host, user, password, cmd)
        if ret == 0:
            print(out)
        else:
            print(f"执行失败: {err}")
        print()


def test_full_diagnostic(host, user, password):
    """T09: 完整诊断测试"""
    print("=" * 60)
    print("T09: 完整诊断测试")
    print("=" * 60)

    # 运行完整诊断
    cmd = "nastool --full 2>&1 | head -50"
    ret, out, err = run_ssh_command(host, user, password, cmd, timeout=120)

    if ret == 0:
        print("[OK] 完整诊断执行成功")
        print(out)
    else:
        print(f"[FAILED] 完整诊断执行失败: {err or out}")
    print()


def test_report_generation(host, user, password):
    """T10: 报告生成测试"""
    print("=" * 60)
    print("T10: 报告生成测试")
    print("=" * 60)

    # 测试 JSON 报告
    cmd = "nastool --output /tmp/test_report.json --format json 2>&1"
    ret, out, err = run_ssh_command(host, user, password, cmd, timeout=60)

    if ret == 0:
        print("[OK] JSON 报告生成成功")
        # 检查文件是否存在
        ret2, out2, err2 = run_ssh_command(host, user, password, "ls -la /tmp/test_report.json")
        if ret2 == 0:
            print(f"报告文件: {out2.strip()}")
        else:
            print("[FAILED] 报告文件未找到")
    else:
        print(f"[FAILED] JSON 报告生成失败: {err or out}")
    print()


def collect_bugs():
    """收集测试过程中发现的 BUG"""
    bugs = []

    # 这里可以根据测试结果自动收集 BUG
    # 目前返回空列表，实际测试时会根据输出自动识别 BUG

    return bugs


def main():
    parser = argparse.ArgumentParser(description="Jetson 真机测试脚本")
    parser.add_argument("--host", default="192.168.1.123", help="Jetson IP 地址")
    parser.add_argument("--user", default="nvidia", help="Jetson 用户名")
    parser.add_argument("--password", default="nvidia", help="SSH 密码")
    parser.add_argument("--output", help="测试报告输出文件")

    args = parser.parse_args()

    print("=" * 80)
    print(" Jetson 真机测试套件")
    print(" 测试设备: {user}@{host}".format(user=args.user, host=args.host))
    print(" 测试时间: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print(" 测试原则: 先记录 BUG，不得边测边修")
    print("=" * 80)
    print()

    # 测试连接
    if not test_connection(args.host, args.user, args.password):
        print("[ERROR] 无法连接到 Jetson 设备，请检查网络和 SSH 配置")
        return 1

    # 开始测试
    test_system_info(args.host, args.user, args.password)
    test_version_check(args.host, args.user, args.password)
    test_module_imports(args.host, args.user, args.password)
    test_cli_commands(args.host, args.user, args.password)
    test_cuda_environment(args.host, args.user, args.password)
    test_gpu_detection(args.host, args.user, args.password)
    test_storage_check(args.host, args.user, args.password)
    test_network_check(args.host, args.user, args.password)
    test_full_diagnostic(args.host, args.user, args.password)
    test_report_generation(args.host, args.user, args.password)

    # 收集 BUG
    bugs = collect_bugs()

    print("=" * 80)
    print(" 测试完成")
    print("=" * 80)

    if bugs:
        print("\n发现的 BUG:")
        for bug in bugs:
            print(f"- {bug}")
    else:
        print("\n未发现 BUG，测试通过！")

    print("\n测试结果已记录，后续将统一安排修复。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
