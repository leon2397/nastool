"""
core/util.py — 跨平台执行与读取工具

所有采集模块统一走这里，保证三件事：
  1. 任何外部命令失败都不会抛异常（NAS 上权限/命令缺失很常见）
  2. 统一 UTF-8 + errors="replace"，避免中文 Windows / 非 UTF-8 locale 解码崩溃
  3. 非 Linux 环境（Windows / macOS）读取 /proc、/sys 时安全返回空值
"""
import os
import platform
import shutil
import subprocess

IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"
IS_DARWIN = platform.system() == "Darwin"
IS_ROOT = (hasattr(os, "geteuid") and os.geteuid() == 0)

# 已知 NAS / 嵌入式平台常见的存储挂载点，用于自动挑目标路径
COMMON_NAS_MOUNTS = [
    "/volume1", "/volume2",            # Synology DSM
    "/share/CACHEDEV1_DATA",           # QNAP QTS
    "/mnt", "/media", "/data", "/srv",  # 通用 Linux
    "/mnt/user",                       # unRAID
    "/tank", "/mnt/tank",              # TrueNAS
    "/vol1", "/vol2",                  # 部分国产 NAS
]


def run(cmd: str, timeout: int = 5) -> str:
    """
    执行 shell 命令并返回 stdout；失败返回空串。

    解码策略：先按 UTF-8 严格解码，失败再退回系统 locale。
    这样既能读 Linux 的 UTF-8 输出，也能正确处理中文 Windows 的 CP936 输出
    （原实现固定 text=True，在中文 Windows 上会把「以太网」解成乱码）。
    """
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout)
        raw = r.stdout or b""
        if isinstance(raw, bytes):
            try:
                return raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                pass
            # Windows 控制台程序（w32tm / netstat 等）输出的是 ANSI 代码页，
            # 中文系统是 GBK。不能用 locale.getpreferredencoding()——
            # 在 UTF-8 模式下它返回 utf-8，会把 GBK 直接解成乱码。
            candidates = ["mbcs"] if IS_WINDOWS else []
            import locale
            candidates.append(locale.getpreferredencoding(False) or "utf-8")
            for enc in candidates:
                try:
                    return raw.decode(enc).strip()
                except (UnicodeDecodeError, LookupError):
                    continue
            return raw.decode("utf-8", errors="replace").strip()
        return str(raw).strip()
    except Exception:  # noqa: BLE001 - 采集器必须容错
        return ""


def run_ps(script: str, timeout: int = 20) -> str:
    """
    执行 PowerShell 片段并强制 UTF-8 输出。

    用参数列表而不是 shell 拼接，避免脚本里的引号被 cmd 吞掉
    （原先用 shell=True + 转义引号，导致带引号的脚本直接返回空值）。
    """
    if not IS_WINDOWS:
        return ""
    full = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
            "$OutputEncoding=[System.Text.Encoding]::UTF8;" + script)
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", full],
            capture_output=True, timeout=timeout,
        )
        raw = r.stdout or b""
        try:
            return raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            return raw.decode("mbcs", errors="replace").strip()
    except Exception:  # noqa: BLE001
        return ""


def run_ok(cmd: str, timeout: int = 5) -> bool:
    """执行命令并只关心是否成功（退出码 0）。"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def read_file(path: str, fallback: str = "") -> str:
    """读取文本文件首行/全文（strip）；失败返回 fallback。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except Exception:  # noqa: BLE001
        return fallback


def read_first_line(path: str, fallback: str = "") -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.readline().strip()
    except Exception:  # noqa: BLE001
        return fallback


def path_exists(path: str) -> bool:
    try:
        return os.path.exists(path)
    except Exception:  # noqa: BLE001
        return False


def have(cmd: str) -> bool:
    """命令是否存在（不执行）。"""
    return shutil.which(cmd) is not None


def safe_listdir(path: str) -> list:
    """安全列举目录；不存在或无权限返回空列表。"""
    try:
        return os.listdir(path)
    except OSError:
        return []


def human_gb(num: float) -> str:
    """字节 → 人类可读（GB/TB 自适应）。"""
    try:
        gb = float(num)
    except (TypeError, ValueError):
        return "0 GB"
    if gb >= 1024:
        return f"{gb / 1024:.1f} TB"
    return f"{gb:.0f} GB"


def is_writable_dir(path: str) -> bool:
    """目录是否真的能写（只建一个临时文件马上删）。"""
    if not os.path.isdir(path):
        return False
    probe = os.path.join(path, f"._nastool_pick_{os.getpid()}")
    try:
        with open(probe, "w", encoding="utf-8") as f:
            f.write("probe")
        os.remove(probe)
        return True
    except Exception:  # noqa: BLE001
        return False


def pick_default_storage_path() -> str:
    """
    自动挑选「最像 NAS 数据盘」的路径。

    规则：已知 NAS 挂载点 → 可用空间最大的非系统盘 → 家目录 → 当前目录。
    只返回可写目录，避免一上来就报「不可写」的假故障。
    """
    if IS_WINDOWS:
        import shutil as _shutil
        best, best_free = "", -1
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            root = f"{letter}:\\"
            if not os.path.isdir(root) or not is_writable_dir(root):
                continue
            try:
                free = _shutil.disk_usage(root).free
            except OSError:
                continue
            if free > best_free:
                best, best_free = root, free
        if best:
            return best
        home = os.environ.get("USERPROFILE", "")
        if home and is_writable_dir(home):
            return home
        return os.getcwd()

    for candidate in COMMON_NAS_MOUNTS:
        if is_writable_dir(candidate):
            return candidate

    # 没有典型 NAS 挂载点：选可写的、可用空间最大的挂载点
    best, best_free = "", -1
    for line in run("df -kP 2>/dev/null | tail -n +2").splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        mount = parts[-1]
        if mount.startswith(("/proc", "/sys", "/dev", "/run", "/snap", "/boot")):
            continue
        if not is_writable_dir(mount):
            continue
        try:
            free_kb = int(parts[3])
        except ValueError:
            continue
        if free_kb > best_free:
            best, best_free = mount, free_kb
    if best:
        return best

    home = os.path.expanduser("~")
    if is_writable_dir(home):
        return home
    return os.getcwd()
