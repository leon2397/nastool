# -*- coding: utf-8 -*-
"""
nastool/usb/manager.py — V3.0 USB 连接管理器

统一管理四种 USB 连接方式：

  1. ADB (Android Debug Bridge)       — 即插即用，最推荐
  2. USB Gadget (RNDIS 虚拟网卡)        — USB 直连 IP，透明
  3. CDC-ACM (USB 串口)               — 最可靠兜底方案
  4. MTP (Media Transfer Protocol)     — 文件直读，降级方案

连接优先级：ADB > USB Gadget > CDC-ACM > MTP

架构设计：
  - 每种连接方式独立模块，遵循统一接口
  - 支持拔插事件监听（热插拔）
  - 自动选择最优连接方式
  - 支持 ADB 推送 Agent 后自动注册 Relay 远程管理
"""

from __future__ import annotations

import time
import threading
import logging
import os
import re
import socket
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# ── 连接方式枚举 ──────────────────────────────────────────────────


class ConnectionMode(Enum):
    ADB = "adb"
    USB_GADGET = "usb_gadget"
    CDC_ACM = "cdc_acm"
    MTP = "mtp"
    UNKNOWN = "unknown"


# ── 设备信息结构 ──────────────────────────────────────────────────


@dataclass
class USBDevice:
    serial: str
    mode: ConnectionMode
    state: str = "unknown"
    model: str = ""
    manufacturer: str = ""
    product: str = ""
    ip_address: str = ""
    port: int = 22
    transport: str = "usb"
    connection_url: str = ""
    capabilities: List[str] = field(default_factory=list)
    relay_registered: bool = False
    relay_agent_key: str = ""

    @property
    def label(self) -> str:
        name = self.model or self.serial[:16]
        m = {
            ConnectionMode.ADB: "ADB",
            ConnectionMode.USB_GADGET: "USB Gadget",
            ConnectionMode.CDC_ACM: "CDC-ACM",
            ConnectionMode.MTP: "MTP",
            ConnectionMode.UNKNOWN: "未知",
        }.get(self.mode, "")
        return f"{name} [{m}]"

    @property
    def is_ready(self) -> bool:
        return self.state in ("connected", "authorized")

    @property
    def has_shell(self) -> bool:
        return self.mode in (ConnectionMode.ADB, ConnectionMode.USB_GADGET, ConnectionMode.CDC_ACM)

    def __str__(self) -> str:
        return f"USBDevice({self.serial[:12]}, {self.mode.value}, {self.state})"


# ── 抽象连接接口 ─────────────────────────────────────────────────


class USBBackend(ABC):
    @property
    @abstractmethod
    def mode(self) -> ConnectionMode:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def detect_devices(self) -> List[USBDevice]:
        pass

    @abstractmethod
    def run_command(self, device: USBDevice, command: str, timeout: int = 30) -> Tuple[bool, str]:
        pass

    @abstractmethod
    def push_file(self, device: USBDevice, local_path: str, remote_path: str) -> Tuple[bool, str]:
        pass

    @abstractmethod
    def pull_file(self, device: USBDevice, remote_path: str, local_path: str) -> Tuple[bool, str]:
        pass

    def install_agent(
        self,
        device: USBDevice,
        agent_dir: str,
        relay_url: Optional[str] = None,
        agent_key: Optional[str] = None,
    ) -> Tuple[bool, str]:
        import uuid

        ok1, msg1 = self.push_file(device, agent_dir, "/opt/nastools")
        if not ok1:
            return False, f"推送 Agent 目录失败: {msg1}"
        if not agent_key:
            agent_key = f"ak_{uuid.uuid4().hex[:32]}"
        if relay_url:
            config = f"RELAY_URL={relay_url}\nAGENT_KEY={agent_key}\nDEVICE_ID={device.serial}\n"
            ok2, msg2 = self.run_command(
                device, f"cat > /opt/nastools/agent/config.yaml << 'EOF'\n{config}EOF"
            )
            if not ok2:
                return False, f"写入配置失败: {msg2}"
        ok3, msg3 = self.run_command(
            device, "cd /opt/nastools && chmod +x agent.py start.sh && nohup python3 agent.py &"
        )
        if not ok3:
            return False, f"启动 Agent 失败: {msg3}"
        device.relay_registered = bool(relay_url)
        device.relay_agent_key = agent_key
        return True, f"Agent 安装成功 (key={agent_key})"

    def get_device_info(self, device: USBDevice) -> Dict[str, str]:
        info: Dict[str, str] = {}
        if not device.has_shell:
            return {"error": "此连接方式不支持 shell"}
        for key, cmd in [
            ("hostname", "hostname"),
            ("kernel", "uname -a"),
            ("os", "cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2"),
            ("disk", "df -h / | tail -1"),
            ("uptime", "uptime | sed 's/.*up /up /;s/,.*load.*/ min/g'"),
        ]:
            ok, out = self.run_command(device, cmd, timeout=5)
            info[key] = out.strip().splitlines()[0][:60] if ok else "(无数据)"
        return info


