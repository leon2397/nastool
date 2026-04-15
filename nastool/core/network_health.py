# -*- coding: utf-8 -*-
"""
core/network_health.py — 网络健康检测
带宽测试 / 端口扫描 / DNS 覆盖 / 网卡速率 / 连接状态
"""

import os
import re
import socket
import subprocess
import time
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed


class PortStatus(Enum):
    """端口状态"""

    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNKNOWN = "unknown"


class LinkState(Enum):
    """链路状态"""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class BandwidthResult:
    """带宽测试结果"""

    download_mbps: float = 0.0
    upload_mbps: float = 0.0
    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss: float = 0.0
    test_server: str = ""
    error: str = ""


@dataclass
class PortScanResult:
    """端口扫描结果"""

    port: int
    status: PortStatus
    service: str = ""
    banner: str = ""


@dataclass
class DNSResult:
    """DNS 解析结果"""

    server: str
    domain: str
    ip: str = ""
    rtt_ms: float = 0.0
    success: bool = False
    error: str = ""


@dataclass
class InterfaceHealth:
    """网卡健康信息"""

    name: str
    ip: str = ""
    mac: str = ""
    speed_mbps: int = 0
    duplex: str = ""
    link_state: LinkState = LinkState.UNKNOWN
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_errors: int = 0
    tx_errors: int = 0
    rx_dropped: int = 0
    tx_dropped: int = 0
    is_wireless: bool = False
    wifi_ssid: str = ""
    wifi_signal_dbm: int = 0


@dataclass
class NetworkHealthReport:
    """网络健康报告"""

    timestamp: str
    interfaces: List[InterfaceHealth] = field(default_factory=list)
    bandwidth: BandwidthResult = field(default_factory=BandwidthResult)
    port_scan: List[PortScanResult] = field(default_factory=list)
    dns_results: List[DNSResult] = field(default_factory=list)
    gateway: str = ""
    gateway_reachable: bool = False
    internet_reachable: bool = False
    health_score: int = 0
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ok: bool = True


