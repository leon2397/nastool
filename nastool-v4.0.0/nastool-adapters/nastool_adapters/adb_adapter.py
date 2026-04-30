# -*- coding: utf-8 -*-
"""
ADB USB 直连适配器 -- nastools V3.0-alpha

通过 USB / ADB (Android Debug Bridge) 连接 ARM Linux 设备。
无需 IP/密码，插上 USB 线即可操控。

核心优势：
  [OK] 即插即用，零配置
  [OK] 不依赖网络，无需 SSH
  [OK] 离线可用（无网络环境也能用）
  [OK] Windows 10+ 自带 ADB 驱动（大多数情况）

安装 ADB（用户本地 Windows）：
  winget install Google.AndroidPlatformTools
  或从 https://developer.android.com/studio/releases/platform-tools 下载

架构：
  adb devices                  -> 发现 USB 连接的设备
  adb shell <cmd>              -> 在设备上执行命令
  adb push <local> <remote>    -> 推送文件到设备
  adb pull <remote> <local>    -> 从设备拉取文件
  adb install <apk>            -> 安装 APK（Android 设备）
  adb forward tcp:5037 tcp:5037 -> USB 端口转发（远程调试）
"""

from __future__ import annotations

import subprocess
import re
import os
import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


# ── ADB 可执行文件路径 ─────────────────────────────────────────────


