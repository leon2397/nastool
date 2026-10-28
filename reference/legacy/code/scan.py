#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nastool scan - 一键设备检测模块

功能：
- 一键检测本地ARM设备
- 扫描指定IP或IP段
- 自动识别设备类型
- 支持批量检测
- 生成简洁的检测报告

用法：
    nastool scan                    # 检测本地设备
    nastool scan --local            # 仅检测本地
    nastool scan 192.168.1.123       # 检测指定IP
    nastool scan 192.168.1.0/24      # 扫描整个网段
    nastool scan --list             # 显示已保存的设备
    nastool scan --all              # 检测所有已保存的设备
    nastool scan --quick            # 快速检测（仅关键项）
    nastool scan --full             # 完整检测（含基准测试）

作者：NASTool Team
版本：4.1.0
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import socket
import struct
import platform

# 尝试导入必要的模块
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Windows兼容
import sys
if sys.platform != 'win32':
    try:
        import fcntl
        HAS_FCNTL = True
    except ImportError:
        HAS_FCNTL = False
else:
    HAS_FCNTL = False


@dataclass
class DeviceInfo:
    """设备信息"""
    ip: str
    port: int = 22
    hostname: str = ""
    device_type: str = ""
    device_family: str = ""
    status: str = "unknown"  # unknown, online, offline, ssh-open, http-open
    response_time: float = 0.0
    ssh_banner: str = ""
    http_title: str = ""
    mac_address: str = ""
    vendor: str = ""
    last_seen: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Colors:
    """终端颜色"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    @staticmethod
    def disable():
        for attr in ['RED', 'GREEN', 'YELLOW', 'BLUE', 'MAGENTA', 'CYAN', 'WHITE', 'GRAY', 'BOLD', 'UNDERLINE', 'END']:
            setattr(Colors, attr, '')


class DeviceScanner:
    """设备扫描器"""

    def __init__(self, timeout: int = 3, max_workers: int = 50):
        self.timeout = timeout
        self.max_workers = max_workers
        self.devices: List[DeviceInfo] = []

    def get_local_ip(self) -> str:
        """获取本机IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"

    def get_local_network(self) -> tuple:
        """获取本地网络信息"""
        local_ip = self.get_local_ip()
        parts = local_ip.split('.')
        network = '.'.join(parts[:3])
        return local_ip, f"{network}.0/24"

    def ip_range_to_list(self, ip_range: str) -> List[str]:
        """将IP范围转换为IP列表"""
        ips = []

        if '/' in ip_range:
            # CIDR notation (e.g., 192.168.1.0/24)
            ip, prefix = ip_range.split('/')
            prefix = int(prefix)

            # Calculate network address and broadcast address
            ip_int = struct.unpack('!I', socket.inet_aton(ip))[0]
            mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
            network = ip_int & mask
            broadcast = network | (~mask & 0xFFFFFFFF)

            # Generate IP list (skip network and broadcast)
            for i in range(network + 1, broadcast):
                ips.append(socket.inet_ntoa(struct.pack('!I', i)))
        elif '-' in ip_range:
            # Range notation (e.g., 192.168.1.1-10)
            start, end = ip_range.split('-')
            start_parts = start.split('.')
            base = '.'.join(start_parts[:3])
            start_num = int(start_parts[3])
            end_num = int(end)

            for i in range(start_num, end_num + 1):
                ips.append(f"{base}.{i}")
        else:
            # Single IP
            ips.append(ip_range)

        return ips

    def scan_port(self, ip: str, port: int) -> bool:
        """扫描单个端口"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False

    def check_ssh(self, ip: str, port: int = 22) -> Optional[str]:
        """检查SSH端口"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((ip, port))

            # 尝试读取SSH banner
            sock.send(b'\n')
            banner = sock.recv(256).decode('utf-8', errors='ignore').strip()

            sock.close()
            return banner if banner else ""
        except:
            return None

    def check_http(self, ip: str, port: int = 8000) -> Optional[str]:
        """检查HTTP端口"""
        if not HAS_REQUESTS:
            return None

        try:
            response = requests.get(f"http://{ip}:{port}", timeout=self.timeout, verify=False)
            title = ""
            if 'text/html' in response.headers.get('Content-Type', ''):
                # 简单提取title
                import re
                match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
                if match:
                    title = match.group(1)[:50]
            return f"HTTP {response.status_code}" + (f" - {title}" if title else "")
        except:
            return None

    def get_mac_vendor(self, mac: str) -> str:
        """获取MAC地址厂商（简化版）"""
        # 常见厂商MAC前缀
        vendors = {
            '00:50:56': 'VMware',
            '00:0c:29': 'VMware',
            '00:1c:42': 'Parallels',
            '08:00:27': 'VirtualBox',
            '34:7d:f6': 'Realtek',
            '3c:6d:66': 'Huawei',
            '64:6e:97': 'Huawei',
            '00:1a:11': 'Google',
            'f4:39:09': 'Huawei',
            '00:1e:68': 'Quanta',
            '00:25:90': 'Intel',
            '00:1b:21': 'Intel',
            'b8:27:eb': 'Raspberry Pi',
            'dc:a6:32': 'Raspberry Pi',
            'e4:5f:01': 'Raspberry Pi',
        }

        mac_prefix = ':'.join(mac.upper().split(':')[:3]) if ':' in mac else ':'.join(mac.upper()[:12].upper()[i:i+2] for i in range(0, 12, 2))

        return vendors.get(mac_prefix, "")

    def scan_device(self, ip: str) -> DeviceInfo:
        """扫描单个设备"""
        device = DeviceInfo(ip=ip, last_seen=datetime.now().isoformat())

        try:
            start_time = time.time()

            # 快速端口扫描
            ports_to_check = [22, 80, 443, 8000, 8080, 18888, 5000]

            for port in ports_to_check:
                if self.scan_port(ip, port):
                    if port == 22:
                        device.status = "ssh-open"
                        device.port = 22
                        device.ssh_banner = self.check_ssh(ip, port) or ""
                        break
                    elif port in [80, 443, 8000, 8080, 5000]:
                        device.status = "http-open"
                        device.port = port
                        device.http_title = self.check_http(ip, port) or ""
                        break
                    elif port == 18888:
                        device.status = "relay-open"
                        device.port = port
                        break

            device.response_time = (time.time() - start_time) * 1000  # ms

            if device.status == "unknown":
                device.status = "online" if self.scan_port(ip, 22) else "offline"

        except Exception as e:
            device.status = "error"
            device.error = str(e)

        return device

    def scan_range(self, ip_range: str, progress: bool = True) -> List[DeviceInfo]:
        """扫描IP范围"""
        ips = self.ip_range_to_list(ip_range)
        total = len(ips)
        devices = []

        if progress:
            print(f"{Colors.CYAN}正在扫描 {total} 个地址...{Colors.END}")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.scan_device, ip): ip for ip in ips}

            for i, future in enumerate(as_completed(futures), 1):
                device = future.result()
                devices.append(device)

                if progress and i % 10 == 0:
                    print(f"\r进度: {i}/{total} ({100*i//total}%)", end='', flush=True)

        if progress:
            print(f"\r{Colors.GREEN}扫描完成！{Colors.END}")

        # 过滤出在线设备
        online = [d for d in devices if d.status != "offline" and d.status != "error"]
        print(f"{Colors.GREEN}发现 {len(online)} 个在线设备 / {total} 总地址{Colors.END}")

        return devices


