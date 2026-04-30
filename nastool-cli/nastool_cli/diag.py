#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nastool一键诊断 - 简化版远程检测

功能：
- 自动使用已保存的设备信息
- 直接通过SSH执行诊断
- 一条命令完成扫描和诊断

用法：
    nastool diag                # 诊断所有已保存的设备
    nastool diag 192.168.1.123  # 诊断指定IP

作者：NASTool Team
版本：4.1.0
"""

import argparse
import json
import os
import sys
import time
from typing import Optional, List, Dict, Any

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False


class Colors:
    """终端颜色"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    END = '\033[0m'

    @staticmethod
    def disable():
        for attr in ['RED', 'GREEN', 'YELLOW', 'BLUE', 'CYAN', 'WHITE', 'GRAY', 'BOLD', 'END']:
            setattr(Colors, attr, '')


class QuickDiagnose:
    """快速诊断类"""

    def __init__(self, host: str, port: int = 22, username: str = "nvidia", password: str = "nvidia"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None

        if sys.platform == 'win32':
            Colors.disable()

    def connect(self) -> bool:
        """连接到远程设备"""
        if not HAS_PARAMIKO:
            print(f"{Colors.RED}错误: 需要安装paramiko库{Colors.END}")
            print(f"请运行: pip install paramiko")
            return False

        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )
            print(f"{Colors.GREEN}✓{Colors.END} 已连接到 {self.host}")
            return True
        except Exception as e:
            print(f"{Colors.RED}✗{Colors.END} 连接失败: {e}")
            return False

    def run_command(self, command: str) -> tuple:
        """执行远程命令"""
        if not self.client:
            return "", "Not connected"

        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=30)
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            return output, error
        except Exception as e:
            return "", str(e)

    def diagnose(self) -> Dict[str, Any]:
        """执行快速诊断"""
        results = {
            'host': self.host,
            'status': 'unknown',
            'os': '',
            'cpu': '',
            'memory': '',
            'disk': '',
            'temperature': '',
            'gpu': '',
            'network': '',
            'errors': []
        }

        # 1. 获取系统信息
        print(f"\n{Colors.CYAN}收集系统信息...{Colors.END}")
        output, _ = self.run_command("uname -a && cat /etc/os-release | grep PRETTY_NAME")
        if output:
            results['os'] = output.strip()[:100]
            results['status'] = 'online'
        else:
            results['errors'].append('无法获取系统信息')
            results['status'] = 'error'
            return results

        # 2. 获取CPU信息
        output, _ = self.run_command("cat /proc/cpuinfo | grep 'model name' | head -1 && nproc")
        if output:
            results['cpu'] = output.strip()

        # 3. 获取内存信息
        output, _ = self.run_command("free -h | grep Mem")
        if output:
            results['memory'] = output.strip()

        # 4. 获取磁盘信息
        output, _ = self.run_command("df -h | grep -E '/$|/data' | head -2")
        if output:
            results['disk'] = output.strip()

        # 5. 获取温度信息
        output, _ = self.run_command("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || tegrastats --interval 1 5 2>/dev/null | tail -1 || echo 'N/A'")
        if output:
            temp_str = output.strip()
            if 'temp=' in temp_str.lower():
                results['temperature'] = temp_str
            elif temp_str != 'N/A' and temp_str.isdigit():
                results['temperature'] = f"{int(temp_str)/1000:.1f}°C"
            else:
                results['temperature'] = temp_str[:50]

        # 6. 获取GPU信息
        output, _ = self.run_command("nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu --format=csv,noheader 2>/dev/null || echo 'N/A'")
        if output and 'N/A' not in output:
            results['gpu'] = output.strip()
        else:
            results['gpu'] = 'No NVIDIA GPU detected'

        # 7. 获取网络状态
        output, _ = self.run_command("ip addr show | grep inet | grep -v127.0.0.1 | head -3")
        if output:
            results['network'] = output.strip()

        # 8. 获取运行时间
        output, _ = self.run_command("uptime -p")
        if output:
            results['uptime'] = output.strip()

        return results

    def print_results(self, results: Dict[str, Any]):
        """打印诊断结果"""
        print(f"""
{Colors.BOLD}{'='*60}
设备诊断报告: {results['host']}
{'='*60}{Colors.END}
""")

        if results['status'] == 'error':
            print(f"{Colors.RED}诊断失败: {results['errors'][0] if results['errors'] else '未知错误'}{Colors.END}")
            return

        # 系统信息
        print(f"{Colors.CYAN}📋 系统信息{Colors.END}")
        if results['os']:
            print(f"  操作系统: {results['os']}")
        if hasattr(results, 'uptime') and results.get('uptime'):
            print(f"  运行时间: {results['uptime']}")
        print()

        # CPU信息
        print(f"{Colors.CYAN}🖥️  CPU{Colors.END}")
        if results['cpu']:
            print(f"  {results['cpu']}")
        else:
            print(f"  {Colors.GRAY}无法获取CPU信息{Colors.END}")
        print()

        # 内存信息
        print(f"{Colors.CYAN}💾 内存{Colors.END}")
        if results['memory']:
            print(f"  {results['memory']}")
        else:
            print(f"  {Colors.GRAY}无法获取内存信息{Colors.END}")
        print()

        # 存储信息
        print(f"{Colors.CYAN}💿 存储{Colors.END}")
        if results['disk']:
            for line in results['disk'].split('\n'):
                print(f"  {line}")
        else:
            print(f"  {Colors.GRAY}无法获取存储信息{Colors.END}")
        print()

        # 温度信息
        print(f"{Colors.CYAN}🌡️  温度{Colors.END}")
        if results['temperature']:
            temp_val = results['temperature']
            # 判断温度是否过高
            if '°C' in temp_val:
                try:
                    temp_num = float(temp_val.replace('°C', '').strip())
                    if temp_num > 80:
                        color = Colors.RED
                    elif temp_num > 70:
                        color = Colors.YELLOW
                    else:
                        color = Colors.GREEN
                    print(f"  {color}{temp_val}{Colors.END}")
                except:
                    print(f"  {temp_val}")
            else:
                print(f"  {temp_val}")
        else:
            print(f"  {Colors.GRAY}无法获取温度信息{Colors.END}")
        print()

        # GPU信息
        print(f"{Colors.CYAN}🎮 GPU{Colors.END}")
        if results['gpu']:
            print(f"  {results['gpu']}")
        else:
            print(f"  {Colors.GRAY}无法获取GPU信息{Colors.END}")
        print()

        # 网络信息
        print(f"{Colors.CYAN}🌐 网络{Colors.END}")
        if results['network']:
            for line in results['network'].split('\n'):
                print(f"  {line}")
        else:
            print(f"  {Colors.GRAY}无法获取网络信息{Colors.END}")
        print()

        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()


