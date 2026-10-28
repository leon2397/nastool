"""
core/storage.py — 存储检测：容量 / 可写性 / 读写速度 / RAID / SMART

设计原则：
  - 所有检测项都「尽力而为」，缺命令或缺权限只降级、不报错崩溃
  - 速度测试会真实写入临时文件，默认 50MB，--no-speed-test 可跳过
  - RAID / SMART 只在 Linux + 对应工具存在时执行
"""
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import List, Optional

from .util import IS_LINUX, IS_WINDOWS, have, read_file, run, run_ps


@dataclass
class DiskInfo:
    device: str = ""
    model: str = ""
    size_gb: float = 0.0
    fstype: str = ""
    mountpoint: str = ""
    total_gb: float = 0.0
    free_gb: float = 0.0
    use_percent: float = 0.0
    inodes_use_percent: float = 0.0
    readonly: bool = False


@dataclass
class PhysicalDisk:
    name: str = ""
    size_gb: float = 0.0
    model: str = ""
    rotational: Optional[bool] = None   # True=HDD False=SSD None=未知


@dataclass
class RaidInfo:
    name: str = ""
    kind: str = ""              # md / zfs / btrfs
    level: str = ""             # raid1 / raid5 / mirror ...
    state: str = ""             # active / degraded / rebuilding / ONLINE
    members_total: int = 0
    members_active: int = 0
    rebuild_percent: float = 0.0
    errors: List[str] = field(default_factory=list)
    healthy: bool = True


@dataclass
class SmartInfo:
    device: str = ""
    model: str = ""
    healthy: Optional[bool] = None      # None = 无法判定
    temperature_c: float = 0.0
    power_on_hours: int = 0
    reallocated_sectors: int = 0
    pending_sectors: int = 0
    uncorrectable: int = 0
    message: str = ""


@dataclass
class StorageReport:
    target_path: str = ""
    target_exists: bool = False
    is_dir: bool = False
    can_write: bool = False
    target_total_gb: float = 0.0
    target_free_gb: float = 0.0
    target_use_percent: float = 0.0
    writable_test_size_mb: int = 0
    disks: List[DiskInfo] = field(default_factory=list)
    physical_disks: List[PhysicalDisk] = field(default_factory=list)
    raids: List[RaidInfo] = field(default_factory=list)
    smart: List[SmartInfo] = field(default_factory=list)
    smart_checked: bool = False
    seq_read_mbps: float = 0.0
    seq_write_mbps: float = 0.0
    iops_4k_read: int = 0
    iops_4k_write: int = 0
    speed_test_done: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    ok: bool = False


# ── 挂载盘 ──────────────────────────────────────────────────
def _parse_df_line(line: str) -> Optional[DiskInfo]:
    """解析 `df -kP` 单行（POSIX 格式：Filesystem 1024-blocks Used Available Capacity Mounted）。"""
    parts = line.split()
    if len(parts) < 6:
        return None
    device, total_kb, _used_kb, avail_kb, cap, mount = (
        parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
    )
    try:
        total_gb = round(int(total_kb) / 1024 / 1024, 1)
        free_gb = round(int(avail_kb) / 1024 / 1024, 1)
        use_pct = float(cap.replace("%", ""))
    except (ValueError, AttributeError):
        return None
    return DiskInfo(
        device=device, mountpoint=mount, fstype="",
        total_gb=total_gb, size_gb=total_gb, free_gb=free_gb,
        use_percent=use_pct,
    )


def get_mounted_disks() -> List[DiskInfo]:
    """读取已挂载文件系统（Linux / macOS / Windows 分别适配）。"""
    disks: List[DiskInfo] = []

    if IS_WINDOWS:
        out = run_ps('Get-CimInstance Win32_LogicalDisk '
                     '| Select-Object DeviceID,FileSystem,Size,FreeSpace '
                     '| ConvertTo-Csv -NoTypeInformation', timeout=25)
        for line in out.splitlines()[1:]:
            parts = [p.strip('"') for p in line.split(",")]
            if len(parts) < 4 or not parts[2].isdigit():
                continue
            total_gb = round(int(parts[2]) / 1024 ** 3, 1)
            free_gb = round(int(parts[3]) / 1024 ** 3, 1) if parts[3].isdigit() else 0.0
            use_pct = round((total_gb - free_gb) / total_gb * 100, 1) if total_gb else 0.0
            disks.append(DiskInfo(
                device=parts[0], mountpoint=parts[0] + "\\",
                fstype=parts[1] or "NTFS",
                total_gb=total_gb, size_gb=total_gb,
                free_gb=free_gb, use_percent=use_pct,
            ))
        return disks

    # Linux / macOS：df -kP 是 POSIX 标准，列数稳定
    out = run("df -kP 2>/dev/null | tail -n +2", timeout=10)
    for line in out.splitlines():
        d = _parse_df_line(line)
        if d:
            disks.append(d)

    # fstype 补充（df -T 仅 Linux 有）
    if IS_LINUX:
        fs_map = {}
        for line in run("df -TP 2>/dev/null | tail -n +2", timeout=10).splitlines():
            parts = line.split()
            if len(parts) >= 7:
                fs_map[parts[-1]] = parts[1]
        for d in disks:
            d.fstype = fs_map.get(d.mountpoint, "?")

    # 只读检测
    if IS_LINUX:
        mounts = read_file("/proc/mounts")
        for d in disks:
            for mline in mounts.splitlines():
                mp = mline.split()
                if len(mp) >= 4 and mp[1] == d.mountpoint:
                    d.readonly = "ro" in mp[3].split(",")
                    break

    # inode 使用率（inode 耗尽同样会导致写不进去）
    if IS_LINUX:
        inode_map = {}
        for line in run("df -iP 2>/dev/null | tail -n +2", timeout=10).splitlines():
            parts = line.split()
            if len(parts) >= 6:
                try:
                    inode_map[parts[-1]] = float(parts[4].replace("%", ""))
                except ValueError:
                    pass
        for d in disks:
            d.inodes_use_percent = inode_map.get(d.mountpoint, 0.0)

    return disks


