"""
core/device.py — CPU / 内存 / 主板 / 温度 / 虚拟化 / 系统信息

Linux 走 /proc + /sys + lscpu；Windows / macOS 走各自的系统接口，
保证「通用 NAS 检测工具」在非 Linux 环境下也能给出有效信息（而不是一片未知）。
"""
import os
import platform
from dataclasses import dataclass, field
from typing import List

from .util import IS_DARWIN, IS_LINUX, IS_WINDOWS, read_file, run, run_ps, safe_listdir


@dataclass
class CpuInfo:
    model: str = "未知"
    arch: str = ""
    cores: int = 0
    physical_cores: int = 0
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
    hostname: str = ""
    uptime_hours: float = 0.0


@dataclass
class ThermalInfo:
    zone: str = ""
    temp_c: float = 0.0
    zone_type: str = ""


@dataclass
class DeviceFacts:
    cpu: CpuInfo = field(default_factory=CpuInfo)
    memory: MemInfo = field(default_factory=MemInfo)
    board: BoardInfo = field(default_factory=BoardInfo)
    thermals: List[ThermalInfo] = field(default_factory=list)
    virtualization: str = ""      # 物理机 / docker / lxc / kvm / vmware / hyper-v
    collect_errors: List[str] = field(default_factory=list)


