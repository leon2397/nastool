"""
core/network.py — 网络接口 / 链路速率 / 连通性 / 对端可达性

通用化要点：
  - 不再是「NAS 后端连通性」，而是任意「对端目标」列表（host:port），
    例如管理后台、SMB/NFS 客户端、备份服务器
  - 判断标准按 NAS 常识：只要有网卡拿到 IP 就算基本可用；
    网关/互联网不可达只算告警（内网 NAS 很正常）
  - ip / ifconfig / netstat 都可能缺，逐级降级
"""
import os
import socket
import time
from dataclasses import dataclass, field
from typing import List, Optional

from .util import IS_LINUX, IS_WINDOWS, have, read_file, run, run_ps


@dataclass
class NetworkInterface:
    name: str = ""
    ip: str = ""
    netmask: str = ""
    mac: str = ""
    speed_mbps: int = 0        # 0 = 未知
    duplex: str = ""           # full / half / ""
    up: bool = False
    is_wireless: bool = False
    mtu: int = 0

    def has_usable_ip(self) -> bool:
        """169.254.x.x 是链路本地地址（等于没拿到 DHCP），不能算可用。"""
        return bool(self.ip) and not self.ip.startswith(("127.", "169.254."))


@dataclass
class ConnectivityTest:
    host: str = ""
    port: int = 0
    label: str = ""
    reachable: bool = False
    rtt_ms: float = 0.0
    error: str = ""


@dataclass
class NetworkReport:
    interfaces: List[NetworkInterface] = field(default_factory=list)
    dns_ok: bool = False
    dns_server: str = ""
    gateway: str = ""
    gateway_reachable: bool = False
    internet_reachable: bool = False
    peers: List[ConnectivityTest] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)      # 仅提示，不算问题
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    ok: bool = False

    def best_ip(self) -> str:
        """第一个拿到 IPv4 的非回环接口 IP。"""
        for iface in self.interfaces:
            if iface.up and iface.ip and not iface.ip.startswith("127."):
                return iface.ip
        return "未知"

    def worst_link_speed(self) -> int:
        """最慢的活动网卡速率（0 表示全部未知）。"""
        speeds = [i.speed_mbps for i in self.interfaces if i.up and i.speed_mbps > 0]
        return min(speeds) if speeds else 0


def _parse_ip_br(output: str) -> List[NetworkInterface]:
    """解析 `ip -br addr`（Debian/Ubuntu/群晖等常见）。"""
    result = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name = parts[0].rstrip("@")
        if name in ("lo",) or name.startswith(("docker", "veth", "br-", "virbr", "tun", "tap")):
            continue
        iface = NetworkInterface(name=name)
        iface.up = any(p.upper() == "UP" for p in parts[1:2]) or "UP" in line[:40]
        for p in parts:
            if "/" in p and ":" not in p:
                ip_part, _, cidr = p.partition("/")
                if _is_ipv4(ip_part):
                    iface.ip = ip_part
                    iface.netmask = _cidr_to_netmask(cidr)
                    break
        result.append(iface)
    return result


def _parse_ip_addr(output: str) -> List[NetworkInterface]:
    """解析完整 `ip addr` 输出（当 -br 不支持时）。"""
    result = []
    current: Optional[NetworkInterface] = None
    for line in output.splitlines():
        if line and not line[0].isspace():
            # 2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 ...
            parts = line.split()
            if len(parts) < 2:
                current = None
                continue
            name = parts[1].rstrip(":@")
            if name == "lo" or name.startswith(("docker", "veth", "br-", "virbr")):
                current = None
                continue
            current = NetworkInterface(name=name)
            current.up = " UP " in line or ",UP," in line
            for tok in parts:
                if tok.startswith("mtu"):
                    try:
                        current.mtu = int(parts[parts.index(tok) + 1])
                    except (ValueError, IndexError):
                        pass
            result.append(current)
        elif current and "inet " in line:
            parts = line.split()
            if len(parts) >= 2 and "/" in parts[1]:
                ip_part, _, cidr = parts[1].partition("/")
                if _is_ipv4(ip_part):
                    current.ip = ip_part
                    current.netmask = _cidr_to_netmask(cidr)
    return result


