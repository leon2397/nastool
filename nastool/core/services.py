"""
core/services.py — 运行中的 NAS 服务与端口探测

解决的问题：用户拿到一台 NAS，第一件事是「它现在跑了什么」。
本模块只做只读探测：
  - 本地监听端口（ss / netstat）
  - 常见 NAS 服务对照（SMB / NFS / SSH / Web / Docker / 媒体服务）
  - Docker 容器清单（如果可访问 docker）
  - 关键服务进程是否存在

判定口径：服务缺失不算故障（一台裸 NAS 只跑 SMB 完全正常），
         只有「端口被监听但进程不可识别」才提示。
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List

from .util import IS_WINDOWS, have, run


# 端口 → (服务名, 分类, 说明)
KNOWN_SERVICES: Dict[int, tuple] = {
    135:   ("Windows RPC",  "系统服务", "Windows RPC 端点映射"),
    445:   ("SMB",        "文件共享", "Windows/SMB 文件共享"),
    139:   ("SMB (NetBIOS)", "文件共享", "旧版 SMB 会话服务"),
    2049:  ("NFS",        "文件共享", "网络文件系统"),
    111:   ("rpcbind",    "文件共享", "NFS 依赖的 RPC 端口映射"),
    873:   ("rsync",      "文件共享", "rsync 同步服务"),
    21:    ("FTP",        "文件共享", "FTP 服务"),
    22:    ("SSH",        "远程管理", "SSH 远程登录"),
    23:    ("Telnet",     "远程管理", "Telnet（明文，不建议开启）"),
    80:    ("HTTP",       "管理界面", "Web 管理/门户"),
    443:   ("HTTPS",      "管理界面", "Web 管理（加密）"),
    5000:  ("DSM / 通用 Web", "管理界面", "群晖 DSM 或应用 Web 端口"),
    5001:  ("DSM HTTPS",  "管理界面", "群晖 DSM 加密端口"),
    8080:  ("HTTP 备用",   "管理界面", "QNAP QTS / 各类 Web 面板常用"),
    8000:  ("自建应用",     "管理界面", "常见开发/自建服务端口"),
    3000:  ("Web 应用",    "管理界面", "CasaOS / 各类面板"),
    2375:  ("Docker API", "容器", "Docker 未加密 API（公网暴露极危险）"),
    2376:  ("Docker API (TLS)", "容器", "Docker 加密 API"),
    32400: ("Plex",       "媒体服务", "Plex Media Server"),
    8096:  ("Jellyfin",   "媒体服务", "Jellyfin 媒体服务器"),
    8920:  ("Jellyfin HTTPS", "媒体服务", "Jellyfin 加密端口"),
    8123:  ("Home Assistant", "智能家居", "Home Assistant"),
    9091:  ("Transmission", "下载", "Transmission BT"),
    51413: ("Transmission (BT)", "下载", "Transmission 传输端口"),
    8081:  ("qBittorrent / Nginx", "下载", "qBittorrent WebUI 常用端口"),
    3306:  ("MySQL",      "数据库", "MySQL / MariaDB"),
    5432:  ("PostgreSQL", "数据库", "PostgreSQL"),
    6379:  ("Redis",      "数据库", "Redis 缓存"),
    9000:  ("Portainer / MinIO", "容器", "容器管理或对象存储"),
    199:   ("SNMP",       "监控", "SNMP 设备监控"),
    161:   ("SNMP",       "监控", "SNMP 设备监控（UDP）"),
}

# 关键进程 → 服务名
KNOWN_PROCESSES: Dict[str, str] = {
    "smbd": "SMB", "nmbd": "SMB",
    "nfsd": "NFS", "rpc.mountd": "NFS",
    "sshd": "SSH",
    "dockerd": "Docker", "containerd": "Docker",
    "nginx": "Web 服务器", "httpd": "Web 服务器", "caddy": "Web 服务器",
    "smartd": "SMART 监控",
    "mdadm": "软 RAID 监控",
    "synologand": "群晖系统", "synoscgi": "群晖系统",
    "jellyfin": "Jellyfin", "emby-server": "Emby", "Plex Media Server": "Plex",
    "transmission-daemon": "Transmission",
    "qbittorrent-nox": "qBittorrent",
}


@dataclass
class ServiceItem:
    port: int = 0
    name: str = ""
    category: str = ""
    note: str = ""
    listening: bool = True
    pid: str = ""
    process: str = ""
    bind_address: str = ""


@dataclass
class DockerContainer:
    name: str = ""
    image: str = ""
    status: str = ""
    ports: str = ""


@dataclass
class ServicesReport:
    items: List[ServiceItem] = field(default_factory=list)
    processes: List[str] = field(default_factory=list)
    containers: List[DockerContainer] = field(default_factory=list)
    docker_available: bool = False
    total_listening: int = 0
    notes: List[str] = field(default_factory=list)      # 仅提示，不算问题
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    ok: bool = True

    def has(self, category: str) -> bool:
        return any(i.category == category for i in self.items)

    def find(self, name: str) -> List[ServiceItem]:
        return [i for i in self.items if name.lower() in i.name.lower()]


def _get_listening_ports() -> List[tuple]:
    """
    返回 [(port, bind_address, process, pid)]。
    Linux: ss -tlnp；无 ss 时退回 netstat；Windows: netstat -ano。
    """
    rows: List[tuple] = []

    if IS_WINDOWS:
        out = run("netstat -ano -p tcp", timeout=15)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 5 or not parts[0].upper().startswith("TCP"):
                continue
            local, state, pid = parts[1], parts[3], parts[4]
            if state.upper() != "LISTENING":
                continue
            addr, _, port_s = local.rpartition(":")
            if port_s.isdigit():
                rows.append((int(port_s), addr, "", pid))
        return rows

    if have("ss"):
        out = run("ss -tlnp 2>/dev/null", timeout=8)
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 4:
                continue
            local = parts[3]
            addr, _, port_s = local.rpartition(":")
            if not port_s.isdigit():
                continue
            process, pid = "", ""
            m = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
            if m:
                process, pid = m.group(1), m.group(2)
            rows.append((int(port_s), addr, process, pid))
        return rows

    if have("netstat"):
        out = run("netstat -tlnp 2>/dev/null", timeout=8)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 6 or "LISTEN" not in line:
                continue
            local = parts[3]
            addr, _, port_s = local.rpartition(":")
            if not port_s.isdigit():
                continue
            proc = parts[6].split("/")[-1] if len(parts) > 6 else ""
            rows.append((int(port_s), addr, proc, ""))
    return rows


def _list_processes() -> List[str]:
    """当前进程名列表（只用于判断服务是否在跑）。"""
    out = run("ps -eo comm= 2>/dev/null", timeout=8)
    if not out:
        return []
    return [p.strip() for p in out.splitlines() if p.strip()]


def _docker_containers() -> tuple:
    """docker ps 容器清单；不可用时返回 (False, [])。"""
    if not have("docker"):
        return False, []
    out = run('docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}" 2>/dev/null', timeout=15)
    if not out:
        # docker 装了但没权限（用户不在 docker 组）也会空
        if "permission denied" in run("docker ps 2>&1 | head -1", timeout=10).lower():
            return False, []
        return False, []
    containers = []
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        containers.append(DockerContainer(
            name=parts[0], image=parts[1], status=parts[2],
            ports=parts[3] if len(parts) > 3 else "",
        ))
    return True, containers


def _is_ephemeral(port: int) -> bool:
    """Windows/Linux 临时端口段：数量多、无诊断价值，报告里只计数不逐条列。"""
    return 49152 <= port <= 65535


def detect_services() -> ServicesReport:
    """主入口：监听端口 + 已知服务 + 进程 + Docker。"""
    rep = ServicesReport()

    rows = _get_listening_ports()
    rep.total_listening = len(rows)

    seen_ports = set()
    ephemeral_count = 0
    for port, addr, process, pid in rows:
        if port in seen_ports:
            continue
        seen_ports.add(port)
        if port not in KNOWN_SERVICES and _is_ephemeral(port):
            ephemeral_count += 1
            continue
        name, category, note = KNOWN_SERVICES.get(port, ("未知服务", "其他", ""))
        rep.items.append(ServiceItem(
            port=port, name=name, category=category, note=note,
            listening=True, pid=pid, process=process, bind_address=addr,
        ))

    if ephemeral_count:
        rep.notes.append(
            f"另有 {ephemeral_count} 个临时端口（49152-65535）在监听，多为客户端出站连接，无需处理"
        )

    # 按端口排序，未识别的排后面，报告更好读
    rep.items.sort(key=lambda i: (i.category == "其他", i.port))

    # 进程
    procs = _list_processes()
    rep.processes = sorted({KNOWN_PROCESSES[p] for p in procs if p in KNOWN_PROCESSES})
    if not procs:
        rep.notes.append("无法读取进程列表（权限受限），服务判定仅基于端口")

    # Docker
    rep.docker_available, rep.containers = _docker_containers()

    # 风险提示
    if any(i.port == 23 for i in rep.items):
        rep.warnings.append("Telnet(23) 正在监听：明文传输，建议关闭")
    if any(i.port == 2375 for i in rep.items):
        rep.warnings.append("Docker API(2375) 未加密监听：一旦对外暴露等于交出 root")
    for i in rep.items:
        if i.bind_address in ("0.0.0.0", "*", "::", "[::]") and i.port in (445, 2049, 23, 2375, 3306, 6379):
            rep.warnings.append(f"{i.name}({i.port}) 监听所有地址，请确认已做访问控制")

    # 服务属于「信息项」，不参与失败判定
    rep.ok = True
    return rep
