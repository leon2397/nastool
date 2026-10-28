"""
core/platform_detect.py — NAS 平台识别

判断「这台机器是什么 NAS」，是通用化最核心的一层：
  - 成品 NAS：Synology DSM / QNAP QTS / TrueNAS / unRAID / 绿联·极空间等
  - 自建 NAS 系统：OpenMediaVault / CasaOS / 飞牛 fnOS / Proxmox / OpenWrt
  - 通用 Linux 发行版 / Windows / macOS
  - 是否容器（Docker / LXC）—— 容器内很多检测项不可用，需要提前说明

识别依据只用「文件特征 + os-release」，不执行任何厂商私有命令，保证只读、无副作用。
"""
import os
import platform
from dataclasses import dataclass, field
from typing import List

from .util import IS_LINUX, IS_WINDOWS, IS_DARWIN, read_file, path_exists, run


# ── 平台类型 ────────────────────────────────────────────────
class PlatformKind:
    NAS_APPLIANCE = "nas_appliance"   # 成品 NAS（群晖/威联通/TrueNAS 等）
    NAS_SOFTWARE = "nas_software"     # 装在通用硬件上的 NAS 系统
    LINUX = "linux"                   # 通用 Linux
    WINDOWS = "windows"
    MACOS = "macos"
    UNKNOWN = "unknown"


@dataclass
class PlatformFacts:
    kind: str = PlatformKind.UNKNOWN
    vendor: str = ""            # 群晖 / 威联通 / TrueNAS / 飞牛 ...
    product: str = ""           # DSM / QTS / SCALE ...
    version: str = ""           # 系统版本号
    pretty_name: str = ""       # 完整系统名（/etc/os-release PRETTY_NAME）
    distro_id: str = ""         # debian / ubuntu / synology-dsm ...
    kernel: str = ""
    arch: str = ""
    hostname: str = ""
    in_container: bool = False
    container_type: str = ""    # docker / lxc / podman
    is_root: bool = False
    data_roots: List[str] = field(default_factory=list)   # 探测到的 NAS 数据根目录
    facts: dict = field(default_factory=dict)             # 其他识别到的特征

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "vendor": self.vendor,
            "product": self.product,
            "version": self.version,
            "pretty_name": self.pretty_name,
            "distro_id": self.distro_id,
            "kernel": self.kernel,
            "arch": self.arch,
            "hostname": self.hostname,
            "model": self.facts.get("model", ""),
            "in_container": self.in_container,
            "container_type": self.container_type,
            "is_root": self.is_root,
            "data_roots": list(self.data_roots),
            "facts": dict(self.facts),
        }


def _os_release() -> dict:
    """解析 /etc/os-release；不依赖 distro 包。"""
    info = {}
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        if not os.path.isfile(path):
            continue
        for line in read_file(path).splitlines():
            if "=" not in line or line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            info[k.strip()] = v.strip().strip('"').strip("'")
        break
    return info


def _detect_container() -> tuple:
    """判断是否运行在容器内。"""
    if path_exists("/.dockerenv") or path_exists("/run/.containerenv"):
        return True, "docker"
    cgroup = read_file("/proc/1/cgroup")
    if "docker" in cgroup:
        return True, "docker"
    if "lxc" in cgroup or path_exists("/dev/lxc"):
        return True, "lxc"
    if "kubepods" in cgroup:
        return True, "kubernetes"
    return False, ""