def load_devices() -> List[Dict]:
    """加载已保存的设备"""
    db_path = os.path.join(os.path.expanduser("~"), '.nastool', 'devices.json')
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # devices.json的格式是 {ip: DeviceInfo}
                if isinstance(data, dict):
                    return [{'ip': ip, **info} for ip, info in data.items()]
                elif isinstance(data, list):
                    return data
                else:
                    return []
        except Exception as e:
            print(f"{Colors.YELLOW}警告: 加载设备失败: {e}{Colors.END}")
            return []
    return []


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="NASTool一键诊断 - 简化远程设备检测",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  nastool diag                    # 诊断所有已保存的设备
  nastool diag 192.168.1.123      # 诊断指定IP
  nastool diag --all              # 诊断所有已保存的设备

注意:
  默认使用用户名: nvidia, 密码: nvidia
  如需更改，请在代码中修改或使用SSH密钥认证
        """
    )

    parser.add_argument('host', nargs='?', help='设备IP地址')
    parser.add_argument('--all', '-a', action='store_true', help='诊断所有已保存的设备')
    parser.add_argument('--user', '-u', default='nvidia', help='SSH用户名 (默认: nvidia)')
    parser.add_argument('--port', '-p', type=int, default=22, help='SSH端口 (默认: 22)')
    parser.add_argument('--password', '-P', default='nvidia', help='SSH密码 (默认: nvidia)')
    parser.add_argument('--no-color', action='store_true', help='禁用彩色输出')

    args = parser.parse_args()

    if args.no_color:
        Colors.disable()

    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════╗
║   NASTool 一键诊断 v4.1.0                                    ║
║   简化远程设备检测                                             ║
╚══════════════════════════════════════════════════════════╝{Colors.END}
""")

    hosts = []

    if args.all or not args.host:
        # 加载所有已保存的设备
        devices = load_devices()
        if devices:
            hosts = [d['ip'] for d in devices]
            print(f"{Colors.CYAN}将诊断 {len(hosts)} 个已保存的设备:{Colors.END}")
            for h in hosts:
                print(f"  - {h}")
        else:
            print(f"{Colors.YELLOW}没有已保存的设备{Colors.END}")
            print(f"请先运行: nastool scan 192.168.1.0/24")
            return 1
    else:
        hosts = [args.host]

    print()

    # 诊断每个设备
    for i, host in enumerate(hosts, 1):
        if len(hosts) > 1:
            print(f"\n{Colors.BOLD}[{i}/{len(hosts)}] 诊断 {host}{Colors.END}\n")

        diag = QuickDiagnose(
            host=host,
            port=args.port,
            username=args.user,
            password=args.password
        )

        if diag.connect():
            results = diag.diagnose()
            diag.print_results(results)
            diag.close()
        else:
            print(f"{Colors.RED}跳过 {host}{Colors.END}\n")

        if i < len(hosts):
            time.sleep(1)  # 设备间休息

    print(f"{Colors.GREEN}诊断完成！{Colors.END}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
