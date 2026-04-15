"""
core/network.py — 网络接口检测 + 连通性测试 + NAS 后端连通性
"""

import socket
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class NetworkInterface:
    name: str = ""
    ip: str = ""
    netmask: str = ""
    mac: str = ""
    speed_mbps: int = 0  # 0 = 未知
    duplex: str = ""  # full / half / ""
    up: bool = False
    is_wireless: bool = False


@dataclass
class ConnectivityTest:
    host: str = ""
    port: int = 0
    reachable: bool = False
    rtt_ms: float = 0.0
    error: str = ""


@dataclass
class NetworkReport:
    interfaces: List[NetworkInterface] = field(default_factory=list)
    dns_ok: bool = False
    gateway_reachable: bool = False
    internet_reachable: bool = False
    nas_backend: ConnectivityTest = field(default_factory=ConnectivityTest)
    errors: List[str] = field(default_factory=list)
    ok: bool = False

    def best_ip(self) -> str:
        """返回第一个有 IP 的非 lo 接口"""
        for iface in self.interfaces:
            if iface.up and iface.ip and not iface.ip.startswith("127."):
                return iface.ip
        return "未知"


def _run(cmd: str, timeout: int = 5) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except subprocess.CalledProcessError:
        return ""
    except FileNotFoundError:
        return ""


def get_interfaces() -> List[NetworkInterface]:
    """用 ip addr 读取所有网络接口"""
    interfaces = []
    out = _run("ip -br addr 2>/dev/null")
    if not out:
        # 备选：ifconfig
        out = _run("ip addr 2>/dev/null")

    current = None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            current = None
            continue

        # ip -br addr 格式: eth0  UP  192.168.1.123/24
        parts = line.split()
        if len(parts) >= 2:
            # 检测是否 UP
            state = "UP" if "UP" in line else ("DOWN" if "DOWN" in line else "")
            if state or (parts[0] not in ("lo", "docker", "veth")):
                iface = NetworkInterface()
                iface.name = parts[0]
                iface.up = state == "UP"
                # 解析 IP
                for p in parts:
                    if "/" in p and _is_ipv4(p):
                        iface.ip = p.split("/")[0]
                        iface.netmask = _cidr_to_netmask(p.split("/")[1])
                        break
                interfaces.append(iface)
                current = iface

    # 补充 speed/mac/duplex
    for iface in interfaces:
        # MAC
        mac_out = _run(f"cat /sys/class/net/{iface.name}/address 2>/dev/null")
        if mac_out:
            iface.mac = mac_out.upper()

        # 速率
        speed_path = f"/sys/class/net/{iface.name}/speed"
        try:
            spd = int(open(speed_path).read().strip())
            iface.speed_mbps = abs(spd)
        except (FileNotFoundError, PermissionError, ValueError):
            pass

        # 双工
        duplex_path = f"/sys/class/net/{iface.name}/duplex"
        try:
            iface.duplex = open(duplex_path).read().strip()
        except (FileNotFoundError, PermissionError):
            pass

        # 是否无线
        iface.is_wireless = os.path.exists(f"/sys/class/net/{iface.name}/wireless")

    return interfaces


def _is_ipv4(s: str) -> bool:
    try:
        socket.inet_aton(s)
        return True
    except (socket.error, OSError):
        return False


def _cidr_to_netmask(cidr: str) -> str:
    try:
        bits = int(cidr)
        mask = (0xFFFFFFFF >> (32 - bits)) & 0xFFFFFFFF
        return f"{(mask >> 24) & 0xFF}.{(mask >> 16) & 0xFF}.{(mask >> 8) & 0xFF}.{mask & 0xFF}"
    except ValueError:
        return ""


def test_connectivity(host: str, port: int = 80, timeout: int = 3) -> ConnectivityTest:
    """TCP 连通性测试（支持端口）"""
    test = ConnectivityTest(host=host, port=port)
    start = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        test.rtt_ms = round((time.time() - start) * 1000, 1)
        test.reachable = True
        sock.close()
    except socket.timeout:
        test.reachable = False
        test.error = "timeout"
    except ConnectionRefusedError:
        test.reachable = False
        test.error = "connection_refused"
    except OSError as e:
        test.reachable = False
        test.error = str(e)[:60]
    return test


def test_http(url: str, timeout: int = 5) -> bool:
    """HTTP GET 测试"""
    try:
        r = subprocess.run(
            f'curl -sf --max-time {timeout} "{url}"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout + 1,
        )
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except subprocess.CalledProcessError:
        return False


def check_network(nas_host: str = "120.77.249.3", nas_port: int = 8000) -> NetworkReport:
    """
    主入口：网络接口 + 网关 + 互联网 + NAS 后端连通性
    """
    import os

    report = NetworkReport()

    # 1. 接口列表
    report.interfaces = get_interfaces()

    # 2. DNS
    try:
        socket.gethostbyname("www.baidu.com")
        report.dns_ok = True
    except Exception as e:
        pass  # TODO: 添加日志

    # 3. 网关连通
    gw = _run("ip route | grep default | awk '{print $3}' | head -1", timeout=3)
    if gw:
        ping_out = _run(f"ping -c 1 -W 2 {gw}", timeout=4)
        report.gateway_reachable = "bytes from" in ping_out or "1 received" in ping_out

    # 4. 互联网（ping 百度）
    ping_out = _run(
        "ping -c 1 -W 3 8.8.8.8 2>/dev/null || ping -c 1 -W 3 114.114.114.114 2>/dev/null",
        timeout=6,
    )
    report.internet_reachable = "bytes from" in ping_out or "1 received" in ping_out

    # 5. NAS 后端（TCP 端口）
    report.nas_backend = test_connectivity(nas_host, nas_port)

    # 6. NAS 后端 HTTP
    if report.nas_backend.reachable:
        http_ok = test_http(f"http://{nas_host}:{nas_port}/health", timeout=5)
        if not http_ok:
            report.errors.append(f"NAS 后端 TCP 可达但 HTTP /health 无响应")

    # 综合判断
    report.ok = len([i for i in report.interfaces if i.up]) > 0 and report.nas_backend.reachable

    return report