def _size_to_gb(text: str) -> float:
    """把 lsblk 的 1.8T / 500G / 200M 转成 GB。"""
    t = text.strip().upper()
    if not t:
        return 0.0
    unit = t[-1]
    num = float(t[:-1])
    if unit == "T":
        return round(num * 1024, 1)
    if unit == "G":
        return round(num, 1)
    if unit == "M":
        return round(num / 1024, 1)
    if unit == "K":
        return round(num / 1024 / 1024, 2)
    return 0.0


def get_physical_disks() -> List[PhysicalDisk]:
    """列出物理盘（lsblk），并判断 HDD/SSD。"""
    result: List[PhysicalDisk] = []
    if not IS_LINUX or not have("lsblk"):
        return result

    out = run("lsblk -dno NAME,SIZE,MODEL,ROTA,TYPE 2>/dev/null", timeout=10)
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        name, size, model, rota, dev_type = parts[0], parts[1], parts[2], parts[3], parts[4].strip()
        if dev_type != "disk":
            continue
        if name.startswith(("loop", "ram", "zram", "dm-", "md", "sr")):
            continue
        try:
            size_gb = _size_to_gb(size)
        except ValueError:
            size_gb = 0.0
        result.append(PhysicalDisk(
            name=f"/dev/{name}", size_gb=size_gb, model=model,
            rotational=None if rota not in ("0", "1") else (rota == "1"),
        ))
    return result


# ── RAID ────────────────────────────────────────────────────
def get_md_raid() -> List[RaidInfo]:
    """解析 /proc/mdstat（群晖 / 威联通 / OMV / unRAID 底层普遍是 md）。"""
    raids: List[RaidInfo] = []
    content = read_file("/proc/mdstat")
    if not content:
        return raids

    current: Optional[RaidInfo] = None
    for line in content.splitlines():
        if not line.strip():
            if current:
                raids.append(current)
                current = None
            continue

        # 形如：md0 : active raid1 sda1[0] sdb1[1]
        if " : " in line and line.split()[0].startswith("md"):
            head, members = line.split(" : ", 1)
            tokens = members.split()
            state_part = tokens[0] if tokens else ""
            level_part = ""
            for tok in tokens:
                if tok.startswith("raid") or tok in ("linear", "multipath"):
                    level_part = tok
                    break
            member_tokens = [t for t in tokens[1:] if "[" in t]
            current = RaidInfo(
                name=head.strip(),
                kind="md",
                level=level_part or state_part,
                state="active" if state_part == "active" else state_part,
                members_total=len(member_tokens),
                members_active=len([t for t in member_tokens if "(F)" not in t]),
            )
            if "(F)" in members or "degraded" in members.lower():
                current.healthy = False
                current.errors.append("阵列降级（有成员盘失效）")
            continue

        if current:
            low = line.lower()
            if "recovery" in low or "resync" in low or "reshape" in low:
                current.state = "rebuilding"
                if "[" in line and "]" in line:
                    try:
                        seg = line.split("[")[1].split("]")[0]
                        pct = seg.count("=") / max(1, len(seg.replace(">", ""))) * 100
                        current.rebuild_percent = round(pct, 1)
                    except Exception:  # noqa: BLE001
                        pass

    if current:
        raids.append(current)
    return raids


