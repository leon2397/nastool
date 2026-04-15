"""
core/device.py — CPU / 内存 / 主板 / 温度 / 系统信息
"""

import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CpuInfo:
    model: str = "未知"
    arch: str = ""
    cores: int = 0
    freq_mhz: int = 0
    flags: List[str] = field(default_factory=list)
    l1d_cache_kb: int = 0
    l2_cache_kb: int = 0
    l3_cache_kb: int = 0


@dataclass
class MemInfo:
    total_gb: float = 0.0
    available_gb: float = 0.0
    used_percent: float = 0.0
    swap_total_gb: float = 0.0
    swap_free_gb: float = 0.0


@dataclass
class BoardInfo:
    model: str = "未知"
    manufacturer: str = "未知"
    serial: str = ""
    os: str = ""
    os_version: str = ""
    kernel: str = ""
    uptime_hours: float = 0.0


@dataclass
class ThermalInfo:
    zone: str = ""
    temp_c: float = 0.0
    zone_type: str = ""


@dataclass
class DeviceReport:
    cpu: CpuInfo = field(default_factory=CpuInfo)
    memory: MemInfo = field(default_factory=MemInfo)
    board: BoardInfo = field(default_factory=BoardInfo)
    thermals: List[ThermalInfo] = field(default_factory=list)
    ok: bool = True
    errors: List[str] = field(default_factory=list)


def _run(cmd: str, timeout: int = 5) -> str:
    """安全执行 shell 命令，超时保护"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return ""


def _read_file(path: str, fallback="") -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception as e:
        return fallback


def get_cpu_info() -> CpuInfo:
    """从 /proc/cpuinfo + lscpu 获取 CPU 信息"""
    cpu = CpuInfo()
    cpu.arch = platform.machine()  # aarch64 / x86_64 / armv7l

    # 尝试 lscpu（最完整）
    out = _run("lscpu 2>/dev/null")
    if out:
        for line in out.splitlines():
            if "Model name" in line:
                cpu.model = line.split(":", 1)[1].strip()
            elif "Architecture:" in line:
                cpu.arch = line.split(":", 1)[1].strip()
            elif "CPU(s):" in line and "Thread" not in line:
                try:
                    cpu.cores = int(line.split(":", 1)[1].strip())
                except Exception as e:
                    pass
            elif "CPU max MHz" in line:
                try:
                    cpu.freq_mhz = int(float(line.split(":", 1)[1].strip()))
                except Exception as e:
                    pass
            elif "Flags" in line:
                cpu.flags = line.split(":", 1)[1].strip().split()

    # 备选：/proc/cpuinfo
    if not cpu.cores or cpu.model == "未知":
        out = _read_file("/proc/cpuinfo")
        for line in out.splitlines():
            if "processor" in line:
                cpu.cores += 1
            elif "Hardware" in line:
                cpu.model = line.split(":", 1)[1].strip()
            elif "model name" in line:
                cpu.model = line.split(":", 1)[1].strip()

    return cpu


def get_memory_info() -> MemInfo:
    """从 /proc/meminfo 读取内存信息"""
    mem = MemInfo()
    content = _read_file("/proc/meminfo")
    if not content:
        return mem

    for line in content.splitlines():
        if "MemTotal" in line:
            mem.total_gb = round(int(line.split()[1]) / 1024 / 1024, 2)
        elif "MemAvailable" in line:
            mem.available_gb = round(int(line.split()[1]) / 1024 / 1024, 2)
        elif "MemFree" in line and mem.available_gb == 0:
            mem.available_gb = round(int(line.split()[1]) / 1024 / 1024, 2)
        elif "SwapTotal" in line:
            mem.swap_total_gb = round(int(line.split()[1]) / 1024 / 1024, 2)
        elif "SwapFree" in line:
            mem.swap_free_gb = round(int(line.split()[1]) / 1024 / 1024, 2)

    if mem.total_gb > 0:
        mem.used_percent = round((mem.total_gb - mem.available_gb) / mem.total_gb * 100, 1)
    return mem


def get_board_info() -> BoardInfo:
    """读取系统/主板信息"""
    board = BoardInfo()
    board.os = platform.system()
    board.os_version = platform.version()
    board.kernel = platform.release()

    # /proc/uptime → 运行小时数
    uptime_sec = float(_read_file("/proc/uptime", "0").split()[0])
    board.uptime_hours = round(uptime_sec / 3600, 1)

    # 设备型号（按优先级尝试）
    for path in [
        "/sys/firmware/devicetree/base/model",
        "/sys/class/dmi/id/product_name",
        "/sys/class/dmi/id/board_name",
    ]:
        val = _read_file(path)
        if val:
            board.model = val
            break

    # 厂商
    for path in [
        "/sys/class/dmi/id/sys_vendor",
        "/sys/class/dmi/id/board_vendor",
    ]:
        val = _read_file(path)
        if val:
            board.manufacturer = val
            break

    # 序列号
    for path in [
        "/sys/class/dmi/id/product_serial",
        "/sys/class/dmi/id/board_serial",
    ]:
        val = _read_file(path)
        if val and val not in ("", "None"):
            board.serial = val
            break

    return board


def get_thermal_zones() -> List[ThermalInfo]:
    """读取 hwmon 温度传感器"""
    thermals = []

    # 遍历 /sys/class/hwmon
    try:
        for name in os.listdir("/sys/class/hwmon"):
            base = f"/sys/class/hwmon/{name}"
            name_file = _read_file(f"{base}/name", "")
            # 读取所有 temp*_input 文件
            for entry in os.listdir(base):
                if entry.startswith("temp") and entry.endswith("_input"):
                    try:
                        temp_millideg = int(_read_file(f"{base}/{entry}"))
                        zone_num = entry.replace("temp", "").replace("_input", "")
                        zone_type = _read_file(f"{base}/temp{zone_num}_label", name_file or "cpu")
                        thermals.append(
                            ThermalInfo(
                                zone=zone_num,
                                temp_c=round(temp_millideg / 1000.0, 1),
                                zone_type=zone_type,
                            )
                        )
                    except Exception as e:
                        pass
    except Exception as e:
        pass

    # 备选：/sys/class/thermal
    if not thermals:
        for zone in os.listdir("/sys/class/thermal"):
            if not zone.startswith("thermal_zone"):
                continue
            tpath = f"/sys/class/thermal/{zone}"
            try:
                temp_millideg = int(_read_file(f"{tpath}/temp", "0"))
                trip_type = _read_file(f"{tpath}/trip_point_0_type", "unknown")
                thermals.append(
                    ThermalInfo(
                        zone=zone,
                        temp_c=round(temp_millideg / 1000.0, 1),
                        zone_type=trip_type,
                    )
                )
            except Exception as e:
                pass

    return thermals


def get_device_info() -> DeviceReport:
    """
    主入口：采集完整设备信息
    任一子模块失败不影响整体，继续采集其他项
    """
    report = DeviceReport()
    errors = []

    # CPU
    try:
        report.cpu = get_cpu_info()
    except Exception as e:
        errors.append(f"CPU: {e}")

    # 内存
    try:
        report.memory = get_memory_info()
    except Exception as e:
        errors.append(f"内存: {e}")

    # 主板
    try:
        report.board = get_board_info()
    except Exception as e:
        errors.append(f"主板: {e}")

    # 温度
    try:
        report.thermals = get_thermal_zones()
    except Exception as e:
        errors.append(f"温度: {e}")

    report.errors = errors
    report.ok = len(errors) == 0
    return report