def _probe_appliance() -> tuple:
    """
    成品 NAS 特征探测。
    返回 (kind, vendor, product, version, facts)
    """
    facts = {}

    # ── Synology DSM ────────────────────────────────────────
    syno_ver = "/etc.defaults/VERSION"
    if path_exists("/usr/syno") or path_exists(syno_ver):
        ver = {}
        for line in read_file(syno_ver).splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                ver[k.strip()] = v.strip().strip('"')
        version = ver.get("productversion", "")
        if ver.get("buildnumber"):
            version = f"{version}-{ver['buildnumber']}"
        facts["dsm_major"] = ver.get("majorversion", "")
        # 群晖型号写在 /proc/sys/kernel/syno_hw_version
        model = read_file("/proc/sys/kernel/syno_hw_version")
        if model:
            facts["model"] = model
        return (PlatformKind.NAS_APPLIANCE, "Synology", "DSM", version, facts)

    # ── QNAP QTS ───────────────────────────────────────────
    if path_exists("/etc/config/uLinux.conf") or path_exists("/sbin/qpkg_cli"):
        conf = read_file("/etc/config/uLinux.conf")
        version = ""
        model = ""
        for line in conf.splitlines():
            s = line.strip()
            if s.startswith("Version =") or s.startswith("Version="):
                version = s.split("=", 1)[1].strip()
            elif s.startswith("Number =") or s.startswith("Number="):
                model = s.split("=", 1)[1].strip()
        facts["model"] = model
        return (PlatformKind.NAS_APPLIANCE, "QNAP", "QTS", version, facts)

    # ── TrueNAS (SCALE / CORE) ─────────────────────────────
    if path_exists("/etc/version") and path_exists("/usr/bin/midclt"):
        return (PlatformKind.NAS_APPLIANCE, "TrueNAS", "SCALE",
                read_file("/etc/version"), facts)
    if os_release_id() in ("truenas-scale", "truenas"):
        return (PlatformKind.NAS_APPLIANCE, "TrueNAS", "SCALE",
                read_file("/etc/version"), facts)

    # ── unRAID ─────────────────────────────────────────────
    if path_exists("/etc/unraid-version"):
        ver = read_file("/etc/unraid-version").split("=", 1)[-1].strip().strip('"')
        return (PlatformKind.NAS_APPLIANCE, "Lime Technology", "unRAID", ver, facts)

    # ── 铁威马 TOS ─────────────────────────────────────────
    if path_exists("/etc/tos/version") or path_exists("/usr/bin/tos-version"):
        return (PlatformKind.NAS_APPLIANCE, "TerraMaster", "TOS",
                read_file("/etc/tos/version"), facts)

    # ── 绿联 UGOS ──────────────────────────────────────────
    if path_exists("/usr/ugos") or path_exists("/etc/ugos-release"):
        return (PlatformKind.NAS_APPLIANCE, "UGREEN", "UGOS",
                read_file("/etc/ugos-release"), facts)

    return ("", "", "", "", facts)


def _probe_software() -> tuple:
    """装在通用硬件上的 NAS 系统。返回 (kind, vendor, product, version, facts)"""
    facts = {}

    # ── 飞牛 fnOS ──────────────────────────────────────────
    if path_exists("/usr/trim") or path_exists("/etc/trim-release"):
        return (PlatformKind.NAS_SOFTWARE, "fnOS", "fnOS",
                read_file("/etc/trim-release"), facts)

    # ── OpenMediaVault ─────────────────────────────────────
    if path_exists("/etc/openmediavault/config.xml") or path_exists("/usr/sbin/omv-engined"):
        return (PlatformKind.NAS_SOFTWARE, "OpenMediaVault", "OMV",
                read_file("/etc/openmediavault-release"), facts)

    # ── CasaOS ─────────────────────────────────────────────
    if path_exists("/usr/lib/casaos") or path_exists("/var/lib/casaos"):
        return (PlatformKind.NAS_SOFTWARE, "IceWhale", "CasaOS",
                read_file("/etc/casaos-release"), facts)

    # ── Proxmox VE（常被当 NAS 宿主）────────────────────────
    if path_exists("/etc/pve") and path_exists("/usr/bin/pveversion"):
        return (PlatformKind.NAS_SOFTWARE, "Proxmox", "VE",
                run("pveversion --verbose 2>/dev/null | head -1"), facts)

    # ── OpenWrt / iStoreOS（常带 NAS 插件）──────────────────
    if path_exists("/etc/openwrt_release"):
        rel = read_file("/etc/openwrt_release")
        version = ""
        for line in rel.splitlines():
            if line.startswith("DISTRIB_RELEASE"):
                version = line.split("=", 1)[1].strip().strip("'")
        return (PlatformKind.NAS_SOFTWARE, "OpenWrt", "OpenWrt", version, facts)

    return ("", "", "", "", facts)