def get_zfs() -> List[RaidInfo]:
    """zpool 状态（TrueNAS / OMV 常见）。"""
    raids: List[RaidInfo] = []
    if not have("zpool"):
        return raids

    out = run("zpool list -H -o name,size,alloc,free,health 2>/dev/null", timeout=10)
    for line in out.splitlines():
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) < 5:
            continue
        name, health = parts[0], parts[4].strip()
        healthy = health.upper() in ("ONLINE", "AVAIL")
        raid = RaidInfo(name=name, kind="zfs", level="zfs",
                        state=health.lower(), healthy=healthy)
        if not healthy:
            raid.errors.append(f"zpool 状态异常: {health}")

        detail = run(f"zpool status -P {name} 2>/dev/null", timeout=10)
        members = [ln for ln in detail.splitlines() if "/dev/" in ln]
        raid.members_total = len(members)
        raid.members_active = len([ln for ln in members if "ONLINE" in ln])
        if raid.members_total and raid.members_active < raid.members_total:
            raid.healthy = False
            raid.errors.append(f"{raid.members_total - raid.members_active} 块成员盘不在线")
        raids.append(raid)
    return raids


def get_btrfs() -> List[RaidInfo]:
    """btrfs 文件系统状态（群晖 Btrfs / OMV / 多数国产 NAS）。"""
    raids: List[RaidInfo] = []
    if not have("btrfs"):
        return raids

    out = run("btrfs filesystem show 2>/dev/null", timeout=10)
    for line in out.splitlines():
        if "Label:" not in line:
            continue
        name = line.split("'")[1] if "'" in line else ""
        try:
            devs = int(line.split("Total devices")[1].split()[0])
        except (IndexError, ValueError):
            devs = 0
        raids.append(RaidInfo(
            name=name or "btrfs", kind="btrfs", level="btrfs",
            state="mounted", members_total=devs, members_active=devs,
        ))

    # btrfs 单盘坏块不会自动降级，必须主动查 device stats
    stats = run("btrfs device stats / 2>/dev/null", timeout=10)
    if stats:
        bad = [ln.strip() for ln in stats.splitlines()
               if "errs" in ln and not ln.strip().endswith(" 0")]
        if bad:
            raids.append(RaidInfo(
                name="/", kind="btrfs", level="btrfs", state="error",
                healthy=False, errors=bad[:5],
            ))
    return raids


def detect_raids() -> List[RaidInfo]:
    raids = get_md_raid()
    raids.extend(get_zfs())
    raids.extend(get_btrfs())
    return raids


# ── SMART ───────────────────────────────────────────────────
def _last_int(line: str) -> int:
    """取一行里最后一个纯数字（smartctl 属性表 RAW_VALUE 常在行尾）。"""
    for tok in reversed(line.replace("|", " ").split()):
        t = tok.strip()
        if t.isdigit():
            return int(t)
    return 0


def _smart_one(device: str) -> SmartInfo:
    """smartctl 读取单盘健康（需要 root）。"""
    info = SmartInfo(device=device)
    out = run(f"smartctl -H -A {device} 2>&1", timeout=15)

    low_all = out.lower()
    if "permission denied" in low_all or "must be root" in low_all:
        info.message = "需要 root 权限"
        return info
    if "unable to detect device type" in low_all or "no such device" in low_all:
        info.message = "设备不可访问（可能在 RAID 卡后面）"
        return info

    for line in out.splitlines():
        low = line.lower()
        if low.startswith("smart overall-health self-assessment test result"):
            if "PASSED" in line.upper():
                info.healthy = True
            elif "FAILED" in line.upper():
                info.healthy = False
        elif "reallocated_sector_ct" in low:
            info.reallocated_sectors = _last_int(line)
        elif "current_pending_sector" in low:
            info.pending_sectors = _last_int(line)
        elif "offline_uncorrectable" in low:
            info.uncorrectable = _last_int(line)
        elif "power_on_hours" in low:
            info.power_on_hours = _last_int(line)
        elif "temperature_celsius" in low or low.startswith("194 temperature"):
            info.temperature_c = float(_last_int(line))
        elif low.startswith("model family") or low.startswith("device model"):
            info.model = line.split(":", 1)[-1].strip()

    if info.healthy is None and not info.message:
        info.message = "无法判定（可能是 USB 桥接盘 / 虚拟盘）"
    if (info.reallocated_sectors > 0 or info.pending_sectors > 0) and info.healthy is not False:
        info.healthy = False
        info.message = "存在坏道计数，建议尽快备份"
    return info


def detect_smart(physical: List[PhysicalDisk], enabled: bool = True) -> List[SmartInfo]:
    """批量读 SMART；没有 smartctl 就整体跳过。"""
    if not enabled or not IS_LINUX or not have("smartctl"):
        return []
    return [_smart_one(d.name) for d in physical[:16]]