def _parse_windows_adapters() -> List[NetworkInterface]:
    """Windows：PowerShell 取已连接的 IPv4 网卡。"""
    out = run_ps('Get-NetIPConfiguration | '
                 'Where-Object {$_.IPv4Address} | ForEach-Object { '
                 "$_.InterfaceAlias + '|' + $_.IPv4Address.IPAddress + '|' + "
                 '$_.IPv4Address.PrefixLength }', timeout=25)
    result = []
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        iface = NetworkInterface(name=parts[0].strip(), up=True)
        iface.ip = parts[1].strip()
        try:
            iface.netmask = _cidr_to_netmask(parts[2].strip())
        except Exception:  # noqa: BLE001
            pass
        result.append(iface)
    return result


def get_interfaces() -> List[NetworkInterface]:
    """读取所有物理/虚拟网卡。"""
    if IS_WINDOWS:
        return _parse_windows_adapters()

    interfaces: List[NetworkInterface] = []
    if have("ip"):
        out = run("ip -br addr 2>/dev/null", timeout=5)
        if out:
            interfaces = _parse_ip_br(out)
        else:
            interfaces = _parse_ip_addr(run("ip addr 2>/dev/null", timeout=5))
    elif have("ifconfig"):
        interfaces = _parse_ifconfig(run("ifconfig -a 2>/dev/null", timeout=5))

    # 补充 MAC / 速率 / 双工 / 无线
    for iface in interfaces:
        if IS_LINUX:
            mac = read_file(f"/sys/class/net/{iface.name}/address")
            if mac:
                iface.mac = mac.upper()
            try:
                spd = int(read_file(f"/sys/class/net/{iface.name}/speed", "0") or 0)
                iface.speed_mbps = abs(spd)
            except ValueError:
                pass
            iface.duplex = read_file(f"/sys/class/net/{iface.name}/duplex")
            iface.is_wireless = os.path.exists(f"/sys/class/net/{iface.name}/wireless")
            if not iface.mtu:
                try:
                    iface.mtu = int(read_file(f"/sys/class/net/{iface.name}/mtu", "0") or 0)
                except ValueError:
                    pass

    return interfaces


def _parse_ifconfig(output: str) -> List[NetworkInterface]:
    """老系统 / macOS 的 ifconfig 解析（尽力而为）。"""
    result = []
    current = None
    for line in output.splitlines():
        if line and not line[0].isspace() and ":" in line:
            name = line.split(":")[0]
            if name == "lo" or name.startswith(("docker", "veth", "br-")):
                current = None
                continue
            current = NetworkInterface(name=name, up=("UP" in line))
            result.append(current)
        elif current and "inet " in line:
            parts = line.split()
            for i, tok in enumerate(parts):
                if tok == "inet" and i + 1 < len(parts):
                    current.ip = parts[i + 1]
                if tok == "netmask" and i + 1 < len(parts):
                    current.netmask = parts[i + 1]
    return result


def _is_ipv4(s: str) -> bool:
    try:
        socket.inet_aton(s)
        return True
    except OSError:
        return False


def _cidr_to_netmask(cidr: str) -> str:
    try:
        bits = int(cidr)
        if not 0 <= bits <= 32:
            return ""
        mask = (0xFFFFFFFF << (32 - bits)) & 0xFFFFFFFF
        return f"{(mask >> 24) & 0xFF}.{(mask >> 16) & 0xFF}.{(mask >> 8) & 0xFF}.{mask & 0xFF}"
    except (ValueError, TypeError):
        return ""


def test_connectivity(host: str, port: int = 80, timeout: int = 3,
                      label: str = "") -> ConnectivityTest:
    """TCP 端口连通性测试。"""
    test = ConnectivityTest(host=host, port=port, label=label or f"{host}:{port}")
    start = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        test.rtt_ms = round((time.time() - start) * 1000, 1)
        test.reachable = True
        sock.close()
    except Exception as e:  # noqa: BLE001
        test.error = str(e)[:80]
    return test


def parse_peer(text: str, default_port: int = 443) -> tuple:
    """把 'host:port' / 'host' 解析成 (host, port)。支持 [ipv6]:port。"""
    text = (text or "").strip()
    if text.startswith("["):
        host, _, rest = text.partition("]")
        host = host.lstrip("[")
        port = rest.lstrip(":")
        return host, int(port) if port.isdigit() else default_port
    if text.count(":") == 1:
        host, _, port = text.partition(":")
        if port.isdigit():
            return host, int(port)
    return text, default_port


