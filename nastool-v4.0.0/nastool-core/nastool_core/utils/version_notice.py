# -*- coding: utf-8 -*-
"""
nastool/utils/version_notice.py
================================
首次运行 / 版本变化检测与提示模块（v7.1.0）

功能：
- 检测版本变化（首次运行 / 版本升级 / 版本降级）
- 显示更新摘要（不阻断流程）
- 支持用户跳过（同一版本不再提示）
- 离线超时 5s 自动跳过

集成点：arm_diagnose.py main() 函数，parse_args() 之后、print_banner() 之前
"""
from __future__ import annotations

import json
import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional

# Resolve nastool root (one level up from utils/)
_NASTOOL_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(_NASTOOL_ROOT))

# Version info helpers - use nastool_common's version
try:
    from nastool_common import __version__
except ImportError:
    __version__ = "4.0.0"
try:
    from core.version_info import get_version_info
except ImportError:
    def get_version_info():
        return {"version": __version__, "git_hash": "", "checks_total": 0, "checks_parts": "?"}

try:
    from nastool_core.checks import list_available_checks
except ImportError:
    def list_available_checks():
        return {}


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_DIR = Path.home() / ".nastool"
CACHE_FILE = CACHE_DIR / "version_cache.json"
CHANGELOG_URL = "https://raw.githubusercontent.com/nastool/nastool/main/CHANGELOG.md"
TIMEOUT_SECONDS = 5


# ---------------------------------------------------------------------------
# VersionNotice class
# ---------------------------------------------------------------------------

