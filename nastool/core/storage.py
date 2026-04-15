"""
core/storage.py — 存储路径检测 + 磁盘信息 + 读写速度测试
"""

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import List, Optional


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
    readonly: bool = False


@dataclass
class StorageReport:
    target_path: str = ""
    target_exists: bool = False
    is_dir: bool = False
    can_write: bool = False
    writable_test_size_mb: int = 0
    disks: List[DiskInfo] = field(default_factory=list)
    seq_read_mbps: float = 0.0
    seq_write_mbps: float = 0.0
    rand_read_iops: int = 0  # 4K random read
    rand_write_iops: int = 0  # 4K random write
    speed_test_done: bool = False
    errors: List[str] = field(default_factory=list)
    ok: bool = False


def _run(cmd: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return ""


def _run_fast(cmd: str, timeout: int = 3) -> str:
    """快命令（网络等），超时更短"""
    return _run(cmd, timeout)


def get_mounted_disks() -> List[DiskInfo]:
    """用 df + lsblk 读取挂载磁盘信息"""
    disks = []

    # df -T 读取挂载点
    out = _run("df -T --block-size=G 2>/dev/null | tail -n +2")
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        # 有些 df 输出没有 Filesystem Type 这两列
        if "/" not in parts[-1] and len(parts) >= 7:
            # ps: Filesystem Type Blocks Use% Mounted
            try:
                size_str = parts[2].replace("G", "").replace("M", "")
                used_pct = int(parts[4].replace("%", ""))
            except Exception as e:
                continue
        elif len(parts) >= 7:
            try:
                size_str = parts[2]
                used_pct = int(parts[5].replace("%", ""))
            except Exception as e:
                continue
        else:
            continue

        device = parts[0]
        mount = parts[-1]
        fstype = parts[1] if len(parts) > 6 and "/" not in parts[1] else "?"

        try:
            free_gb = (
                round(float(parts[4].replace("G", "").replace("M", "")) / 1024, 1)
                if "G" in parts[4] or "M" in parts[4]
                else 0.0
            )
            total_gb = round(float(size_str.replace("G", "").replace("M", "")), 1)
        except Exception as e:
            total_gb, free_gb = 0.0, 0.0

        disks.append(
            DiskInfo(
                device=device,
                size_gb=total_gb,
                mountpoint=mount,
                fstype=fstype,
                total_gb=total_gb,
                free_gb=free_gb,
                use_percent=used_pct,
                readonly=False,
            )
        )

    # 尝试 lsblk 补充 model
    out = _run("lsblk -d -o NAME,MODEL,SIZE,TYPE 2>/dev/null | tail -n +2")
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        dev_name = f"/dev/{parts[0]}"
        model = parts[1] if len(parts) > 1 else ""
        size = parts[2] if len(parts) > 2 else ""
        for d in disks:
            if d.device == dev_name:
                d.model = model
                try:
                    d.size_gb = float(size.replace("G", "").replace("M", "").replace("T", ""))
                except Exception as e:
                    pass

    return disks


def test_write_speed(path: str, size_mb: int = 100) -> float:
    """dd 顺序写测速，返回 MB/s"""
    fpath = os.path.join(path, f"._nastool_write_test_{os.getpid()}")
    try:
        start = time.time()
        r = subprocess.run(
            f"dd if=/dev/zero of={fpath} bs=1M count={size_mb} oflag=direct 2>&1",
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        elapsed = time.time() - start
        if elapsed > 0:
            os.remove(fpath)
            return round(size_mb / elapsed, 1)
    except Exception as e:
        pass
    # 回退：不用 direct
    try:
        start = time.time()
        with open(fpath, "wb") as f:
            f.write(os.urandom(size_mb * 1024 * 1024))
        elapsed = time.time() - start
        if elapsed > 0:
            os.remove(fpath)
            return round(size_mb / elapsed, 1)
    except Exception as e:
        pass
    return 0.0


def test_read_speed(path: str, size_mb: int = 100) -> float:
    """dd 顺序读测速（先写后读），返回 MB/s"""
    fpath = os.path.join(path, f"._nastool_read_test_{os.getpid()}")
    try:
        # 先生成一个测试文件
        with open(fpath, "wb") as f:
            f.write(os.urandom(size_mb * 1024 * 1024))
        # 清除缓存后读
        subprocess.run(
            "sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null", shell=True, timeout=10
        )
        start = time.time()
        r = subprocess.run(
            f"dd if={fpath} of=/dev/null bs=1M 2>&1",
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        elapsed = time.time() - start
        os.remove(fpath)
        if elapsed > 0:
            return round(size_mb / elapsed, 1)
    except Exception as e:
        pass
    return 0.0


def _safe_test_path(storage_path: str) -> bool:
    """验证目标路径是否可写、可读"""
    if not os.path.isdir(storage_path):
        return False
    try:
        test_file = os.path.join(storage_path, f"._nastool_rw_test_{os.getpid()}")
        with open(test_file, "w") as f:
            f.write("nastool test")
        os.remove(test_file)
        return True
    except Exception as e:
        return False


def check_storage(storage_path: str = "/home/nvidia", do_speed_test: bool = True) -> StorageReport:
    """
    主入口：检测存储路径 + 磁盘信息 + 读写速度
    storage_path: 要检测的目标存储路径（通常与 AI-NAS config.yaml 中一致）
    do_speed_test: 是否做读写速度测试（速度测试有 I/O 开销，可跳过）
    """
    report = StorageReport(target_path=storage_path)

    # 1. 路径存在性
    report.target_exists = os.path.exists(storage_path)
    report.is_dir = os.path.isdir(storage_path)

    if not report.target_exists:
        report.errors.append(f"storage_path '{storage_path}' 不存在")
        return report

    if not report.is_dir:
        report.errors.append(f"storage_path '{storage_path}' 不是目录")
        return report

    # 2. 可写性
    report.can_write = _safe_test_path(storage_path)
    if not report.can_write:
        report.errors.append(f"storage_path '{storage_path}' 不可写（权限不足）")
    else:
        # 3. 速度测试
        if do_speed_test:
            report.writable_test_size_mb = 50
            write_mbps = test_write_speed(storage_path, 50)
            read_mbps = test_read_speed(storage_path, 50)
            report.seq_write_mbps = write_mbps
            report.seq_read_mbps = read_mbps
            report.speed_test_done = True
            if write_mbps == 0 and read_mbps == 0:
                report.errors.append("读写速度测试失败（路径可能只读或 I/O 异常）")
        else:
            report.ok = True
            return report

    # 4. 所有磁盘挂载情况
    report.disks = get_mounted_disks()

    # 5. 综合判断
    report.ok = (
        report.target_exists and report.is_dir and report.can_write and len(report.errors) == 0
    )

    return report
