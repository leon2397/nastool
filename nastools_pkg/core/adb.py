# -*- coding: utf-8 -*-
"""
core/adb.py — USB 直连封装（GUI 层）

本模块是 nastool/usb/manager.py 的 GUI 封装，
nastools_pkg 使用此模块（不在 nastool 依赖链中）。

功能：
  - 自动发现 USB 连接的 ARM 设备（四种方式）
  - 通过 ADB / USB Gadget / CDC-ACM 执行命令
  - 设备信息读取与诊断
  - USB 拔插事件监听
  - Agent 一键安装（可选注册 Relay）
"""

from __future__ import annotations

import subprocess
import time
import threading
import logging
import os
from typing import List, Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)

# ── 延迟导入统一管理器 ─────────────────────────────────────────────


def _get_usb_manager():
    """延迟导入，避免循环依赖"""
    from nastool.usb import USBManager, USBDevice, ConnectionMode

    return USBManager, USBDevice, ConnectionMode


# ── 数据结构（GUI 层）──────────────────────────────────────────────


class USBConnectionManager:
    """
    USB 连接管理器（GUI 封装层）

    统一调度四种 USB 连接方式（ADB / USB Gadget / CDC-ACM / MTP），
    线程安全。

    Usage:
        mgr = USBConnectionManager()

        if not mgr.is_adb_installed():
            print(mgr.install_hint())

        devices = mgr.list_devices()
        for dev in devices:
            print(f"{dev.label}: {dev.state}")

        # 监听拔插事件
        def on_plugged(dev):
            print(f"设备插入: {dev.label}")

        def on_unplugged(serial):
            print(f"设备拔出: {serial}")

        mgr.start_watching(on_plugged, on_unplugged)
        # ...
        mgr.stop_watching()
    """

    def __init__(self, adb_path: Optional[str] = None):
        self._adb_path = adb_path
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_watch = threading.Event()
        self._last_devices: Dict[str, str] = {}
        self._manager = None  # 懒加载

    def _get_manager(self):
        if self._manager is None:
            USBManager, _, _ = _get_usb_manager()
            self._manager = USBManager()
        return self._manager

    # ── ADB 专用 ──────────────────────────────────────────────────

    def is_adb_installed(self) -> bool:
        """ADB 是否已安装"""
        mgr = self._get_manager()
        return mgr.get_backend(
            __import__("nastool.usb", fromlist=["ConnectionMode"]).ConnectionMode.ADB
        ).is_available()

    def adb_version(self) -> str:
        """ADB 版本字符串"""
        try:
            r = subprocess.run(
                ["adb", "version"], capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip().splitlines()[0] if r.returncode == 0 else "未知"
        except Exception:
            return "未知"

    def install_hint(self) -> str:
        return (
            "请安装 Android Platform Tools（ADB）:\n\n"
            "方式1（推荐，用 winget）:\n"
            "  winget install Google.AndroidPlatformTools\n\n"
            "方式2（手动下载）:\n"
            "  1. 访问 https://developer.android.com/studio/releases/platform-tools\n"
            "  2. 下载 Windows 版 platform-tools\n"
            "  3. 解压到任意目录（如 D:\\adb）\n"
            "  4. 将 platform-tools 路径加入系统 PATH\n\n"
            "安装完成后重新打开 nastools。"
        )

    # ── 设备发现（统一）───────────────────────────────────────────

    def list_devices(self) -> List:
        """列出所有 USB 连接的设备（兼容旧接口）"""
        _, USBDevice, _ = _get_usb_manager()
        return self._get_manager().detect_all()

    def get_first_ready(self):
        """获取第一个就绪的设备"""
        return self._get_manager().get_first_ready()

    # ── USB 拔插监听 ─────────────────────────────────────────────

    def start_watching(
        self,
        on_plugged: Optional[Callable] = None,
        on_unplugged: Optional[Callable] = None,
        interval: float = 2.0,
    ) -> None:
        if self._watch_thread and self._watch_thread.is_alive():
            logger.info("USB 监听已在运行")
            return

        self._stop_watch.clear()

        def watch():
            for d in self._get_manager().detect_all():
                self._last_devices[d.serial] = d.state

            while not self._stop_watch.wait(interval):
                current = {d.serial: d.state for d in self._get_manager().detect_all()}

                for serial, dev in [
                    (s, d)
                    for s, d in [
                        (d.serial, d) for d in self._get_manager().detect_all()
                    ]
                    if s not in self._last_devices
                ]:
                    if on_plugged:
                        try:
                            on_plugged(dev)
                        except Exception as e:
                            logger.error(f"on_plugged 异常: {e}")

                for serial in list(self._last_devices.keys()):
                    if serial not in current and on_unplugged:
                        try:
                            on_unplugged(serial)
                        except Exception as e:
                            logger.error(f"on_unplugged 异常: {e}")

                self._last_devices = current

        self._watch_thread = threading.Thread(target=watch, daemon=True)
        self._watch_thread.start()
        logger.info("USB 拔插监听已启动")

    def stop_watching(self) -> None:
        if self._watch_thread and self._watch_thread.is_alive():
            self._stop_watch.set()
            self._watch_thread.join(timeout=5)
            self._watch_thread = None
            logger.info("USB 监听已停止")

    # ── ADB Shell（兼容旧接口）────────────────────────────────────

    def run_on_device(
        self, serial: Optional[str], command: str, timeout: int = 30
    ) -> tuple[bool, str]:
        if not self.is_adb_installed():
            return False, "ADB 未安装"
        devs = self.list_devices()
        if not devs:
            return False, "未检测到 USB 连接的设备"
        target = serial or devs[0].serial
        try:
            r = subprocess.run(
                ["adb", "-s", target, "shell", "--", command],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return True, r.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, f"命令执行超时（{timeout}s）"
        except Exception as e:
            return False, f"ADB shell 异常: {e}"

    def push_file(
        self, serial: Optional[str], local: str, remote: str
    ) -> tuple[bool, str]:
        import os as _os

        if not _os.path.isfile(local):
            return False, f"本地文件不存在: {local}"
        devs = self.list_devices()
        target = serial or (devs[0].serial if devs else None)
        if not target:
            return False, "未检测到设备"
        try:
            r = subprocess.run(
                ["adb", "-s", target, "push", local, remote],
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            if r.returncode == 0:
                return True, r.stdout.strip() or "推送完成"
            return False, r.stderr.strip() or "推送失败"
        except Exception as e:
            return False, f"推送异常: {e}"

    def pull_file(
        self, serial: Optional[str], remote: str, local: str
    ) -> tuple[bool, str]:
        import os as _os

        _os.makedirs(_os.path.dirname(local) or ".", exist_ok=True)
        devs = self.list_devices()
        target = serial or (devs[0].serial if devs else None)
        if not target:
            return False, "未检测到设备"
        try:
            r = subprocess.run(
                ["adb", "-s", target, "pull", remote, local],
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            if r.returncode == 0:
                return True, r.stdout.strip() or f"已保存到 {local}"
            return False, r.stderr.strip() or "拉取失败"
        except Exception as e:
            return False, f"拉取异常: {e}"

    # ── 诊断 ─────────────────────────────────────────────────────

    def diagnose(self) -> Dict[str, Any]:
        return self._get_manager().diagnose()

    def quick_info(self, serial: Optional[str] = None) -> Dict[str, str]:
        info: Dict[str, str] = {}
        if not self.is_adb_installed():
            return {"error": "ADB 不可用"}
        devs = self.list_devices()
        target = serial or (devs[0].serial if devs else None)
        if not target:
            return {"error": "未检测到设备"}
        for key, cmd in [
            ("hostname", "hostname"),
            ("kernel", "uname -a"),
            ("os", "cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2"),
            ("disk", "df -h / | tail -1"),
            ("uptime", "uptime | sed 's/.*up /up /;s/,.*load.*/ min/g'"),
        ]:
            _, out = self.run_on_device(target, cmd, timeout=5)
            info[key] = out if out else "(无数据)"
        return info