def _run(cmd: str, timeout: int = 10) -> str:
    """执行命令并返回输出"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return ""


# ══════════════════════════════════════════════════════════════════
# 带宽测试
# ══════════════════════════════════════════════════════════════════


def test_bandwidth_speedtest() -> BandwidthResult:
    """
    使用 speedtest-cli 测试带宽

    Returns:
        BandwidthResult
    """
    result = BandwidthResult()

    # 检查 speedtest-cli 是否安装
    check = _run("which speedtest-cli || which speedtest")
    if not check:
        result.error = "speedtest-cli 未安装"
        return result

    # 执行测试
    output = _run(
        "speedtest-cli --simple 2>/dev/null || speedtest --simple 2>/dev/null", timeout=60
    )
    if not output:
        result.error = "speedtest 测试失败"
        return result

    # 解析输出
    # 示例:
    # Ping: 5.23 ms
    # Download: 100.23 Mbit/s
    # Upload: 50.12 Mbit/s
    for line in output.splitlines():
        if "Download:" in line:
            match = re.search(r"([\d.]+)\s*Mbit/s", line)
            if match:
                result.download_mbps = float(match.group(1))
        elif "Upload:" in line:
            match = re.search(r"([\d.]+)\s*Mbit/s", line)
            if match:
                result.upload_mbps = float(match.group(1))
        elif "Ping:" in line:
            match = re.search(r"([\d.]+)\s*ms", line)
            if match:
                result.latency_ms = float(match.group(1))

    return result


def test_bandwidth_iperf(server: str = "iperf.he.net") -> BandwidthResult:
    """
    使用 iperf3 测试带宽

    Args:
        server: iperf3 服务器地址
    """
    result = BandwidthResult(test_server=server)

    # 检查 iperf3 是否安装
    check = _run("which iperf3")
    if not check:
        result.error = "iperf3 未安装"
        return result

    # 执行测试
    output = _run(f"iperf3 -c {server} -t 5 -P 2 2>/dev/null", timeout=30)
    if not output:
        result.error = "iperf3 测试失败"
        return result

    # 解析输出
    # [SUM]   0.00-5.00   sec  1.2 GBytes  2.1 Gbits/sec  sender
    for line in output.splitlines():
        if "sender" in line and "Gbits/sec" in line:
            match = re.search(r"([\d.]+)\s*Gbits/sec", line)
            if match:
                result.download_mbps = float(match.group(1)) * 1000
        elif "receiver" in line and "Gbits/sec" in line:
            match = re.search(r"([\d.]+)\s*Gbits/sec", line)
            if match:
                result.upload_mbps = float(match.group(1)) * 1000
        elif "sender" in line and "Mbits/sec" in line:
            match = re.search(r"([\d.]+)\s*Mbits/sec", line)
            if match:
                result.download_mbps = float(match.group(1))

    return result


def test_bandwidth_simple(host: str = "8.8.8.8", size_kb: int = 100) -> BandwidthResult:
    """
    简单带宽测试（ping + 下载测试）

    Args:
        host: 测试目标
        size_kb: 测试数据大小（KB）
    """
    result = BandwidthResult()

    # 延迟测试
    ping_out = _run(f"ping -c 5 -i 0.2 {host} 2>/dev/null", timeout=10)
    if ping_out:
        # 解析延迟
        match = re.search(r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/", ping_out)
        if match:
            result.latency_ms = float(match.group(2))

        # 解析丢包
        match = re.search(r"(\d+)% packet loss", ping_out)
        if match:
            result.packet_loss = float(match.group(1))

    # 简单下载测试（curl）
    curl_out = _run(
        f"curl -o /dev/null -w '%{{speed_download}}' --connect-timeout 5 --max-time 10 http://{host}/ 2>/dev/null",
        timeout=15,
    )
    if curl_out:
        try:
            speed_bytes = float(curl_out)
            result.download_mbps = round(speed_bytes * 8 / 1024 / 1024, 1)
        except Exception as e:
            pass

    return result


# ══════════════════════════════════════════════════════════════════
# 端口扫描
# ══════════════════════════════════════════════════════════════════

COMMON_PORTS = {
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    465: "SMTPS",
    587: "SMTP",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    1521: "Oracle",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    6379: "Redis",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
    9000: "PHP-FPM",
    9200: "Elasticsearch",
    27017: "MongoDB",
}


def scan_port(host: str, port: int, timeout: float = 1.0) -> PortScanResult:
    """
    扫描单个端口

    Args:
        host: 目标主机
        port: 端口号
        timeout: 超时时间
    """
    result = PortScanResult(
        port=port, status=PortStatus.UNKNOWN, service=COMMON_PORTS.get(port, "")
    )

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start = time.time()
        code = sock.connect_ex((host, port))

        if code == 0:
            result.status = PortStatus.OPEN
            # 尝试获取 banner
            try:
                sock.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
                banner = sock.recv(1024).decode("utf-8", errors="ignore")
                result.banner = banner[:100]
            except Exception as e:
                pass
        else:
            result.status = PortStatus.CLOSED

        sock.close()

    except socket.timeout:
        result.status = PortStatus.FILTERED
    except Exception as e:
        result.status = PortStatus.UNKNOWN

    return result


def scan_ports(
    host: str, ports: Optional[List[int]] = None, timeout: float = 1.0, max_workers: int = 20
) -> List[PortScanResult]:
    """
    扫描多个端口

    Args:
        host: 目标主机
        ports: 端口列表（默认扫描常用端口）
        timeout: 单端口超时
        max_workers: 并发数
    """
    if ports is None:
        ports = list(COMMON_PORTS.keys())

    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scan_port, host, port, timeout): port for port in ports}
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                pass

    # 按端口号排序
    results.sort(key=lambda x: x.port)

    return results


# ══════════════════════════════════════════════════════════════════
# DNS 覆盖测试
# ══════════════════════════════════════════════════════════════════

DEFAULT_DNS_SERVERS = [
    "8.8.8.8",  # Google
    "8.8.4.4",  # Google
    "1.1.1.1",  # Cloudflare
    "1.0.0.1",  # Cloudflare
    "114.114.114.114",  # 114 DNS
    "114.114.115.115",  # 114 DNS
    "223.5.5.5",  # 阿里 DNS
    "223.6.6.6",  # 阿里 DNS
    "119.29.29.29",  # 腾讯 DNS
    "180.76.76.76",  # 百度 DNS
]

TEST_DOMAINS = [
    "www.baidu.com",
    "www.qq.com",
    "www.taobao.com",
    "www.jd.com",
    "www.google.com",
    "github.com",
    "www.youtube.com",
]


def test_dns_resolve(server: str, domain: str, timeout: float = 2.0) -> DNSResult:
    """
    测试 DNS 解析

    Args:
        server: DNS 服务器
        domain: 域名
        timeout: 超时时间
    """
    result = DNSResult(server=server, domain=domain)

    # 使用 nslookup 或 dig
    # dig @server domain +time=2
    output = _run(
        f"dig @{server} {domain} +time={int(timeout)} +short 2>/dev/null", timeout=timeout + 1
    )

    if output:
        # 解析 IP
        lines = output.strip().splitlines()
        for line in lines:
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", line.strip()):
                result.ip = line.strip()
                result.success = True
                break

    if not result.success:
        # 备选：nslookup
        output = _run(f"nslookup {domain} {server} 2>/dev/null", timeout=timeout + 1)
        if output:
            match = re.search(r"Address:\s*(\d+\.\d+\.\d+\.\d+)", output)
            if match:
                result.ip = match.group(1)
                result.success = True

    return result


def test_dns_coverage(
    domain: str, servers: Optional[List[str]] = None, timeout: float = 2.0
) -> List[DNSResult]:
    """
    测试 DNS 覆盖（多个 DNS 服务器解析同一域名）

    Args:
        domain: 域名
        servers: DNS 服务器列表
        timeout: 超时时间
    """
    if servers is None:
        servers = DEFAULT_DNS_SERVERS

    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(test_dns_resolve, server, domain, timeout): server for server in servers
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                pass

    return results


def test_all_dns_coverage(
    domains: Optional[List[str]] = None, servers: Optional[List[str]] = None
) -> Dict[str, List[DNSResult]]:
    """
    测试所有域名的 DNS 覆盖

    Args:
        domains: 域名列表
        servers: DNS 服务器列表
    """
    if domains is None:
        domains = TEST_DOMAINS

    results = {}

    for domain in domains:
        results[domain] = test_dns_coverage(domain, servers)

    return results


# ══════════════════════════════════════════════════════════════════
# 网卡健康检测
# ══════════════════════════════════════════════════════════════════


def get_interface_health(name: str) -> InterfaceHealth:
    """
    获取单个网卡健康信息

    Args:
        name: 网卡名称
    """
    iface = InterfaceHealth(name=name)

    # IP 地址
    ip_out = _run(
        f"ip -4 addr show {name} 2>/dev/null | grep inet | awk '{{print $2}}' | cut -d/ -f1"
    )
    if ip_out:
        iface.ip = ip_out

    # MAC 地址
    mac_path = f"/sys/class/net/{name}/address"
    if os.path.exists(mac_path):
        try:
            iface.mac = open(mac_path).read().strip().upper()
        except Exception as e:
            pass

    # 速率
    speed_path = f"/sys/class/net/{name}/speed"
    if os.path.exists(speed_path):
        try:
            speed = int(open(speed_path).read().strip())
            iface.speed_mbps = abs(speed)  # -1 表示未知
        except Exception as e:
            pass

    # 双工
    duplex_path = f"/sys/class/net/{name}/duplex"
    if os.path.exists(duplex_path):
        try:
            iface.duplex = open(duplex_path).read().strip()
        except Exception as e:
            pass

    # 链路状态
    operstate_path = f"/sys/class/net/{name}/operstate"
    if os.path.exists(operstate_path):
        try:
            state = open(operstate_path).read().strip()
            iface.link_state = LinkState.UP if state == "up" else LinkState.DOWN
        except Exception as e:
            pass

    # 统计信息
    stats_base = f"/sys/class/net/{name}/statistics"
    if os.path.exists(stats_base):
        try:
            iface.rx_bytes = int(open(f"{stats_base}/rx_bytes").read().strip())
            iface.tx_bytes = int(open(f"{stats_base}/tx_bytes").read().strip())
            iface.rx_packets = int(open(f"{stats_base}/rx_packets").read().strip())
            iface.tx_packets = int(open(f"{stats_base}/tx_packets").read().strip())
            iface.rx_errors = int(open(f"{stats_base}/rx_errors").read().strip())
            iface.tx_errors = int(open(f"{stats_base}/tx_errors").read().strip())
            iface.rx_dropped = int(open(f"{stats_base}/rx_dropped").read().strip())
            iface.tx_dropped = int(open(f"{stats_base}/tx_dropped").read().strip())
        except Exception as e:
            pass

    # 无线信息
    wireless_path = f"/sys/class/net/{name}/wireless"
    if os.path.exists(wireless_path):
        iface.is_wireless = True

        # SSID
        ssid_out = _run(f"iw dev {name} link 2>/dev/null | grep SSID | awk '{{print $2}}'")
        if ssid_out:
            iface.wifi_ssid = ssid_out

        # 信号强度
        signal_out = _run(f"iw dev {name} link 2>/dev/null | grep 'signal:' | awk '{{print $2}}'")
        if signal_out:
            try:
                iface.wifi_signal_dbm = int(signal_out)
            except Exception as e:
                pass

    return iface


def get_all_interfaces() -> List[InterfaceHealth]:
    """获取所有网卡健康信息"""
    interfaces = []

    # 列出所有网卡
    out = _run("ls /sys/class/net")
    if not out:
        return interfaces

    for name in out.splitlines():
        name = name.strip()
        if name and name != "lo":
            iface = get_interface_health(name)
            interfaces.append(iface)

    return interfaces


# ══════════════════════════════════════════════════════════════════
# 综合检测
# ══════════════════════════════════════════════════════════════════


def check_network_health(
    do_bandwidth: bool = False,
    scan_ports: Optional[List[int]] = None,
    test_dns: bool = True,
    target_host: str = "localhost",
) -> NetworkHealthReport:
    """
    主入口：网络健康检测

    Args:
        do_bandwidth: 是否测试带宽（较慢）
        scan_ports: 要扫描的端口列表（None 则不扫描）
        test_dns: 是否测试 DNS 覆盖
        target_host: 端口扫描目标主机
    """
    report = NetworkHealthReport(timestamp=datetime.now().isoformat())

    # 1. 网卡信息
    report.interfaces = get_all_interfaces()

    # 2. 网关
    gw = _run("ip route | grep default | awk '{print $3}' | head -1")
    if gw:
        report.gateway = gw
        ping_out = _run(f"ping -c 1 -W 2 {gw}", timeout=4)
        report.gateway_reachable = "bytes from" in ping_out or "1 received" in ping_out

    # 3. 互联网连通
    ping_out = _run("ping -c 1 -W 3 8.8.8.8 2>/dev/null", timeout=5)
    report.internet_reachable = "bytes from" in ping_out or "1 received" in ping_out

    # 4. 带宽测试
    if do_bandwidth:
        report.bandwidth = test_bandwidth_speedtest()
        if report.bandwidth.error:
            # 备选：简单测试
            report.bandwidth = test_bandwidth_simple()

    # 5. 端口扫描
    if scan_ports:
        report.port_scan = scan_ports(target_host, scan_ports)

    # 6. DNS 覆盖
    if test_dns:
        # 只测试一个域名
        report.dns_results = test_dns_coverage("www.baidu.com")

    # 7. 计算健康分数
    report.health_score = calculate_network_health_score(report)

    # 8. 收集问题
    for iface in report.interfaces:
        if iface.link_state == LinkState.DOWN:
            report.warnings.append(f"网卡 {iface.name} 链路断开")
        if iface.rx_errors > 100 or iface.tx_errors > 100:
            report.warnings.append(
                f"网卡 {iface.name} 错误计数过高（rx={iface.rx_errors}, tx={iface.tx_errors}）"
            )
        if iface.is_wireless and iface.wifi_signal_dbm < -70:
            report.warnings.append(f"无线网卡 {iface.name} 信号弱（{iface.wifi_signal_dbm} dBm）")

    if not report.gateway_reachable:
        report.issues.append("网关不可达")
    if not report.internet_reachable:
        report.issues.append("互联网不可达")

    # 9. 综合判断
    report.ok = len(report.issues) == 0 and report.internet_reachable

    return report


def calculate_network_health_score(report: NetworkHealthReport) -> int:
    """
    计算网络健康分数（0-100）

    评分规则：
    - 基础分 100
    - 网关不可达: -20
    - 互联网不可达: -30
    - 网卡断开: -10 每个
    - 网卡错误 > 100: -5 每个
    - 无线信号 < -70: -5 每个
    - DNS 失败: -5 每个
    """
    score = 100

    if not report.gateway_reachable:
        score -= 20
    if not report.internet_reachable:
        score -= 30

    for iface in report.interfaces:
        if iface.link_state == LinkState.DOWN:
            score -= 10
        if iface.rx_errors > 100 or iface.tx_errors > 100:
            score -= 5
        if iface.is_wireless and iface.wifi_signal_dbm < -70:
            score -= 5

    # DNS 失败
    dns_failed = sum(1 for d in report.dns_results if not d.success)
    score -= dns_failed * 5

    return max(0, min(100, score))


def format_report(report: NetworkHealthReport, verbose: bool = False) -> str:
    """格式化报告为文本"""
    lines = []

    # 标题
    lines.append("=" * 60)
    lines.append("网络健康报告")
    lines.append(f"时间: {report.timestamp}")
    lines.append(f"健康分数: {report.health_score}/100")
    lines.append("=" * 60)
    lines.append("")

    # 网卡信息
    if report.interfaces:
        lines.append("🌐 网卡状态:")
        for iface in report.interfaces:
            status_icon = "✅" if iface.link_state == LinkState.UP else "❌"
            speed_str = f", {iface.speed_mbps} Mbps" if iface.speed_mbps > 0 else ""
            lines.append(f"  {status_icon} {iface.name}: {iface.ip}{speed_str}")

            if iface.is_wireless:
                lines.append(f"     WiFi: {iface.wifi_ssid}, 信号: {iface.wifi_signal_dbm} dBm")

            if verbose and (iface.rx_errors > 0 or iface.tx_errors > 0):
                lines.append(f"     错误: rx={iface.rx_errors}, tx={iface.tx_errors}")
        lines.append("")

    # 网关和互联网
    lines.append("🔗 连通性:")
    gw_icon = "✅" if report.gateway_reachable else "❌"
    lines.append(f"  {gw_icon} 网关: {report.gateway or '未知'}")
    net_icon = "✅" if report.internet_reachable else "❌"
    lines.append(f"  {net_icon} 互联网")
    lines.append("")

    # 带宽
    if report.bandwidth.download_mbps > 0:
        lines.append("📊 带宽:")
        lines.append(f"  下载: {report.bandwidth.download_mbps:.1f} Mbps")
        lines.append(f"  上传: {report.bandwidth.upload_mbps:.1f} Mbps")
        lines.append(f"  延迟: {report.bandwidth.latency_ms:.1f} ms")
        if report.bandwidth.packet_loss > 0:
            lines.append(f"  丢包: {report.bandwidth.packet_loss:.1f}%")
        lines.append("")

    # 端口扫描
    if report.port_scan:
        lines.append("🚪 端口扫描:")
        for p in report.port_scan:
            status_icon = "✅" if p.status == PortStatus.OPEN else "❌"
            service_str = f" ({p.service})" if p.service else ""
            lines.append(f"  {status_icon} {p.port}{service_str}: {p.status.value}")
        lines.append("")

    # DNS
    if report.dns_results:
        lines.append("🔍 DNS 解析:")
        for d in report.dns_results:
            status_icon = "✅" if d.success else "❌"
            lines.append(f"  {status_icon} {d.server}: {d.ip or '失败'}")
        lines.append("")

    # 问题
    if report.issues:
        lines.append("❌ 严重问题:")
        for issue in report.issues:
            lines.append(f"  - {issue}")
        lines.append("")

    if report.warnings:
        lines.append("⚠️ 警告:")
        for warning in report.warnings:
            lines.append(f"  - {warning}")
        lines.append("")

    # 总结
    if report.ok:
        lines.append("✅ 网络健康状态良好")
    else:
        lines.append("❌ 网络需要维护")

    return "\n".join(lines)