class DeviceDatabase:
    """设备数据库（简化版，使用JSON文件存储）"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            home = os.path.expanduser("~")
            self.db_path = os.path.join(home, '.nastool', 'devices.json')
        else:
            self.db_path = db_path

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.devices: Dict[str, DeviceInfo] = {}
        self.load()

    def load(self):
        """加载设备数据库"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.devices = {ip: DeviceInfo.from_dict(d) for ip, d in data.items()}
            except Exception as e:
                print(f"{Colors.YELLOW}警告: 无法加载设备数据库: {e}{Colors.END}")
                self.devices = {}

    def save(self):
        """保存设备数据库"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                data = {ip: d.to_dict() for ip, d in self.devices.items()}
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"{Colors.RED}错误: 无法保存设备数据库: {e}{Colors.END}")

    def add(self, device: DeviceInfo):
        """添加设备"""
        self.devices[device.ip] = device
        self.save()

    def remove(self, ip: str):
        """删除设备"""
        if ip in self.devices:
            del self.devices[ip]
            self.save()

    def get(self, ip: str) -> Optional[DeviceInfo]:
        """获取设备"""
        return self.devices.get(ip)

    def list_all(self) -> List[DeviceInfo]:
        """列出所有设备"""
        return list(self.devices.values())

    def update(self, ip: str, **kwargs):
        """更新设备信息"""
        if ip in self.devices:
            for key, value in kwargs.items():
                if hasattr(self.devices[ip], key):
                    setattr(self.devices[ip], key, value)
            self.save()


class NastoolScan:
    """NASTool Scan 主类"""

    def __init__(self, use_color: bool = True):
        self.scanner = DeviceScanner()
        self.db = DeviceDatabase()

        if not use_color or sys.platform == 'win32':
            Colors.disable()

    def print_banner(self):
        """打印横幅"""
        print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   {Colors.WHITE}{Colors.BOLD}NASTool Scanner v4.1.0{Colors.END}{Colors.CYAN}                               ║
║   {Colors.GRAY}ARM设备检测工具 - 一键发现与诊断{Colors.END}{Colors.CYAN}                      ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝{Colors.END}
""")

    def print_device_table(self, devices: List[DeviceInfo], show_all: bool = False):
        """打印设备表格"""
        if not devices:
            print(f"{Colors.YELLOW}没有发现设备{Colors.END}")
            return

        # 按状态排序
        status_order = {'ssh-open': 0, 'http-open': 1, 'relay-open': 2, 'online': 3, 'offline': 4, 'error': 5}
        devices = sorted(devices, key=lambda d: status_order.get(d.status, 99))

        # 打印表头
        print(f"\n{Colors.BOLD}{'IP Address':<16} {'Status':<12} {'Type':<10} {'Response':<10} {'Info':<30}{Colors.END}")
        print("-" * 80)

        for device in devices:
            if not show_all and device.status in ['offline', 'error']:
                continue

            # 状态颜色
            status_colors = {
                'ssh-open': Colors.GREEN,
                'http-open': Colors.GREEN,
                'relay-open': Colors.GREEN,
                'online': Colors.YELLOW,
                'offline': Colors.GRAY,
                'error': Colors.RED,
            }
            status_color = status_colors.get(device.status, Colors.WHITE)
            status_text = {
                'ssh-open': 'SSH OPEN',
                'http-open': 'HTTP OPEN',
                'relay-open': 'RELAY',
                'online': 'ONLINE',
                'offline': 'OFFLINE',
                'error': 'ERROR',
            }

            # 设备类型
            device_type = device.device_type or 'Unknown'

            # 响应时间
            response = f"{device.response_time:.0f}ms" if device.response_time else "-"

            # 设备信息
            info = ""
            if device.ssh_banner:
                if 'Ubuntu' in device.ssh_banner:
                    info = "Ubuntu"
                elif 'Debian' in device.ssh_banner:
                    info = "Debian"
                elif 'ARM' in device.ssh_banner:
                    info = "ARM"
                else:
                    info = device.ssh_banner[:28]
            elif device.http_title:
                info = device.http_title[:28]

            print(f"{device.ip:<16} {status_color}{status_text.get(device.status, device.status):<12}{Colors.END} {device_type:<10} {response:<10} {info:<30}")

        print()

    def cmd_discover(self, ip_range: str = None, save: bool = True):
        """发现设备"""
        if not ip_range:
            local_ip, ip_range = self.scanner.get_local_network()
            print(f"{Colors.CYAN}本地IP: {local_ip}{Colors.END}")
            print(f"{Colors.CYAN}扫描网段: {ip_range}{Colors.END}\n")

        devices = self.scanner.scan_range(ip_range)

        # 过滤在线设备
        online = [d for d in devices if d.status != 'offline' and d.status != 'error']

        if online:
            self.print_device_table(online)

            # 保存到数据库
            if save:
                for device in online:
                    self.db.add(device)
                print(f"{Colors.GREEN}已保存 {len(online)} 个设备到数据库{Colors.END}")
        else:
            print(f"{Colors.YELLOW}未发现在线设备{Colors.END}")

        return online

    def cmd_local(self):
        """检测本地设备"""
        print(f"{Colors.CYAN}检测本地ARM设备...{Colors.END}\n")

        local_ip = self.scanner.get_local_ip()
        print(f"{Colors.CYAN}本地IP: {local_ip}{Colors.END}")

        # 检测SSH
        ssh_banner = self.scanner.check_ssh(local_ip)
        if ssh_banner:
            print(f"{Colors.GREEN}✓{Colors.END} SSH端口开放")
            print(f"  Banner: {ssh_banner[:50]}")

            # 尝试识别设备类型
            if 'Ubuntu' in ssh_banner:
                print(f"  {Colors.GREEN}检测到Ubuntu系统{Colors.END}")
        else:
            print(f"{Colors.YELLOW}✗{Colors.END} SSH端口未开放（本地检测跳过）")

        print()

    def cmd_list(self):
        """列出已保存的设备"""
        devices = self.db.list_all()

        if not devices:
            print(f"{Colors.YELLOW}没有已保存的设备。使用 'nastool scan --discover' 发现设备{Colors.END}")
            return

        print(f"{Colors.CYAN}已保存的设备 ({len(devices)}):{Colors.END}\n")
        self.print_device_table(devices, show_all=True)

    def cmd_quick(self, target: str = None):
        """快速检测"""
        if target:
            # 检测指定IP
            device = self.scanner.scan_device(target)
            self.print_device_table([device])
            return device
        else:
            # 检测所有已保存的设备
            devices = self.db.list_all()
            if not devices:
                print(f"{Colors.YELLOW}没有已保存的设备。先运行 'nastool scan --discover'{Colors.END}")
                return []

            print(f"{Colors.CYAN}快速检测 {len(devices)} 个设备...{Colors.END}\n")

            results = []
            for device in devices:
                scanned = self.scanner.scan_device(device.ip)
                scanned.device_type = device.device_type
                results.append(scanned)

            self.print_device_table(results, show_all=True)
            return results

    def cmd_full(self, target: str = None):
        """完整检测"""
        if target:
            print(f"{Colors.CYAN}对 {target} 进行完整检测...{Colors.END}\n")

            # 使用NASTool的完整检测功能
            os.system(f'python -m nastool_cli.main --full --target {target}')
        else:
            # 检测所有已保存的设备
            devices = self.db.list_all()
            if not devices:
                print(f"{Colors.YELLOW}没有已保存的设备。先运行 'nastool scan --discover'{Colors.END}")
                return []

            print(f"{Colors.CYAN}完整检测 {len(devices)} 个设备...{Colors.END}\n")

            for device in devices:
                if device.status != 'offline':
                    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
                    print(f"{Colors.BOLD}检测设备: {device.ip}{Colors.END}")
                    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

                    os.system(f'python -m nastool_cli.main --full --target {device.ip}')

    def cmd_remove(self, ip: str):
        """删除设备"""
        if ip in [d.ip for d in self.db.list_all()]:
            self.db.remove(ip)
            print(f"{Colors.GREEN}已删除设备: {ip}{Colors.END}")
        else:
            print(f"{Colors.RED}设备不存在: {ip}{Colors.END}")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="NASTool Scanner - 一键ARM设备检测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  nastool scan                    # 发现局域网内的设备
  nastool scan --local            # 仅检测本地设备
  nastool scan 192.168.1.123      # 检测指定IP
  nastool scan 192.168.1.0/24     # 扫描整个网段
  nastool scan --list             # 列出已保存的设备
  nastool scan --quick            # 快速检测所有已保存的设备
  nastool scan --full             # 完整检测所有已保存的设备
  nastool scan --remove 192.168.1.123  # 从列表中删除设备