def os_release_id() -> str:
    return _os_release().get("ID", "").lower()


def _find_data_roots() -> List[str]:
    """找数据盘根目录：把容量最大的几个挂载点作为 NAS 数据根。"""
    roots = []
    try:
        for line in run("df -kP 2>/dev/null | tail -n +2").splitlines():
            parts = line.split()
            if len(parts) < 6:
                continue
            mount = parts[-1]
            if mount == "/" or not os.path.isdir(mount):
                continue
            if mount.startswith(("/proc", "/sys", "/dev", "/run", "/snap", "/boot")):
                continue
            try:
                free_kb = int(parts[3])
            except ValueError:
                continue
            roots.append((free_kb, mount))
    except Exception:  # noqa: BLE001
        pass
    roots.sort(reverse=True)
    return [m for _, m in roots[:5]]


def _is_admin() -> bool:
    """是否具备管理员/root 权限（SMART、RAID 等检测依赖它）。"""
    if IS_WINDOWS:
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:  # noqa: BLE001
            return False
    return hasattr(os, "geteuid") and os.geteuid() == 0


def detect_platform() -> PlatformFacts:
    """主入口：识别当前设备属于哪类 NAS 平台。"""
    rep = PlatformFacts()
    rep.arch = platform.machine()
    rep.kernel = platform.release()
    rep.hostname = platform.node()

    rel = _os_release()
    rep.pretty_name = rel.get("PRETTY_NAME", "") or platform.platform()
    rep.distro_id = rel.get("ID", "")

    rep.in_container, rep.container_type = _detect_container()
    rep.is_root = _is_admin()

    if IS_WINDOWS:
        rep.kind = PlatformKind.WINDOWS
        rep.vendor = "Microsoft"
        rep.product = "Windows"
        rep.version = platform.version()
        return rep
    if IS_DARWIN:
        rep.kind = PlatformKind.MACOS
        rep.vendor = "Apple"
        rep.product = "macOS"
        rep.version = platform.mac_ver()[0]
        return rep

    if not IS_LINUX:
        rep.kind = PlatformKind.UNKNOWN
        return rep

    # 1) 先看成品 NAS
    kind, vendor, product, version, facts = _probe_appliance()

    # 2) 再看 NAS 系统
    if not kind:
        kind, vendor, product, version, facts = _probe_software()

    # 3) 都没有 → 通用 Linux
    if not kind:
        kind = PlatformKind.LINUX
        vendor = rel.get("NAME", "Linux")
        product = rel.get("ID", "") or "linux"
        version = rel.get("VERSION_ID", "")
        facts["derivative"] = rel.get("ID_LIKE", "")

    rep.kind = kind
    rep.vendor = vendor
    rep.product = product
    rep.version = version
    rep.facts = facts

    # 型号信息：优先 NAS 私有字段，否则 DMI
    if not rep.facts.get("model"):
        for path in ("/sys/class/dmi/id/product_name", "/sys/firmware/devicetree/base/model"):
            model = read_file(path)
            if model:
                rep.facts["model"] = model
                break

    rep.data_roots = _find_data_roots()

    return rep


def platform_is_nas(rep: PlatformFacts) -> bool:
    """是否是「NAS 形态」（成品机或 NAS 系统），用于报告措辞。"""
    return rep.kind in (PlatformKind.NAS_APPLIANCE, PlatformKind.NAS_SOFTWARE)