def _detect_gateway() -> str:
    if IS_WINDOWS:
        out = run_ps('(Get-NetRoute -DestinationPrefix 0.0.0.0/0 '
                     '| Select-Object -First 1).NextHop', timeout=20)
        return out.strip()
    if IS_LINUX:
        out = run("ip route 2>/dev/null | awk '/^default/ {print $3; exit}'", timeout=3)
        if out:
            return out.strip()
    out = run("route -n 2>/dev/null | awk '/^0.0.0.0/ {print $2; exit}'", timeout=3)
    return out.strip()


def _detect_dns_server() -> str:
    if IS_WINDOWS:
        out = run_ps('(Get-DnsClientServerAddress -AddressFamily IPv4 | '
                     'Where-Object {$_.ServerAddresses} | '
                     'Select-Object -First 1).ServerAddresses -join ","', timeout=20)
        servers = []
        for s in out.replace(",", " ").split():
            if s and s not in servers:
                servers.append(s)
        return ", ".join(servers)
    content = read_file("/etc/resolv.conf")
    for line in content.splitlines():
        if line.strip().startswith("nameserver"):
            parts = line.split()
            if len(parts) > 1:
                return parts[1]
    return ""


def check_network(peers: Optional[List[str]] = None,
                  do_internet_check: bool = True) -> NetworkReport:
    """
    主入口。
    peers: 需要对端探测的目标列表，形如 ["192.168.1.10:445", "nas.local:5000"]
    """
    report = NetworkReport()

    # 1. 接口
    report.interfaces = get_interfaces()

    # 2. DNS
    report.dns_server = _detect_dns_server()
    try:
        socket.gethostbyname("www.baidu.com" if IS_LINUX else "www.bing.com")
        report.dns_ok = True
    except OSError:
        report.dns_ok = False

    # 3. 网关
    report.gateway = _detect_gateway()
    if report.gateway:
        if IS_WINDOWS:
            ping = run(f"ping -n 1 -w 2000 {report.gateway}", timeout=6)
        else:
            ping = run(f"ping -c 1 -W 2 {report.gateway} 2>/dev/null", timeout=6)
        report.gateway_reachable = ("TTL=" in ping.upper() or "bytes from" in ping
                                    or "1 received" in ping or "1 packets received" in ping)

    # 4. 互联网
    if do_internet_check:
        if IS_WINDOWS:
            ping = run("ping -n 1 -w 3000 223.5.5.5", timeout=6)
        else:
            ping = run("ping -c 1 -W 3 223.5.5.5 2>/dev/null || "
                       "ping -c 1 -W 3 114.114.114.114 2>/dev/null", timeout=8)
        report.internet_reachable = ("TTL=" in ping.upper() or "bytes from" in ping
                                     or "1 received" in ping or "1 packets received" in ping)

    # 5. 对端探测
    for target in (peers or []):
        host, port = parse_peer(target)
        if host:
            report.peers.append(test_connectivity(host, port))

    # 6. 告警
    active = [i for i in report.interfaces if i.up]
    usable = [i for i in active if i.has_usable_ip()]

    if not active:
        report.errors.append("没有任何已启用的网络接口")
    elif not usable:
        report.errors.append("网络接口未获取到有效 IP（只有链路本地地址）")

    for i in active:
        if i.ip.startswith("169.254."):
            msg = f"{i.name} 只有链路本地地址（169.254.x.x），可能未接网线/DHCP 失败"
            # 已经有一条可用链路时，其他网卡的 link-local 只是提示，不算问题
            (report.notes if usable else report.warnings).append(msg)
        if i.speed_mbps and i.speed_mbps <= 100:
            rep.warnings.append(
                f"{i.name} 链路速率仅 {i.speed_mbps} Mbps（千兆及以上网卡建议检查网线/交换机）"
            )

    if active and not report.gateway_reachable:
        report.warnings.append("默认网关不可达（内网直连可忽略）")
    if report.gateway_reachable and not report.internet_reachable:
        report.warnings.append("外网不可达（NAS 常见，若无需联网可忽略）")
    if not report.dns_ok:
        report.warnings.append("DNS 解析失败")

    for peer in report.peers:
        if not peer.reachable:
            report.errors.append(f"对端不可达: {peer.label}（{peer.error}）")

    # 7. 判定：有网卡拿到有效 IP 即基本可用
    report.ok = bool(usable)
    return report