便捷操作:
  nastool scan                     # 默认扫描当前网络
  nastool scan 192                 # 快速扫描192.168.1.x
        """
    )

    parser.add_argument('target', nargs='?', help='目标IP、IP段或CIDR')
    parser.add_argument('--local', action='store_true', help='仅检测本地设备')
    parser.add_argument('--list', '-l', action='store_true', help='列出已保存的设备')
    parser.add_argument('--quick', '-q', action='store_true', help='快速检测')
    parser.add_argument('--full', '-f', action='store_true', help='完整检测（含基准测试）')
    parser.add_argument('--remove', '-r', metavar='IP', help='删除指定IP的设备')
    parser.add_argument('--no-color', action='store_true', help='禁用彩色输出')
    parser.add_argument('--timeout', '-t', type=int, default=3, help='扫描超时（秒）')
    parser.add_argument('--parallel', '-p', type=int, default=50, help='并行扫描数量')

    args = parser.parse_args()

    # 创建扫描器
    nastool = NastoolScan(use_color=not args.no_color)

    # 处理命令
    if args.local:
        nastool.cmd_local()
    elif args.list:
        nastool.cmd_list()
    elif args.quick:
        nastool.cmd_quick(args.target)
    elif args.full:
        nastool.cmd_full(args.target)
    elif args.remove:
        nastool.cmd_remove(args.remove)
    elif args.target:
        # 处理便捷输入（如 "192" 表示 "192.168.1.0/24"）
        target = args.target
        if target.isdigit() and len(target) <= 3:
            target = f"192.168.1.0/24"

        nastool.cmd_discover(target)
    else:
        # 默认：发现设备
        nastool.cmd_discover()


if __name__ == '__main__':
    main()