# ── CPU ─────────────────────────────────────────────────────
def _cpu_linux(cpu: CpuInfo) -> None:
    out = run("lscpu 2>/dev/null", timeout=5)
    if out:
        for line in out.splitlines():
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if key == "Model name":
                cpu.model = val
            elif key == "Architecture":
                cpu.arch = val
            elif key in ("CPU(s)", "Core(s) per socket", "Socket(s)"):
                try:
                    n = int(val)
                    if key == "CPU(s)":
                        cpu.cores = n
                    elif key == "Core(s) per socket":
                        cpu.physical_cores = n * max(1, cpu.physical_cores or 1)
                except ValueError:
                    pass
            elif key in ("CPU max MHz", "CPU MHz"):
                try:
                    cpu.freq_mhz = int(float(val))
                except ValueError:
                    pass
            elif key == "Flags":
                cpu.flags = val.split()

    if not cpu.cores or cpu.model == "未知":
        cores, model = 0, cpu.model
        for line in read_file("/proc/cpuinfo").splitlines():
            if line.startswith("processor"):
                cores += 1
            elif line.startswith("model name") or line.startswith("Hardware"):
                model = line.split(":", 1)[-1].strip()
        cpu.cores = cpu.cores or cores
        cpu.model = model if model and model != "未知" else f"CPU ({cpu.arch})"

    if not cpu.freq_mhz:
        try:
            khz = int(read_file("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "0") or 0)
            cpu.freq_mhz = khz // 1000
        except ValueError:
            pass


def _cpu_windows(cpu: CpuInfo) -> None:
    out = run_ps('Get-CimInstance Win32_Processor | '
                 'Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed '
                 '| ConvertTo-Csv -NoTypeInformation', timeout=25)
    for line in out.splitlines()[1:]:
        parts = [p.strip('"') for p in line.split(",")]
        if len(parts) < 4:
            continue
        cpu.model = parts[0] or platform.processor() or "未知"
        try:
            cpu.physical_cores = int(parts[1])
            cpu.cores = int(parts[2])
            cpu.freq_mhz = int(parts[3])
        except ValueError:
            pass
        break
    if cpu.model == "未知":
        cpu.model = platform.processor() or "未知"


def _cpu_macos(cpu: CpuInfo) -> None:
    cpu.model = run("sysctl -n machdep.cpu.brand_string 2>/dev/null", timeout=5) or platform.processor()
    try:
        cpu.cores = int(run("sysctl -n hw.logicalcpu 2>/dev/null", timeout=5) or 0)
        cpu.physical_cores = int(run("sysctl -n hw.physicalcpu 2>/dev/null", timeout=5) or 0)
        cpu.freq_mhz = int(int(run("sysctl -n hw.cpufrequency 2>/dev/null", timeout=5) or 0) / 1000)
    except ValueError:
        pass


def get_cpu_info() -> CpuInfo:
    cpu = CpuInfo(arch=platform.machine())
    try:
        if IS_WINDOWS:
            _cpu_windows(cpu)
        elif IS_DARWIN:
            _cpu_macos(cpu)
        elif IS_LINUX:
            _cpu_linux(cpu)
    except Exception:  # noqa: BLE001
        pass
    if not cpu.cores:
        cpu.cores = os.cpu_count() or 0
    return cpu


# ── 内存 ────────────────────────────────────────────────────
def _mem_linux(mem: MemInfo) -> None:
    content = read_file("/proc/meminfo")
    if not content:
        return
    for line in content.splitlines():
        key, _, val = line.partition(":")
        parts = val.split()
        if not parts:
            continue
        try:
            kb = int(parts[0])
        except ValueError:
            continue
        if key == "MemTotal":
            mem.total_gb = round(kb / 1024 / 1024, 2)
        elif key == "MemAvailable":
            mem.available_gb = round(kb / 1024 / 1024, 2)
        elif key == "MemFree" and mem.available_gb == 0:
            mem.available_gb = round(kb / 1024 / 1024, 2)
        elif key == "SwapTotal":
            mem.swap_total_gb = round(kb / 1024 / 1024, 2)
        elif key == "SwapFree":
            mem.swap_free_gb = round(kb / 1024 / 1024, 2)


def _mem_windows(mem: MemInfo) -> None:
    """用 GlobalMemoryStatusEx（ctypes），不依赖外部命令。"""
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        mem.total_gb = round(stat.ullTotalPhys / 1024 ** 3, 2)
        mem.available_gb = round(stat.ullAvailPhys / 1024 ** 3, 2)
        mem.used_percent = float(stat.dwMemoryLoad)
        page_total = stat.ullTotalPageFile - stat.ullTotalPhys
        page_free = stat.ullAvailPageFile - stat.ullAvailPhys
        if page_total > 0:
            mem.swap_total_gb = round(page_total / 1024 ** 3, 2)
            mem.swap_free_gb = round(max(0, page_free) / 1024 ** 3, 2)


def _mem_macos(mem: MemInfo) -> None:
    try:
        total = int(run("sysctl -n hw.memsize 2>/dev/null", timeout=5) or 0)
        mem.total_gb = round(total / 1024 ** 3, 2)
    except ValueError:
        pass
    vm = run("vm_stat 2>/dev/null", timeout=5)
    page_size = 4096
    free_pages = 0
    for line in vm.splitlines():
        if "page size of" in line:
            digits = "".join(ch for ch in line if ch.isdigit())
            if digits:
                page_size = int(digits)
        elif line.startswith("Pages free"):
            free_pages = int(line.split(":")[1].strip().rstrip("."))
    if free_pages:
        mem.available_gb = round(free_pages * page_size / 1024 ** 3, 2)


def get_memory_info() -> MemInfo:
    mem = MemInfo()
    try:
        if IS_WINDOWS:
            _mem_windows(mem)
        elif IS_DARWIN:
            _mem_macos(mem)
        else:
            _mem_linux(mem)
    except Exception:  # noqa: BLE001
        pass
    if mem.total_gb > 0 and not mem.used_percent:
        mem.used_percent = round((mem.total_gb - mem.available_gb) / mem.total_gb * 100, 1)
    return mem


# ── 主板 / 系统 ─────────────────────────────────────────────
def _uptime_hours() -> float:
    if IS_LINUX:
        try:
            return round(float(read_file("/proc/uptime", "0").split()[0]) / 3600, 1)
        except (ValueError, IndexError):
            return 0.0
    if IS_DARWIN:
        try:
            boot = int(run("sysctl -n kern.boottime 2>/dev/null", timeout=5).split("sec = ")[1].split(",")[0])
            import time
            return round((time.time() - boot) / 3600, 1)
        except (ValueError, IndexError):
            return 0.0
    if IS_WINDOWS:
        out = run_ps('[math]::Round(((Get-Date) - (Get-CimInstance '
                     'Win32_OperatingSystem).LastBootUpTime).TotalHours,1)', timeout=20)
        try:
            return float(out)
        except ValueError:
            return 0.0
    return 0.0


def get_board_info() -> BoardInfo:
    board = BoardInfo(
        os=platform.system(),
        os_version=platform.version(),
        kernel=platform.release(),
        hostname=platform.node(),
        uptime_hours=_uptime_hours(),
    )

    if IS_LINUX:
        for path in ("/sys/firmware/devicetree/base/model",
                     "/sys/class/dmi/id/product_name",
                     "/sys/class/dmi/id/board_name"):
            val = read_file(path).rstrip("\x00")
            if val and val.strip():
                board.model = val.strip()
                break
        for path in ("/sys/class/dmi/id/sys_vendor", "/sys/class/dmi/id/board_vendor"):
            val = read_file(path)
            if val and val.strip():
                board.manufacturer = val.strip()
                break
        for path in ("/sys/class/dmi/id/product_serial", "/sys/class/dmi/id/board_serial"):
            val = read_file(path)
            if val and val.strip() not in ("", "None", "0"):
                board.serial = val.strip()
                break
    elif IS_WINDOWS:
        out = run_ps('Get-CimInstance Win32_ComputerSystem | '
                     'Select-Object Manufacturer,Model | ConvertTo-Csv -NoTypeInformation',
                     timeout=25)
        for line in out.splitlines()[1:]:
            parts = [p.strip('"') for p in line.split(",")]
            if len(parts) >= 2:
                board.manufacturer, board.model = parts[0] or "未知", parts[1] or "未知"
                break
        board.os_version = platform.platform(terse=True)
    elif IS_DARWIN:
        board.manufacturer = "Apple"
        board.model = run("sysctl -n hw.model 2>/dev/null", timeout=5) or "Mac"
        board.os_version = platform.mac_ver()[0]

    return board


def detect_virtualization() -> str:
    """判断运行环境：物理机 / 容器 / 常见虚拟机。"""
    if os.path.exists("/.dockerenv"):
        return "docker"
    cgroup = read_file("/proc/1/cgroup")
    if "lxc" in cgroup:
        return "lxc"
    if "kubepods" in cgroup:
        return "kubernetes"
    if IS_WINDOWS:
        out = run_ps('(Get-CimInstance Win32_ComputerSystem).Model', timeout=20)
        low = out.lower()
        for key, name in (("virtualbox", "virtualbox"), ("vmware", "vmware"),
                          ("kvm", "kvm"), ("virtual machine", "hyper-v")):
            if key in low:
                return name
        return "physical"
    # DMI / hypervisor 标识
    product = read_file("/sys/class/dmi/id/product_name").lower()
    for key, name in (("kvm", "kvm"), ("vmware", "vmware"), ("virtualbox", "virtualbox"),
                      ("qemu", "qemu"), ("virtual machine", "hyper-v")):
        if key in product:
            return name
    if os.path.exists("/dev/lxc"):
        return "lxc"
    return "physical"


def get_thermal_zones() -> List[ThermalInfo]:
    """读取温度传感器（hwmon 优先，thermal_zone 兜底）。"""
    thermals: List[ThermalInfo] = []
    if not IS_LINUX:
        return thermals

    for name in safe_listdir("/sys/class/hwmon"):
        base = f"/sys/class/hwmon/{name}"
        hw_name = read_file(f"{base}/name")
        for entry in safe_listdir(base):
            if not (entry.startswith("temp") and entry.endswith("_input")):
                continue
            raw = read_file(f"{base}/{entry}", "0")
            try:
                temp_c = round(int(raw) / 1000.0, 1)
            except ValueError:
                continue
            zone_num = entry.replace("temp", "").replace("_input", "")
            label = read_file(f"{base}/temp{zone_num}_label", hw_name or "cpu")
            thermals.append(ThermalInfo(zone=f"{hw_name}/{zone_num}", temp_c=temp_c,
                                        zone_type=label or hw_name or "cpu"))

    if not thermals:
        for zone in safe_listdir("/sys/class/thermal"):
            if not zone.startswith("thermal_zone"):
                continue
            raw = read_file(f"/sys/class/thermal/{zone}/temp", "0")
            try:
                temp_c = round(int(raw) / 1000.0, 1)
            except ValueError:
                continue
            ztype = read_file(f"/sys/class/thermal/{zone}/type", "unknown")
            thermals.append(ThermalInfo(zone=zone, temp_c=temp_c, zone_type=ztype))

    return thermals


def get_device_info() -> DeviceFacts:
    """主入口：任一子项失败不影响其他项。"""
    report = DeviceFacts()
    errors = []

    for name, fn, attr in (
        ("CPU", get_cpu_info, "cpu"),
        ("内存", get_memory_info, "memory"),
        ("主板", get_board_info, "board"),
        ("温度", get_thermal_zones, "thermals"),
        ("虚拟化", detect_virtualization, "virtualization"),
    ):
        try:
            setattr(report, attr, fn())
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")

    report.collect_errors = errors
    return report