# ── 读写速度 ────────────────────────────────────────────────
def test_write_speed(path: str, size_mb: int = 50) -> float:
    """顺序写测速，返回 MB/s。"""
    fpath = os.path.join(path, f"._nastool_write_test_{os.getpid()}")
    try:
        start = time.time()
        with open(fpath, "wb") as f:
            chunk = b"\0" * (1024 * 1024)
            for _ in range(size_mb):
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
        elapsed = time.time() - start
        return round(size_mb / elapsed, 1) if elapsed > 0 else 0.0
    except Exception:  # noqa: BLE001
        return 0.0
    finally:
        try:
            if os.path.exists(fpath):
                os.remove(fpath)
        except OSError:
            pass


def test_read_speed(path: str, size_mb: int = 50) -> float:
    """顺序读测速（先写后读，Linux 上尝试清缓存）。"""
    fpath = os.path.join(path, f"._nastool_read_test_{os.getpid()}")
    try:
        with open(fpath, "wb") as f:
            chunk = os.urandom(1024 * 1024)
            for _ in range(size_mb):
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())

        if IS_LINUX:
            run("sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null", timeout=10)

        start = time.time()
        with open(fpath, "rb") as f:
            while f.read(1024 * 1024):
                pass
        elapsed = time.time() - start
        return round(size_mb / elapsed, 1) if elapsed > 0 else 0.0
    except Exception:  # noqa: BLE001
        return 0.0
    finally:
        try:
            if os.path.exists(fpath):
                os.remove(fpath)
        except OSError:
            pass


def _safe_test_path(storage_path: str) -> bool:
    """验证目标路径可写。"""
    if not os.path.isdir(storage_path):
        return False
    try:
        test_file = os.path.join(storage_path, f"._nastool_rw_test_{os.getpid()}")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("nastool write test")
        os.remove(test_file)
        return True
    except Exception:  # noqa: BLE001
        return False


def check_storage(storage_path: str = "",
                  do_speed_test: bool = True,
                  do_smart: bool = True) -> StorageReport:
    """主入口：目标路径 + 挂载盘 + 物理盘 + RAID + SMART + 读写速度。"""
    report = StorageReport(target_path=storage_path)

    # 1. 路径存在性
    report.target_exists = os.path.exists(storage_path)
    report.is_dir = os.path.isdir(storage_path)

    if not report.target_exists:
        report.errors.append(f"目标路径 '{storage_path}' 不存在")
    elif not report.is_dir:
        report.errors.append(f"目标路径 '{storage_path}' 不是目录")
    else:
        # 2. 可写性
        report.can_write = _safe_test_path(storage_path)
        if not report.can_write:
            report.errors.append(f"目标路径 '{storage_path}' 不可写（权限不足或只读挂载）")

        # 3. 容量
        try:
            usage = shutil.disk_usage(storage_path)
            report.target_total_gb = round(usage.total / 1024 ** 3, 1)
            report.target_free_gb = round(usage.free / 1024 ** 3, 1)
            if usage.total > 0:
                used = usage.total - usage.free
                report.target_use_percent = round(used / usage.total * 100, 1)
        except Exception:  # noqa: BLE001
            pass

        # 4. 速度测试
        if do_speed_test and report.can_write:
            report.writable_test_size_mb = 50
            report.seq_write_mbps = test_write_speed(storage_path, 50)
            report.seq_read_mbps = test_read_speed(storage_path, 50)
            report.speed_test_done = True
            if report.seq_write_mbps == 0 and report.seq_read_mbps == 0:
                report.warnings.append("读写测速未取得有效数据（路径可能只读或 I/O 异常）")

    # 5. 磁盘 / RAID / SMART（与目标路径是否可用无关，都要采集）
    report.disks = get_mounted_disks()
    report.physical_disks = get_physical_disks()
    report.raids = detect_raids()

    if do_smart and report.physical_disks:
        report.smart = detect_smart(report.physical_disks, enabled=True)
        report.smart_checked = bool(report.smart)

    # 6. 告警汇总
    for d in report.disks:
        if d.use_percent >= 95:
            report.warnings.append(f"{d.mountpoint} 空间即将耗尽（{d.use_percent}%）")
        if d.inodes_use_percent >= 95:
            report.warnings.append(f"{d.mountpoint} inode 即将耗尽（{d.inodes_use_percent}%）")
        if d.readonly and d.fstype not in ("squashfs", "iso9660"):
            report.warnings.append(f"{d.mountpoint} 为只读挂载")

    if not report.physical_disks and IS_LINUX:
        report.warnings.append("未识别到物理磁盘（可能运行在容器/虚拟机中）")

    # 7. 综合判断
    bad_raid = [r for r in report.raids if not r.healthy]
    bad_smart = [s for s in report.smart if s.healthy is False]

    report.ok = (
        report.target_exists
        and report.is_dir
        and report.can_write
        and not report.errors
        and not bad_raid
        and not bad_smart
    )
    return report