# ── ADB 后端 ─────────────────────────────────────────────────────


class ADBBackend(USBBackend):
    def __init__(self):
        self._adb_path: Optional[str] = None
        self._available: Optional[bool] = None

    @property
    def mode(self) -> ConnectionMode:
        return ConnectionMode.ADB

    def _find_adb(self) -> Optional[str]:
        try:
            r = subprocess.run(["adb", "version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return "adb"
        except Exception as e:
            pass
        for path in [
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
            r"C:\Android\platform-tools\adb.exe",
            r"D:\adb\adb.exe",
        ]:
            if os.path.isfile(path):
                return path
        return None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        self._adb_path = self._find_adb()
        self._available = self._adb_path is not None
        return self._available

    def detect_devices(self) -> List[USBDevice]:
        if not self.is_available():
            return []
        try:
            r = subprocess.run(
                [self._adb_path, "devices", "-l"], capture_output=True, text=True, timeout=10
            )
            if r.returncode != 0:
                return []
        except Exception as e:
            return []
        devices = []
        for line in r.stdout.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("List") or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            dev = USBDevice(serial=serial, mode=ConnectionMode.ADB, state=state)
            for p in parts[2:]:
                if p.startswith("model:"):
                    dev.model = p.split(":", 1)[1].replace("_", " ")
                elif p.startswith("product:"):
                    dev.product = p.split(":", 1)[1]
            dev.capabilities = ["shell", "push", "pull", "install_agent"]
            dev.connection_url = f"adb:{serial}"
            if state == "device":
                dev.state = "authorized"
            devices.append(dev)
        return devices

    def run_command(self, device: USBDevice, command: str, timeout: int = 30) -> Tuple[bool, str]:
        if not self.is_available():
            return False, "ADB 不可用"
        try:
            r = subprocess.run(
                [self._adb_path, "-s", device.serial, "shell", "--", command],
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

    def push_file(self, device: USBDevice, local_path: str, remote_path: str) -> Tuple[bool, str]:
        if not os.path.isfile(local_path):
            return False, f"本地文件不存在: {local_path}"
        try:
            r = subprocess.run(
                [self._adb_path, "-s", device.serial, "push", local_path, remote_path],
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

    def pull_file(self, device: USBDevice, remote_path: str, local_path: str) -> Tuple[bool, str]:
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        try:
            r = subprocess.run(
                [self._adb_path, "-s", device.serial, "pull", remote_path, local_path],
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            if r.returncode == 0:
                return True, r.stdout.strip() or f"已保存到 {local_path}"
            return False, r.stderr.strip() or "拉取失败"
        except Exception as e:
            return False, f"拉取异常: {e}"


# ── USB Gadget (RNDIS) 后端 ──────────────────────────────────────


class USBGadgetBackend(USBBackend):
    def __init__(self):
        self._ssh_available: Optional[bool] = None

    @property
    def mode(self) -> ConnectionMode:
        return ConnectionMode.USB_GADGET

    def is_available(self) -> bool:
        if self._ssh_available is not None:
            return self._ssh_available
        try:
            r = subprocess.run(["ssh", "-V"], capture_output=True, text=True, timeout=5)
            self._ssh_available = r.returncode == 0
        except Exception as e:
            self._ssh_available = False
        return self._ssh_available

    def _get_adapter_ip(self, adapter_name: str) -> Optional[str]:
        try:
            r = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    f"(Get-NetIPAddress -InterfaceAlias '{adapter_name}' "
                    "-AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="replace",
            )
            ip = r.stdout.strip().splitlines()[0].strip()
            if re.match(r"\d+\.\d+\.\d+\.\d+", ip):
                return ip
        except Exception as e:
            pass
        return None

    def _check_port(self, host: str, port: int, timeout: float = 2.0) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception as e:
            return False

    def detect_devices(self) -> List[USBDevice]:
        devices = []
        try:
            r = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-NetAdapter | Where-Object {$_.InterfaceDescription -match "
                    "'RNDIS|USB Ethernet|Linux-USB|gadget'} | "
                    "Select-Object Name, InterfaceDescription, Status, MacAddress | "
                    "ConvertTo-Json -Compress",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            if not r.stdout.strip():
                return []
            import json

            adapters = json.loads(r.stdout.strip())
            if isinstance(adapters, dict):
                adapters = [adapters]
        except Exception as e:
            return []

        for adapter in adapters:
            name = adapter.get("Name", "")
            desc = adapter.get("InterfaceDescription", "")
            status = adapter.get("Status", "")
            mac = adapter.get("MacAddress", "")
            if status != "Up":
                continue
            ip = self._get_adapter_ip(name)
            if not ip:
                continue
            if self._check_port(ip, 22):
                devices.append(
                    USBDevice(
                        serial=f"usb_gadget_{mac.replace(':', '')[-8:]}",
                        mode=ConnectionMode.USB_GADGET,
                        state="connected",
                        ip_address=ip,
                        port=22,
                        transport="tcp",
                        connection_url=f"ssh://root@{ip}:22",
                        capabilities=["shell", "push", "pull", "sftp"],
                        manufacturer="USB Gadget",
                        product=desc,
                    )
                )
                logger.info(f"USB Gadget 设备: {name} -> {ip}")
        return devices

    def run_command(self, device: USBDevice, command: str, timeout: int = 30) -> Tuple[bool, str]:
        if not device.ip_address:
            return False, "设备无 IP 地址"
        try:
            r = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    f"ConnectTimeout={min(timeout, 10)}",
                    "-o",
                    "BatchMode=yes",
                    f"root@{device.ip_address}",
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
                encoding="utf-8",
                errors="replace",
            )
            return (r.returncode == 0, r.stdout.strip())
        except subprocess.TimeoutExpired:
            return False, f"命令执行超时（{timeout}s）"
        except Exception as e:
            return False, f"SSH 异常: {e}"

    def push_file(self, device: USBDevice, local_path: str, remote_path: str) -> Tuple[bool, str]:
        if not device.ip_address:
            return False, "设备无 IP 地址"
        try:
            r = subprocess.run(
                [
                    "scp",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "BatchMode=yes",
                    local_path,
                    f"root@{device.ip_address}:{remote_path}",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            if r.returncode == 0:
                return True, f"已推送: {local_path} -> {remote_path}"
            return False, r.stderr.strip() or "SCP 推送失败"
        except Exception as e:
            return False, f"SCP 异常: {e}"

    def pull_file(self, device: USBDevice, remote_path: str, local_path: str) -> Tuple[bool, str]:
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        if not device.ip_address:
            return False, "设备无 IP 地址"
        try:
            r = subprocess.run(
                [
                    "scp",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "BatchMode=yes",
                    f"root@{device.ip_address}:{remote_path}",
                    local_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            if r.returncode == 0:
                return True, f"已拉取: {remote_path} -> {local_path}"
            return False, r.stderr.strip() or "SCP 拉取失败"
        except Exception as e:
            return False, f"SCP 异常: {e}"


# ── CDC-ACM 后端 ─────────────────────────────────────────────────


class CDCACMBackend(USBBackend):
    def __init__(self):
        self._serial_available: Optional[bool] = None

    @property
    def mode(self) -> ConnectionMode:
        return ConnectionMode.CDC_ACM

    def is_available(self) -> bool:
        if self._serial_available is not None:
            return self._serial_available
        try:
            import serial.tools.list_ports  # noqa: F401

            self._serial_available = True
            return True
        except ImportError:
            logger.warning("pyserial 未安装: pip install pyserial")
            self._serial_available = False
            return False

    def detect_devices(self) -> List[USBDevice]:
        if not self.is_available():
            return []
        import serial.tools.list_ports

        devices = []
        for port in serial.tools.list_ports.comports():
            desc = (port.description or "") + (port.hwid or "") + (port.name or "")
            if not any(
                kw in desc.upper()
                for kw in ["USB", "ACM", "SERIAL", "UART", "CH340", "CP210", "FTDI"]
            ):
                continue
            devices.append(
                USBDevice(
                    serial=port.device,
                    mode=ConnectionMode.CDC_ACM,
                    state="connected",
                    model=port.description or "",
                    manufacturer=port.manufacturer or "",
                    product=port.description or "",
                    port=int(port.name.replace("COM", ""))
                    if port.name and port.name.startswith("COM")
                    else 0,
                    transport="serial",
                    connection_url=port.device,
                    capabilities=["shell", "push", "pull"],
                )
            )
            logger.info(f"CDC-ACM 设备: {port.device} - {port.description}")
        return devices

    def run_command(self, device: USBDevice, command: str, timeout: int = 30) -> Tuple[bool, str]:
        try:
            import serial
        except ImportError:
            return False, "pyserial 未安装: pip install pyserial"
        try:
            ser = serial.Serial(
                port=device.serial,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=5,
                write_timeout=5,
            )
        except Exception as e:
            return False, f"无法打开串口 {device.serial}: {e}"
        try:
            ser.flush()
            ser.write((command + "\n").encode("utf-8", errors="replace"))
            lines = []
            start = time.time()
            while time.time() - start < timeout:
                if ser.in_waiting > 0:
                    line = ser.readline().decode("utf-8", errors="replace").strip()
                    if line:
                        lines.append(line)
                    if len(lines) > 1 and line.strip() == command.strip():
                        lines = []
                else:
                    time.sleep(0.1)
            ser.close()
            return True, "\n".join(lines)
        except Exception as e:
            try:
                ser.close()
            except Exception as e:
                pass
            return False, f"串口通信异常: {e}"

    def push_file(self, device: USBDevice, local_path: str, remote_path: str) -> Tuple[bool, str]:
        if not os.path.isfile(local_path):
            return False, f"本地文件不存在: {local_path}"
        size = os.path.getsize(local_path)
        if size < 65536:
            import base64

            with open(local_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("ascii")
            cmds = "\n".join(
                [
                    f"cat > {remote_path}.b64 << 'BASE64EOF'",
                    data,
                    "BASE64EOF",
                    f"base64 -d {remote_path}.b64 > {remote_path}",
                    f"rm {remote_path}.b64",
                    f"chmod 644 {remote_path}",
                ]
            )
            ok, out = self.run_command(device, cmds, timeout=60)
            if ok:
                return True, f"已推送 {size} 字节"
            return False, f"串口推送失败: {out}"
        return False, (f"文件过大（{size} 字节），串口不适合。请使用 ADB push 或 USB Gadget scp")

    def pull_file(self, device: USBDevice, remote_path: str, local_path: str) -> Tuple[bool, str]:
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        ok, data = self.run_command(device, f"base64 {remote_path}", timeout=60)
        if not ok:
            return False, f"串口拉取失败: {data}"
        try:
            import base64

            content = base64.b64decode(data.strip())
            with open(local_path, "wb") as f:
                f.write(content)
            return True, f"已保存 {len(content)} 字节到 {local_path}"
        except Exception as e:
            return False, f"base64 解码失败: {e}"


# ── MTP 后端 ─────────────────────────────────────────────────────


class MTPBackend(USBBackend):
    def __init__(self):
        self._mtp_available: Optional[bool] = None

    @property
    def mode(self) -> ConnectionMode:
        return ConnectionMode.MTP

    def is_available(self) -> bool:
        if self._mtp_available is not None:
            return self._mtp_available
        try:
            import mtp  # noqa: F401

            self._mtp_available = True
        except ImportError:
            logger.warning("python-mtp 未安装: pip install python-mtp")
            self._mtp_available = False
        return self._mtp_available

    def detect_devices(self) -> List[USBDevice]:
        if not self.is_available():
            return []
        devices = []
        try:
            import mtp

            ctx = mtp.MTP()
            ctx.init()
            try:
                devs = ctx.get_devices()
                for dev in devs:
                    info = ctx.get_device_info(dev)
                    devices.append(
                        USBDevice(
                            serial=str(dev),
                            mode=ConnectionMode.MTP,
                            state="connected",
                            model=info.get("model", "MTP Device"),
                            manufacturer=info.get("manufacturer", ""),
                            product=info.get("friendly_name", ""),
                            transport="mtp",
                            connection_url=f"mtp:{dev}",
                            capabilities=["file_list", "file_get", "file_send"],
                        )
                    )
            finally:
                ctx.exit()
        except Exception as e:
            logger.debug(f"MTP 设备检测失败: {e}")
        return devices

    def run_command(self, device: USBDevice, command: str, timeout: int = 30) -> Tuple[bool, str]:
        return False, "MTP 不支持命令执行，请使用 ADB / USB Gadget / CDC-ACM"

    def push_file(self, device: USBDevice, local_path: str, remote_path: str) -> Tuple[bool, str]:
        return False, "MTP push_file 暂未实现（请使用 ADB push）"

    def pull_file(self, device: USBDevice, remote_path: str, local_path: str) -> Tuple[bool, str]:
        return False, "MTP pull_file 暂未实现（请使用 ADB pull）"


# ── 统一管理器 ──────────────────────────────────────────────────


class USBManager:
    def __init__(self):
        self._backends: Dict[ConnectionMode, USBBackend] = {
            ConnectionMode.ADB: ADBBackend(),
            ConnectionMode.USB_GADGET: USBGadgetBackend(),
            ConnectionMode.CDC_ACM: CDCACMBackend(),
            ConnectionMode.MTP: MTPBackend(),
        }
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_watch = threading.Event()
        self._last_devices: Dict[str, USBDevice] = {}

    def detect_all(self) -> List[USBDevice]:
        all_devices: List[USBDevice] = []
        seen: Dict[str, bool] = {}
        for mode in [
            ConnectionMode.ADB,
            ConnectionMode.USB_GADGET,
            ConnectionMode.CDC_ACM,
            ConnectionMode.MTP,
        ]:
            backend = self._backends.get(mode)
            if backend and backend.is_available():
                for dev in backend.detect_devices():
                    if dev.serial not in seen:
                        all_devices.append(dev)
                        seen[dev.serial] = True
        return all_devices

    def get_first_ready(self) -> Optional[USBDevice]:
        devs = self.detect_all()
        for d in devs:
            if d.is_ready:
                return d
        return devs[0] if devs else None

    def get_backend(self, mode: ConnectionMode) -> Optional[USBBackend]:
        return self._backends.get(mode)

    def run_command(self, device: USBDevice, command: str, timeout: int = 30) -> Tuple[bool, str]:
        backend = self._backends.get(device.mode)
        if not backend:
            return False, f"不支持的连接方式: {device.mode}"
        return backend.run_command(device, command, timeout)

    def push_file(self, device: USBDevice, local_path: str, remote_path: str) -> Tuple[bool, str]:
        backend = self._backends.get(device.mode)
        if not backend:
            return False, f"不支持的连接方式: {device.mode}"
        return backend.push_file(device, local_path, remote_path)

    def pull_file(self, device: USBDevice, remote_path: str, local_path: str) -> Tuple[bool, str]:
        backend = self._backends.get(device.mode)
        if not backend:
            return False, f"不支持的连接方式: {device.mode}"
        return backend.pull_file(device, remote_path, local_path)

    def install_agent(
        self,
        device: USBDevice,
        agent_dir: str,
        relay_url: Optional[str] = None,
        agent_key: Optional[str] = None,
    ) -> Tuple[bool, str]:
        backend = self._backends.get(device.mode)
        if not backend:
            return False, f"不支持的连接方式: {device.mode}"
        return backend.install_agent(device, agent_dir, relay_url, agent_key)

    def get_device_info(self, device: USBDevice) -> Dict[str, str]:
        backend = self._backends.get(device.mode)
        if not backend:
            return {"error": f"不支持的连接方式: {device.mode}"}
        return backend.get_device_info(device)

    def start_watching(
        self,
        on_plugged: Optional[Callable[[USBDevice], None]] = None,
        on_unplugged: Optional[Callable[[str], None]] = None,
        interval: float = 2.0,
    ) -> None:
        if self._watch_thread and self._watch_thread.is_alive():
            return
        self._stop_watch.clear()

        def watch():
            for d in self.detect_all():
                self._last_devices[d.serial] = d
            while not self._stop_watch.wait(interval):
                current = {d.serial: d for d in self.detect_all()}
                for serial, dev in current.items():
                    if serial not in self._last_devices and on_plugged:
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

    def diagnose(self) -> Dict[str, Any]:
        report: Dict[str, Any] = {
            "backends": {},
            "devices": [],
            "recommendations": [],
        }
        for mode, backend in self._backends.items():
            b_report: Dict[str, Any] = {
                "available": backend.is_available(),
                "devices": [],
                "suggestions": [],
            }
            devs = backend.detect_devices()
            b_report["devices"] = [
                {"serial": d.serial, "state": d.state, "mode": d.mode.value} for d in devs
            ]
            if not backend.is_available():
                hints = {
                    ConnectionMode.ADB: "ADB 未安装: winget install Google.AndroidPlatformTools",
                    ConnectionMode.USB_GADGET: "USB Gadget 需要设备支持 USB Gadget 模式",
                    ConnectionMode.CDC_ACM: "CDC-ACM 需要 pyserial: pip install pyserial",
                    ConnectionMode.MTP: "MTP 需要 python-mtp: pip install python-mtp",
                }
                b_report["suggestions"].append(hints.get(mode, ""))
            report["backends"][mode.value] = b_report
        report["devices"] = self.detect_all()
        if not report["devices"]:
            report["recommendations"].extend(
                [
                    "1. 检查 USB 线是否插好（建议用数据线）",
                    "2. 确认设备已开启 USB 调试（设置 -> 开发者选项）",
                    "3. 在设备上点击「允许 USB 调试」授权弹窗",
                    "4. 尝试换一根 USB 线（部分线只支持充电）",
                ]
            )
        return report


_manager: Optional[USBManager] = None


def get_manager() -> USBManager:
    global _manager
    if _manager is None:
        _manager = USBManager()
    return _manager


def detect_all() -> List[USBDevice]:
    return get_manager().detect_all()