def _find_adb() -> Optional[str]:
    """
    在系统 PATH 中查找 adb.exe

    Returns:
        adb.exe 完整路径，或 None（未找到）
    """
    # 直接调 adb version 测试 PATH 中是否已有
    try:
        r = subprocess.run(["adb", "version"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return "adb"  # PATH 中已有
    except Exception as e:
        pass  # TODO: 添加日志

    # 常见安装路径
    search_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        os.path.expandvars(r"%ProgramFiles%\Android\android-sdk\platform-tools\adb.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Android\android-sdk\platform-tools\adb.exe"),
        r"C:\Android\platform-tools\adb.exe",
        r"C:\adb\adb.exe",
        r"D:\adb\platform-tools\adb.exe",
        r"D:\adb\adb.exe",
    ]
    for path in search_paths:
        if os.path.isfile(path):
            return path

    return None


# ── 数据结构 ───────────────────────────────────────────────────────


class DeviceState(Enum):
    """ADB 设备状态"""

    UNAUTHORIZED = "unauthorized"  # 需要在设备上授权 USB 调试
    OFFLINE = "offline"  # 设备离线
    BOOTLOADER = "bootloader"  # 处于 bootloader 模式
    RECOVERY = "recovery"  # 处于 recovery 模式
    DEVICE = "device"  # 已授权，正常设备
    NODEVICE = "no_device"  # 未检测到任何设备
    UNAVAILABLE = "unavailable"  # ADB 服务不可用


@dataclass
class ADBDevice:
    """ADB 连接的设备信息"""

    serial: str  # 设备序列号（adb devices 输出第一列）
    state: DeviceState  # 设备状态
    product: str = ""  # 产品名
    model: str = ""  # 型号（从设备读取）
    device_path: str = ""  # 设备路径
    transport_id: str = ""  # 传输 ID

    @property
    def is_ready(self) -> bool:
        """设备是否可用（已授权且在线）"""
        return self.state == DeviceState.DEVICE

    @property
    def display_name(self) -> str:
        """人类可读的设备名"""
        return self.model or self.product or self.serial[:12]

    def __str__(self) -> str:
        return f"ADBDevice({self.serial[:16]}, {self.state.value})"


# ── ADB 客户端 ─────────────────────────────────────────────────────


class ADBClient:
    """
    ADB 客户端封装

    通过 subprocess 调用 adb 命令与 USB 连接的设备通信。
    所有方法线程安全（每次调用独立 subprocess）。

    用法示例：
        client = ADBClient()
        if not client.is_available():
            print("请安装 ADB: winget install Google.AndroidPlatformTools")

        devices = client.list_devices()
        if not devices:
            print("未检测到 USB 连接的设备")
            return

        dev = devices[0]
        # 执行命令
        result = client.shell(dev.serial, "uname -a")
        print(result)

        # 推送文件
        client.push(dev.serial, "D:/setup.sh", "/tmp/setup.sh")

        # 拉取文件
        client.pull(dev.serial, "/tmp/report.json", "D:/report.json")
    """

    def __init__(self, adb_path: Optional[str] = None):
        """
        初始化 ADB 客户端

        Args:
            adb_path: adb.exe 路径，默认自动从 PATH / 常见路径查找
        """
        self._adb = adb_path or _find_adb()
        self._available: Optional[bool] = None  # 缓存可用性检测结果

    # ── 基础可用性 ────────────────────────────────────────────────

    def is_available(self) -> bool:
        """
        ADB 是否可用（adb.exe 存在且可执行）

        Returns:
            True 如果 ADB 可用
        """
        if self._available is not None:
            return self._available

        if self._adb is None:
            self._available = False
            return False

        try:
            r = subprocess.run([self._adb, "version"], capture_output=True, text=True, timeout=5)
            self._available = r.returncode == 0
        except Exception as e:
            self._available = False

        return self._available

    def version_info(self) -> str:
        """获取 ADB 版本信息"""
        if not self.is_available():
            return "ADB 不可用"
        try:
            r = subprocess.run([self._adb, "version"], capture_output=True, text=True, timeout=5)
            return r.stdout.strip()
        except Exception as e:
            return f"ADB 版本读取失败: {e}"

    # ── 设备发现 ───────────────────────────────────────────────────

    def list_devices(self, refresh: bool = False) -> List[ADBDevice]:
        """
        列出所有通过 USB 连接的 ADB 设备

        等效于命令: adb devices

        Args:
            refresh: 是否强制刷新（执行 adb kill-server 再 start-server）

        Returns:
            设备列表（可能为空）
        """
        if not self.is_available():
            return []

        # 可选：重启 ADB 服务以刷新设备列表
        if refresh:
            self._restart_server()

        try:
            r = subprocess.run(
                [self._adb, "devices", "-l"], capture_output=True, text=True, timeout=10
            )
            if r.returncode != 0:
                logger.warning(f"adb devices 失败: {r.stderr.strip()}")
                return []
        except Exception as e:
            logger.error(f"adb devices 执行异常: {e}")
            return []

        devices = []
        for line in r.stdout.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("List") or line.startswith("*"):
                continue

            # 格式: serialno state product:xxx model:xxx device:xxx transport:xxx
            parts = line.split()
            if len(parts) < 2:
                continue

            serial = parts[0]
            state_str = parts[1]
            state = self._parse_state(state_str)

            device = ADBDevice(serial=serial, state=state)

            # 解析 -l 输出的额外信息
            for part in parts[2:]:
                if part.startswith("product:"):
                    device.product = part.split(":", 1)[1]
                elif part.startswith("model:"):
                    device.model = part.split(":", 1)[1].replace("_", " ")
                elif part.startswith("device:"):
                    device.device_path = part.split(":", 1)[1]
                elif part.startswith("transport:"):
                    device.transport_id = part.split(":", 1)[1]

            devices.append(device)

        return devices

    def get_device(self, serial: Optional[str] = None) -> Optional[ADBDevice]:
        """
        获取指定序列号的设备（只有一个设备时 serial 可为 None）

        Args:
            serial: 设备序列号，默认取第一个就绪的设备

        Returns:
            设备对象，或 None
        """
        devices = self.list_devices()
        if not devices:
            return None

        if serial:
            for dev in devices:
                if dev.serial == serial:
                    return dev
            return None

        # 无指定序列号 -> 取第一个就绪的设备
        for dev in devices:
            if dev.is_ready:
                return dev
        return devices[0]  # 返回第一个（即使未就绪，供诊断用）

    # ── ADB 服务器管理 ─────────────────────────────────────────────

    def _restart_server(self) -> bool:
        """重启 ADB 服务器（刷新设备列表）"""
        try:
            subprocess.run([self._adb, "kill-server"], capture_output=True, timeout=5)
            subprocess.run([self._adb, "start-server"], capture_output=True, timeout=10)
            return True
        except Exception as e:
            logger.warning(f"ADB server restart failed: {e}")
            return False

    def start_server(self) -> bool:
        """启动 ADB 服务器"""
        try:
            r = subprocess.run(
                [self._adb, "start-server"], capture_output=True, text=True, timeout=10
            )
            return r.returncode == 0
        except Exception as e:
            return False

    def kill_server(self) -> bool:
        """关闭 ADB 服务器"""
        try:
            subprocess.run([self._adb, "kill-server"], capture_output=True, timeout=5)
            return True
        except Exception as e:
            return False

    # ── Shell 命令 ─────────────────────────────────────────────────

    def shell(self, serial: Optional[str], command: str, timeout: int = 30) -> Tuple[bool, str]:
        """
        在设备上执行 shell 命令

        等效于: adb -s <serial> shell <command>

        Args:
            serial: 设备序列号
            command: 要执行的命令
            timeout: 超时秒数

        Returns:
            (成功标志, 输出内容)
        """
        if not self.is_available():
            return False, "ADB 不可用"

        devices = self.list_devices()
        if not devices:
            return False, "未检测到 USB 连接的设备（请检查 USB 线是否插好）"

        target_serial = serial or (devices[0].serial if devices else None)
        if not target_serial:
            return False, "未指定设备序列号且无可用设备"

        cmd_list = [self._adb, "-s", target_serial, "shell", "--", command]

        try:
            r = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            # adb shell 的 stderr 通常为空，真实错误在 stdout 里
            output = r.stdout.strip()
            # 某些情况下退出码非0但有有效输出（如 grep 无匹配）
            return True, output
        except subprocess.TimeoutExpired:
            return False, f"命令执行超时（{timeout}s）"
        except Exception as e:
            return False, f"ADB shell 执行异常: {e}"

    def shell_interactive(self, serial: Optional[str], command: str) -> subprocess.Popen:
        """
        启动交互式 shell（用于需要 TTY 的命令，如 top, htop, vim）

        返回 Popen 对象，调用方负责 wait() 或读取输出。
        """
        if not self.is_available():
            raise RuntimeError("ADB 不可用")

        devices = self.list_devices()
        target_serial = serial or (devices[0].serial if devices else None)
        if not target_serial:
            raise RuntimeError("未检测到 USB 连接的设备")

        return subprocess.Popen(
            [self._adb, "-s", target_serial, "shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    # ── 文件传输 ───────────────────────────────────────────────────

    def push(
        self, serial: Optional[str], local_path: str, remote_path: str, progress: bool = False
    ) -> Tuple[bool, str]:
        """
        推送本地文件到设备

        等效于: adb push <local> <remote>

        Args:
            serial: 设备序列号
            local_path: 本地文件路径（绝对路径）
            remote_path: 设备上的目标路径
            progress: 是否显示进度（subprocess 会实时输出）

        Returns:
            (成功标志, 信息)
        """
        if not os.path.isfile(local_path):
            return False, f"本地文件不存在: {local_path}"

        devices = self.list_devices()
        target_serial = serial or (devices[0].serial if devices else None)
        if not target_serial:
            return False, "未检测到 USB 连接的设备"

        cmd_list = [self._adb, "-s", target_serial, "push", local_path, remote_path]

        try:
            r = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            if r.returncode == 0:
                # adb push 输出类似: [100%] /path/to/file
                return True, r.stdout.strip() or "推送完成"
            else:
                return False, r.stderr.strip() or "推送失败"
        except subprocess.TimeoutExpired:
            return False, "推送超时（文件过大或 USB 连接不稳定）"
        except Exception as e:
            return False, f"推送异常: {e}"

    def pull(
        self, serial: Optional[str], remote_path: str, local_path: str, progress: bool = False
    ) -> Tuple[bool, str]:
        """
        从设备拉取文件到本地

        等效于: adb pull <remote> <local>

        Args:
            serial: 设备序列号
            remote_path: 设备上的源文件路径
            local_path: 本地保存路径
            progress: 是否显示进度

        Returns:
            (成功标志, 信息)
        """
        devices = self.list_devices()
        target_serial = serial or (devices[0].serial if devices else None)
        if not target_serial:
            return False, "未检测到 USB 连接的设备"

        # 确保本地目录存在
        local_dir = os.path.dirname(local_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)

        cmd_list = [self._adb, "-s", target_serial, "pull", remote_path, local_path]

        try:
            r = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            if r.returncode == 0:
                return True, r.stdout.strip() or f"已保存到 {local_path}"
            else:
                return False, r.stderr.strip() or "拉取失败"
        except subprocess.TimeoutExpired:
            return False, "拉取超时"
        except Exception as e:
            return False, f"拉取异常: {e}"

    # ── 安装 Agent ─────────────────────────────────────────────────

    def install_agent(self, serial: Optional[str], agent_zip_path: str) -> Tuple[bool, str]:
        """
        通过 ADB 一键安装 nastool Agent 到设备

        流程：
        1. 推送 agent 包到 /tmp/
        2. 解压到 /opt/nastools/（ARM Linux）
        3. 设置可执行权限
        4. 验证安装

        Args:
            serial: 设备序列号
            agent_zip_path: 本地 agent zip 包路径

        Returns:
            (成功标志, 信息)
        """
        if not os.path.isfile(agent_zip_path):
            return False, f"Agent 包不存在: {agent_zip_path}"

        devices = self.list_devices()
        target_serial = serial or (devices[0].serial if devices else None)
        if not target_serial:
            return False, "未检测到 USB 连接的设备"

        steps = []
        ok = True

        # Step 1: 推送文件
        ok1, msg1 = self.push(
            serial=target_serial, local_path=agent_zip_path, remote_path="/tmp/nastools_agent.zip"
        )
        steps.append(msg1)
        if not ok1:
            return False, f"推送 Agent 包失败: {msg1}"

        # Step 2: 解压到 /opt/nastools
        ok2, msg2 = self.shell(
            serial=target_serial,
            command="mkdir -p /opt/nastools && "
            "cd /opt/nastools && "
            "unzip -o /tmp/nastools_agent.zip && "
            "rm /tmp/nastools_agent.zip && "
            "chmod +x *.sh *.py 2>/dev/null; echo DONE",
        )
        steps.append(msg2)
        if not ok2 or "DONE" not in msg2:
            return False, f"解压 Agent 包失败: {msg2}"

        # Step 3: 验证
        ok3, msg3 = self.shell(
            serial=target_serial, command="test -f /opt/nastools/agent.py && echo OK || echo FAIL"
        )
        steps.append(msg3)
        if "OK" not in msg3:
            return False, f"Agent 安装验证失败: {msg3}"

        return True, "\n".join(steps)

    # ── 诊断与发现 ─────────────────────────────────────────────────

    def diagnose_connection(self, serial: Optional[str] = None) -> Dict[str, Any]:
        """
        完整诊断 USB/ADB 连接问题

        返回详细的诊断报告，包含所有检查点和解决方案建议。
        """
        result = {
            "adb_available": self.is_available(),
            "adb_path": self._adb,
            "adb_version": self.version_info() if self.is_available() else None,
            "devices": [],
            "issues": [],
            "suggestions": [],
        }

        if not self.is_available():
            result["issues"].append("ADB 不可用（adb.exe 未找到）")
            result["suggestions"].append(
                "请安装 Android Platform Tools:\n"
                "  winget install Google.AndroidPlatformTools\n"
                "  或从 https://developer.android.com/studio/releases/platform-tools 下载"
            )
            return result

        # 检查设备列表
        devices = self.list_devices()
        result["devices"] = [
            {
                "serial": d.serial,
                "state": d.state.value,
                "model": d.model,
                "product": d.product,
                "is_ready": d.is_ready,
            }
            for d in devices
        ]

        if not devices:
            result["issues"].append("未检测到 USB 连接的设备")
            result["suggestions"].extend(
                [
                    "1. 检查 USB 线是否插好（建议使用数据线，不是充电线）",
                    "2. 部分设备需要开启 USB 调试：设置 -> 开发者选项 -> USB 调试",
                    "3. 尝试换一根 USB 线或 USB 接口",
                    "4. 在设备上授权此电脑的 USB 调试",
                ]
            )
        else:
            for dev in devices:
                if dev.state == DeviceState.UNAUTHORIZED:
                    result["issues"].append(f"设备 {dev.display_name} 未授权")
                    result["suggestions"].append(
                        f"请在设备 [{dev.display_name}] 上点击「允许 USB 调试」弹窗"
                    )
                elif dev.state == DeviceState.OFFLINE:
                    result["issues"].append(f"设备 {dev.display_name} 离线")
                    result["suggestions"].append("尝试: adb kill-server && adb start-server")
                elif dev.state == DeviceState.BOOTLOADER:
                    result["issues"].append(f"设备处于 Bootloader 模式: {dev.display_name}")
                    result["suggestions"].append(
                        "设备处于 Bootloader，请先刷入系统或重启到正常模式"
                    )
                elif dev.is_ready:
                    pass  # 就绪，无问题

        return result

    def get_device_info(self, serial: Optional[str] = None) -> Dict[str, str]:
        """
        获取设备的系统信息（通过 ADB shell）

        读取: hostname, uname, /proc/cpuinfo, /proc/meminfo
        """
        info: Dict[str, str] = {}
        if not self.is_available():
            return {"error": "ADB 不可用"}

        devices = self.list_devices()
        target_serial = serial or (devices[0].serial if devices else None)
        if not target_serial:
            return {"error": "未检测到设备"}

        cmds = {
            "hostname": "hostname",
            "kernel": "uname -a",
            "os_version": "cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2",
            "cpuinfo": "cat /proc/cpuinfo | head -20",
            "meminfo": "cat /proc/meminfo | head -5",
            "disk_usage": "df -h / | tail -1",
            "uptime": "uptime",
        }

        for key, cmd in cmds.items():
            _, output = self.shell(serial=target_serial, command=cmd, timeout=5)
            info[key] = output if output else "(无数据)"

        return info

    # ── 内部辅助 ────────────────────────────────────────────────────

    @staticmethod
    def _parse_state(state_str: str) -> DeviceState:
        """解析 adb devices 输出中的设备状态字符串"""
        state_map = {
            "unauthorized": DeviceState.UNAUTHORIZED,
            "offline": DeviceState.OFFLINE,
            "bootloader": DeviceState.BOOTLOADER,
            "recovery": DeviceState.RECOVERY,
            "device": DeviceState.DEVICE,
            "no device": DeviceState.NODEVICE,
            "unavailable": DeviceState.UNAVAILABLE,
        }
        return state_map.get(state_str.lower(), DeviceState.NODEVICE)

    def __repr__(self) -> str:
        return f"ADBClient(adb={self._adb}, available={self.is_available()})"


# ── 全局单例（懒加载）──────────────────────────────────────────────

_client: Optional[ADBClient] = None


def get_client() -> ADBClient:
    """获取全局 ADB 客户端单例"""
    global _client
    if _client is None:
        _client = ADBClient()
    return _client


# ── 快捷函数 ───────────────────────────────────────────────────────


def list_usb_devices() -> List[ADBDevice]:
    """快捷函数：列出所有 USB 连接的设备"""
    return get_client().list_devices()


def is_adb_available() -> bool:
    """快捷函数：检查 ADB 是否可用"""
    return get_client().is_available()


def diagnose() -> Dict[str, Any]:
    """快捷函数：诊断 ADB 连接问题"""
    return get_client().diagnose_connection()