class VersionNotice:
    """
    首次运行 / 版本变化检测。

    使用方式：
        notice = VersionNotice()
        notice.check_and_show()        # 显示提示（如有新版本）
        notice.save()                  # 保存当前状态
    """

    # 缓存文件字段
    _FIELDS = ("version", "git_hash", "checks_total", "checks_by_category",
               "last_run", "device_profile", "skip_notice_for_version")

    def __init__(self, current_version: Optional[str] = None,
                 git_hash: str = "",
                 checks_total: int = 0,
                 checks_by_category: Optional[dict] = None,
                 device_profile: str = ""):
        self.version = current_version or __version__
        self.git_hash = git_hash
        self.checks_total = checks_total
        self.checks_by_category = checks_by_category or {}
        self.device_profile = device_profile
        self._cache: dict = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load(self) -> dict:
        """从缓存文件加载上次状态。"""
        if self._loaded:
            return self._cache
        self._loaded = True
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, encoding="utf-8") as f:
                    raw = json.load(f)
                    self._cache = {k: raw[k] for k in self._FIELDS if k in raw}
            except (json.JSONDecodeError, IOError):
                self._cache = {}
        return self._cache

    def save(self) -> None:
        """保存当前状态到缓存文件。"""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache = self.load()
        cache.update({
            "version": self.version,
            "git_hash": self.git_hash,
            "checks_total": self.checks_total,
            "checks_by_category": self.checks_by_category,
            "last_run": _iso_now(),
            "device_profile": self.device_profile,
        })
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Detection logic
    # ------------------------------------------------------------------

    def is_first_run(self) -> bool:
        """从未运行过（缓存文件不存在）。"""
        return not CACHE_FILE.exists()

    def is_version_changed(self) -> bool:
        """版本号是否变化（首次运行或版本号不同）。"""
        cache = self.load()
        if not cache:
            return True  # first run
        cached_version = cache.get("version", "")
        return cached_version != self.version

    def should_show_notice(self) -> bool:
        """
        是否应显示提示。

        返回 False 的情况：
        - 首次运行但用户已跳过（skip_notice_for_version == "first_run"）
        - 同一版本重复运行（用户已点过"跳过"）
        """
        cache = self.load()
        if not cache:
            return True  # first run -- always show
        # User already dismissed notice for this version
        skip_for = cache.get("skip_notice_for_version", "")
        if skip_for == self.version:
            return False
        return True

    def dismiss_for_current_version(self) -> None:
        """用户点击"跳过"后，标记当前版本已忽略。"""
        cache = self.load()
        cache["skip_notice_for_version"] = self.version
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Change summary
    # ------------------------------------------------------------------

    def get_change_summary(self) -> dict:
        """
        计算版本变化摘要（检查项数量变化）。

        Returns:
            dict with keys: is_upgrade, is_downgrade, checks_added, checks_removed
        """
        cache = self.load()
        prev_total = cache.get("checks_total", 0)
        prev_by_cat = cache.get("checks_by_category", {})

        return {
            "is_upgrade": self.version > cache.get("version", ""),
            "is_downgrade": self.version < cache.get("version", ""),
            "checks_added": max(0, self.checks_total - prev_total),
            "checks_removed": max(0, prev_total - self.checks_total),
            "prev_by_cat": prev_by_cat,
            "curr_by_cat": self.checks_by_category,
        }

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def check_and_show(self) -> bool:
        """
        主入口：检测是否需要显示提示，如需要则打印并等待用户选择。

        Returns:
            True  = 用户选择继续（显示了提示，用户按 Enter / 跳过）
            False = 未显示提示（已缓存跳过 / 离线）
        """
        if not self.should_show_notice():
            return False

        first_run = self.is_first_run()
        changed = self.is_version_changed()

        if first_run:
            self._show_first_run_notice()
        elif changed:
            self._show_version_change_notice()
        else:
            # Same version, no notice needed
            return False

        choice = self._prompt_user()
        if choice == "s":
            self.dismiss_for_current_version()
        return True  # always continue after notice

    def _show_first_run_notice(self) -> None:
        print()
        print("[NEW] nastool v%s 首次运行！" % self.version)
        print("-" * 50)
        print("  nastool 是 ARM NAS 设备诊断工具，可检测：")
        print("    - 系统状态（CPU / 内存 / 磁盘 / 温度）")
        print("    - 网络配置（DNS / 网关 / 延迟）")
        print("    - 存储状态（容量 / 读写速度）")
        print("    - AI 加速器（GPU / CUDA / TensorRT）")
        print("    - NAS 服务（SMB / NFS / FTP / WebDAV）")
        print("    - 安全配置（SSH / 防火墙 / 用户权限）")
        print()
        print("  使用方法：")
        print("    python arm_diagnose.py --quick      # 快速诊断")
        print("    python arm_diagnose.py --full        # 完整诊断")
        print("    python arm_diagnose.py --fix         # 诊断 + 修复")
        print("    python arm_diagnose.py --doctor      # 运行环境检查")
        print()
        print("  [!] 首次运行会自动检测设备类型，无需指定 --profile")
        print()

    def _show_version_change_notice(self) -> None:
        summary = self.get_change_summary()
        print()
        print("[UPDATE] nastool v%s 更新！" % self.version)
        print("-" * 50)

        prev = summary.get("is_downgrade") and "v%s" % self.load().get("version", "?") or "旧版本"
        print("  从 %s 升级到 v%s" % (prev, self.version))

        # Show check count changes
        if summary["checks_added"] > 0 or summary["checks_removed"] > 0:
            print("  \u2022 检查项数量变化：%+d（新增 %d / 移除 %d）" % (
                summary["checks_added"] - summary["checks_removed"],
                summary["checks_added"],
                summary["checks_removed"],
            ))
        elif self.checks_total > 0:
            print("  \u2022 共 %d 个检查项" % self.checks_total)

        if self.device_profile:
            print("  - 设备类型：%s" % self.device_profile)

        print()
        print("  完整更新日志请查看：CHANGELOG.md")
        print()

    def _prompt_user(self) -> str:
        """
        等待用户按键。

        Returns:
            ""  = Enter（继续）
            "s" = s（跳过本次提示）
        """
        try:
            if sys.stdin.isatty():
                print("  [Enter 继续]  [S 跳过本次提示]", end="", flush=True)
                key = _read_char()
                print()  # newline after keypress
                if key.lower() == "s":
                    return "s"
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------------
    # Offline changelog fetch (background thread)
    # ------------------------------------------------------------------

    def fetch_changelog_async(self, url: str = CHANGELOG_URL) -> None:
        """
        后台线程获取远程 changelog（5s 超时）。
        结果存入 self._remote_changelog，不阻断主流程。
        """
        self._remote_changelog = None

        def _fetch():
            try:
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": "nastool"})
                with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                    self._remote_changelog = resp.read().decode("utf-8", errors="ignore")
            except Exception:
                pass

        t = threading.Thread(target=_fetch, daemon=True)
        t.start()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=8))  # Asia/Shanghai
    return datetime.now(tz).isoformat(timespec="seconds")


def _read_char() -> str:
    """
    跨平台读取单个字符（无需 Enter）。
    Windows: msvcrt.getch()；Linux/macOS: tty + termios。
    """
    try:
        # Windows
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\r", b"\n"):
            return ""
        return ch.decode("utf-8", errors="ignore")
    except ImportError:
        pass

    try:
        # Linux/macOS
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def check_and_show_notice(device_profile: str = "") -> bool:
    """
    一行 API：在 arm_diagnose.py main() 中调用。

    用法（在 main() 函数开头，parse_args() 之后）：
        from utils.version_notice import check_and_show_notice
        notice = check_and_show_notice(args.profile or "")
        notice.save()
    """
    info = get_version_info()
    current_version = info.get("version", __version__)
    git_hash = info.get("git_hash", "")
    checks_total = info.get("checks_total", 0)

    # Build checks_by_category
    checks_by_category: dict = {}
    try:
        checks = list_available_checks()
        for check in checks.values():
            cat = check.get("category", "other")
            checks_by_category[cat] = checks_by_category.get(cat, 0) + 1
    except Exception:
        pass

    notice = VersionNotice(
        current_version=current_version,
        git_hash=git_hash,
        checks_total=checks_total,
        checks_by_category=checks_by_category,
        device_profile=device_profile,
    )
    shown = notice.check_and_show()
    notice.save()
    return shown
