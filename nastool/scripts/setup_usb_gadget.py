from typing import Dict, Optional, Tuple
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_usb_gadget.py — USB Gadget 一键启用脚本

V3.0-beta

在 ARM Linux 设备上自动启用 USB Gadget 虚拟网卡模式，
让 PC 通过 USB 线直接用 IP 访问设备，无需网络配置。

适用设备：
  - Jetson Nano / Xavier NX / Orin（NVIDIA L4T）
  - RK3588 / RK3399（Rockchip）
  - 树莓派 4（官方 USB Gadget 模式）
  - 其他支持 USB Gadget 的 ARM 设备

工作流程：
  1. 检测 USB 控制器类型
  2. 自动选择 gadget 驱动（g_ether / g_rndis）
  3. 加载 gadget 模块并配置
  4. 分配 USB IP 地址
  5. 可选：配置 NAT 共享互联网

用法：
  # 自动检测并启用
  sudo python3 setup_usb_gadget.py

  # 指定驱动
  sudo python3 setup_usb_gadget.py --driver rndis

  # 查看状态
  sudo python3 setup_usb_gadget.py --status

  # 禁用
  sudo python3 setup_usb_gadget.py --disable

依赖：
  - Python 3.6+
  - root 权限（sudo）
  - 内核支持 USB Gadget（CONFIG_USB_GADGET）
"""

import sys
import os
import re
import json
import shutil
import argparse
import subprocess
import time
from pathlib import Path

# ── 全局路径常量 ──────────────────────────────────────────────────

USB_GADGET_PATH = "/sys/kernel/config/usb_gadget"
USB_GADGET_NAME = "nastools"
USB_IP_HOST = "192.168.58.1"  # PC 端 USB 网卡 IP（Windows 默认）
USB_IP_DEVICE = "192.168.58.2"  # 设备端 USB Gadget IP
USB_NETMASK = "255.255.255.0"
USB_GADGET_IFACE = "usb0"


# ── Shell 工具 ──────────────────────────────────────────────────


def is_root() -> bool:
    return os.geteuid() == 0


def run(cmd: str, timeout: int = 30, check: bool = False) -> Tuple[int, str, str]:
    """执行 shell 命令"""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def run_ok(cmd: str, timeout: int = 30) -> Tuple[bool, str]:
    """执行命令，成功返回 (True, stdout)"""
    code, out, err = run(cmd, timeout)
    return code == 0, (out or err)


def is_file(path: str) -> bool:
    return os.path.isfile(path)


def is_dir(path: str) -> bool:
    return os.path.isdir(path)


def write_file(path: str, content: str) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"  [错误] 写入 {path} 失败: {e}")
        return False


def read_file(path: str, default: str = "") -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except Exception as e:
        return default


# ── 设备检测 ────────────────────────────────────────────────────


class DeviceInfo:
    """检测到的设备信息"""

    def __init__(self):
        self.platform = ""
        self.soc_family = ""  # nvidia / rockchip / rpi / other
        self.kernel_version = ""
        self.usb_controller = ""
        self.has_gadget = False
        self.has_ether = False
        self.has_rndis = False
        self.has_dwc2 = False
        self.has_dwc3 = False
        self.current_gadget: Optional[str] = None
        self.usb_connected = False
        self.gadget_iface_state = ""
        self.extra_info: Dict[str, str] = {}

    def summary(self) -> str:
        sos = {
            "nvidia": "NVIDIA Jetson (L4T)",
            "rockchip": "Rockchip RK3588/RK3399",
            "rpi": "Raspberry Pi",
            "other": "通用 ARM 设备",
            "": "未知",
        }
        return sos.get(self.soc_family, "未知设备")


def detect_device() -> DeviceInfo:
    """
    全面检测设备信息

    检测项：
      - 平台类型（Jetson / RK3588 / 树莓派 / 通用）
      - USB 控制器类型（DWC2 / DWC3 / etc）
      - USB Gadget 支持情况（g_ether / g_rndis 模块）
      - 当前 USB 连接状态
      - 已启用的 gadget（若有）
    """
    info = DeviceInfo()

    # 1. 内核版本
    _, kernel, _ = run("uname -r")
    info.kernel_version = kernel

    # 2. SOC 家族检测
    soc_info = _detect_soc_family()
    info.soc_family = soc_info["family"]
    info.platform = soc_info.get("model", "")
    info.extra_info = soc_info

    # 3. USB 控制器检测
    info.usb_controller = _detect_usb_controller()

    # 4. USB Gadget 内核支持检测
    info.has_gadget = is_dir(USB_GADGET_PATH)

    # 检查 configfs USB gadget 是否已配置
    if info.has_gadget:
        gadgets = []
        try:
            for name in os.listdir(USB_GADGET_PATH):
                gadget_path = os.path.join(USB_GADGET_PATH, name)
                if os.path.isdir(gadget_path):
                    gadgets.append(name)
        except Exception as e:
            pass
        if gadgets:
            info.current_gadget = gadgets[0]

    # 5. 可用 Gadget 驱动检测
    info.has_ether = _module_loaded("g_ether") or _module_exists("g_ether")
    info.has_rndis = _module_loaded("g_rndis") or _module_exists("g_rndis")
    info.has_dwc2 = _module_exists("dwc2")
    info.has_dwc3 = _module_exists("dwc3")

    # 6. USB 连接状态（dmesg 最新 USB 连接事件）
    _, dmesg_usb, _ = run("dmesg | grep -i 'usb.*connect\\| gadget' | tail -5")
    info.usb_connected = bool(dmesg_usb)

    # 7. USB Gadget 网卡状态（若有）
    if os.path.exists(f"/sys/class/net/{USB_GADGET_IFACE}"):
        state = read_file(f"/sys/class/net/{USB_GADGET_IFACE}/operstate", "?")
        info.gadget_iface_state = state

    return info


def _detect_soc_family() -> Dict[str, str]:
    """检测 SOC 家族"""
    result: Dict[str, str] = {"family": "", "model": ""}

    # NVIDIA Jetson（L4T）
    if os.path.exists("/etc/nv_tegra_release"):
        result["family"] = "nvidia"
        # 读取具体型号
        content = read_file("/etc/nv_tegra_release", "")
        if "Jetson Nano" in content:
            result["model"] = "Jetson Nano"
        elif "Jetson Xavier" in content:
            result["model"] = "Jetson Xavier NX/AGX"
        elif "Orin" in content:
            result["model"] = "Jetson Orin"
        else:
            result["model"] = "NVIDIA Jetson (L4T)"
        return result

    # Rockchip RK3588 / RK3399
    if os.path.exists("/proc/device-tree/compatible"):
        compat = read_file("/proc/device-tree/compatible", "")
        if "rk3588" in compat:
            result["family"] = "rockchip"
            result["model"] = "Rockchip RK3588"
            return result
        if "rk3399" in compat:
            result["family"] = "rockchip"
            result["model"] = "Rockchip RK3399"
            return result
        if "rockchip" in compat:
            result["family"] = "rockchip"
            result["model"] = "Rockchip"
            return result

    # Raspberry Pi
    if os.path.exists("/sys/firmware/devicetree/base/model"):
        model = read_file("/sys/firmware/devicetree/base/model", "")
        if "Raspberry Pi" in model or "rpi" in model.lower():
            result["family"] = "rpi"
            result["model"] = model
            return result

    # FriendlyARM / NanoPi / etc.
    if os.path.exists("/etc/friendlyarm-version"):
        result["family"] = "friendlyarm"
        result["model"] = read_file("/etc/friendlyarm-version", "FriendlyARM")
        return result

    # Orange Pi / etc.
    if os.path.exists("/proc/device-tree/model"):
        model = read_file("/proc/device-tree/model", "")
        if model:
            result["model"] = model
            result["family"] = "other"
            return result

    # /proc/cpuinfo 回退
    _, cpuinfo, _ = run("cat /proc/cpuinfo")
    if "nvidia" in cpuinfo.lower():
        result["family"] = "nvidia"
        result["model"] = "NVIDIA SoC"
    elif "rockchip" in cpuinfo.lower():
        result["family"] = "rockchip"
        result["model"] = "Rockchip SoC"

    return result


def _detect_usb_controller() -> str:
    """检测 USB 控制器类型"""
    # L4T Jetson：使用 DWC3 USB 控制器
    if os.path.exists("/sys/bus/platform/devices/3610000.xhci"):
        return "DWC3 (NVIDIA)"
    if os.path.exists("/sys/bus/platform/devices/fe980000.usb"):
        return "DWC3 (Rockchip)"
    # 通用检测
    if os.path.exists("/sys/bus/usb"):
        return "EHCI/OHCI"
    # 搜索 xhci-hcd
    _, xhci, _ = run("lsmod | grep xhci")
    if "xhci" in xhci:
        return "XHCI"
    return "Unknown"


def _module_loaded(name: str) -> bool:
    _, out, _ = run(f"lsmod | grep '^{name}'")
    return bool(out)


def _module_exists(name: str) -> bool:
    # 检查内核模块是否可用
    return os.path.exists(f"/lib/modules/{os.uname().release}/kernel/drivers/usb/gadget/{name}.ko")


# ── USB Gadget 配置 ──────────────────────────────────────────────


class USBGadgetSetup:
    """
    USB Gadget 配置器

    支持两种驱动：
      - g_ether: 最广泛支持（Linux/macOS/Windows）
      - g_rndis: Windows 原生支持（推荐），速度更快
    """

    def __init__(self, driver: str = "rndis"):
        self.driver = driver  # "rndis" 或 "ether"
        self.gadget_name = USB_GADGET_NAME
        self.gadget_path = os.path.join(USB_GADGET_PATH, self.gadget_name)
        self.ready = False

    def is_supported(self) -> bool:
        """驱动是否支持"""
        return shutil.which("modprobe") is not None

    def enable(self, info: DeviceInfo) -> Tuple[bool, str]:
        """
        启用 USB Gadget

        完整流程：
          1. 加载内核模块
          2. 创建 configfs gadget
          3. 配置 USB 函数（RNDIS / ECM）
          4. 绑定到 USB 控制器
          5. 配置 IP 地址
          6. 验证连接
        """
        print(f"\n{'=' * 50}")
        print(f"  USB Gadget 启用中（驱动: {self.driver}）")
        print(f"{'=' * 50}\n")

        # Step 1: 检查 root 权限
        if not is_root():
            return False, "需要 root 权限，请用 sudo 运行"

        # Step 2: 检测内核支持
        if not info.has_gadget:
            ok, msg = self._check_kernel_support()
            if not ok:
                return False, msg

        # Step 3: 加载内核模块
        ok, msg = self._load_modules(info)
        if not ok:
            return False, msg

        # Step 4: 创建 Gadget
        ok, msg = self._create_gadget(info)
        if not ok:
            return False, msg

        # Step 5: 分配 IP
        ok, msg = self._configure_ip()
        if not ok:
            return False, msg

        self.ready = True
        print(f"\n[成功] USB Gadget 已启用！")
        print(f"\n设备端 IP: {USB_IP_DEVICE}")
        print(f"PC 端 IP:  {USB_IP_HOST}（在 PC 的 USB RNDIS 网卡上设置）")
        print(f"测试连接:  ping {USB_IP_HOST}")
        print(f"\n在 PC 上访问设备: ssh root@{USB_IP_DEVICE}")
        return True, "USB Gadget 已启用"

    def _check_kernel_support(self) -> Tuple[bool, str]:
        """检查内核是否支持 USB Gadget"""
        print("[检查] 内核 USB Gadget 支持...")
        if is_dir("/sys/kernel/config/usb_gadget"):
            return True, "configfs USB Gadget 支持正常"
        # 尝试加载
        ok, out = run_ok("modprobe libcomposite")
        if ok:
            if is_dir("/sys/kernel/config/usb_gadget"):
                return True, "libcomposite 模块已加载"
        return False, (
            "内核不支持 USB Gadget (CONFIG_USB_GADGET)。"
            "请确认内核配置:\n"
            "  CONFIG_USB_GADGET=y\n"
            "  CONFIG_USB_CONFIGFS=y\n"
            "  CONFIG_USB_LIBCOMPOSITE=y"
        )

    def _load_modules(self, info: DeviceInfo) -> Tuple[bool, str]:
        """加载所需内核模块"""
        print("[加载] 加载内核模块...")

        modules = ["libcomposite"]

        # Jetson 特殊处理
        if info.soc_family == "nvidia":
            # L4T 通常已经内置 gadget 支持，检查是否有专用模块
            if is_file("/sys/module/dwc3"):
                print("  [跳过] DWC3 模块已加载（Jetson 内置）")
            else:
                modules.append("dwc3")
                modules.append("dwc3-of-simple")

        # RK3588
        if info.soc_family == "rockchip":
            modules.extend(["dwc3", "rockchip_usb2"])

        # 树莓派
        if info.soc_family == "rpi":
            # 树莓派 Zero 需要 dtoverlay=dwc2
            if is_file("/boot/config.txt"):
                content = read_file("/boot/config.txt", "")
                if "dwc2" not in content:
                    print("  [提示] 建议在 /boot/config.txt 中添加: dtoverlay=dwc2")
                else:
                    print("  [OK] DWC2 已启用（config.txt）")
            modules.append("dwc2")

        for mod in modules:
            ok, out = run_ok(f"modprobe {mod}")
            if ok:
                print(f"  [OK] {mod} 已加载")
            else:
                print(f"  [跳过] {mod} 加载失败（可能已内置或不存在）")

        # 确保 gadgetfs 可用
        ok, _ = run_ok("mount | grep configfs")
        if not ok:
            ok, _ = run_ok("mount -t configfs none /sys/kernel/config")
            if ok:
                print("  [OK] configfs 已挂载")
            else:
                return False, "无法挂载 configfs"

        return True, "内核模块加载完成"

    def _create_gadget(self, info: DeviceInfo) -> Tuple[bool, str]:
        """创建 USB Gadget"""
        print("[配置] 创建 USB Gadget...")

        # 清理已存在的 gadget
        if is_dir(self.gadget_path):
            ok, _ = run_ok(f"rmdir {self.gadget_path}")
            if not ok:
                return False, f"无法清理旧 gadget（{self.gadget_path}），可能被占用"

        # 创建 gadget 目录
        try:
            os.makedirs(self.gadget_path, exist_ok=True)
        except Exception as e:
            return False, f"无法创建 gadget 目录: {e}"

        # 生成随机 ID（VID/PID）
        id_vendor = "0x1d6b"  # Linux Foundation
        id_product = "0x0104"  # Multifunction Composite Gadget

        # 写入基本属性
        write_file(os.path.join(self.gadget_path, "idVendor"), id_vendor)
        write_file(os.path.join(self.gadget_path, "idProduct"), id_product)
        write_file(os.path.join(self.gadget_path, "bcdDevice"), "0x0100")
        write_file(os.path.join(self.gadget_path, "bcdUSB"), "0x0200")

        # 配置字符串（可选，让 PC 看到设备名）
        strings_path = os.path.join(self.gadget_path, "strings", "0x409")
        os.makedirs(strings_path, exist_ok=True)
        write_file(
            os.path.join(strings_path, "serialnumber"),
            f"nastools-{USB_GADGET_NAME}-{int(time.time())}",
        )
        write_file(os.path.join(strings_path, "manufacturer"), "nastools")
        write_file(os.path.join(strings_path, "product"), f"USB Gadget ({self.driver.upper()})")

        # 创建配置
        configs_path = os.path.join(self.gadget_path, "configs", "c.1")
        os.makedirs(configs_path, exist_ok=True)
        strings_c = os.path.join(configs_path, "strings", "0x409")
        os.makedirs(strings_c, exist_ok=True)
        write_file(os.path.join(strings_c, "configuration"), "Config 1")

        # 创建 USB 函数（RNDIS 或 ECM）
        func_type = "rndis" if self.driver == "rndis" else "ecm"
        func_path = os.path.join(self.gadget_path, "functions", f"{func_type}.0")
        os.makedirs(func_path, exist_ok=True)

        # RNDIS 特殊配置（Windows 需要）
        if self.driver == "rndis":
            write_file(os.path.join(func_path, "host_addr"), "de:ad:be:ef:00:01")
            write_file(os.path.join(func_path, "device_addr"), "de:ad:be:ef:00:02")

        # 将函数链接到配置
        func_link = os.path.join(configs_path, func_type)
        try:
            if os.path.islink(func_link):
                os.unlink(func_link)
            os.symlink(func_path, func_link)
        except Exception as e:
            return False, f"无法链接函数到配置: {e}"

        # 绑定到 USB 控制器
        # 查找可用的 USB UDC 控制器
        udc_path = "/sys/class/udc"
        if os.path.exists(udc_path):
            controllers = os.listdir(udc_path)
            if controllers:
                udc_name = controllers[0]
                print(f"  [绑定] UDC: {udc_name}")
                write_file(os.path.join(self.gadget_path, "UDC"), udc_name)
            else:
                return False, (
                    "未找到 USB UDC 控制器。请确保 USB Gadget USB Gadget 已连接到 PC（USB 线插上）"
                )
        else:
            return False, "未找到 /sys/class/udc，USB Gadget 不支持此设备"

        print(f"  [OK] Gadget 已创建: {self.gadget_name}")
        return True, "Gadget 创建成功"

    def _configure_ip(self) -> Tuple[bool, str]:
        """配置 USB Gadget 网卡 IP"""
        print(f"[IP] 配置 {USB_GADGET_IFACE} -> {USB_IP_DEVICE}")

        # 分配 IP
        ok, out = run_ok(f"ip addr add {USB_IP_DEVICE}/24 dev {USB_GADGET_IFACE} 2>/dev/null")
        if not ok:
            # IP 可能已存在，尝试设置
            pass

        # 启用网卡
        ok, out = run_ok(f"ip link set {USB_GADGET_IFACE} up")
        if not ok:
            return False, f"无法启用 {USB_GADGET_IFACE}，可能未创建成功"

        # 显示 IP
        _, ip_out, _ = run(f"ip addr show {USB_GADGET_IFACE}")
        print(f"  [OK] {USB_GADGET_IFACE} IP 已配置")

        # 可选：启用 NAT 共享互联网
        self._setup_nat()

        return True, "IP 配置完成"

    def _setup_nat(self) -> None:
        """可选：配置 NAT 互联网共享"""
        print("[NAT] 配置互联网共享（可选）...")

        # 检测是否有互联网接口
        default_iface = ""
        with open("/proc/net/route", "r") as f:
            for line in f.readlines()[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    iface, dest, flags = parts[0], parts[1], parts[3]
                    if dest == "00000000" and int(flags, 16) & 0x1:
                        default_iface = iface
                        break

        if not default_iface or default_iface == USB_GADGET_IFACE:
            print("  [跳过] 无其他互联网接口，跳过 NAT 配置")
            return

        print(f"  [NAT] 通过 {default_iface} 共享互联网到 {USB_GADGET_IFACE}")

        run_ok(f"echo 1 > /proc/sys/net/ipv4/ip_forward")
        run_ok(f"iptables -t nat -A POSTROUTING -o {default_iface} -j MASQUERADE")
        run_ok(
            f"iptables -A FORWARD -i {default_iface} -o {USB_GADGET_IFACE} -m state "
            "--state RELATED,ESTABLISHED -j ACCEPT"
        )
        run_ok(f"iptables -A FORWARD -i {USB_GADGET_IFACE} -o {default_iface} -j ACCEPT")
        print("  [OK] NAT 已启用，PC 可通过 USB 访问互联网")

    def disable(self) -> Tuple[bool, str]:
        """禁用 USB Gadget"""
        if not is_root():
            return False, "需要 root 权限"

        # 禁用 IP
        run_ok(f"ip link set {USB_GADGET_IFACE} down 2>/dev/null")
        run_ok(f"ip addr del {USB_IP_DEVICE}/24 dev {USB_GADGET_IFACE} 2>/dev/null")

        # 清理 gadget
        if is_dir(self.gadget_path):
            # 写空字符串断开 UDC
            write_file(os.path.join(self.gadget_path, "UDC"), "")
            time.sleep(0.5)
            shutil.rmtree(self.gadget_path, ignore_errors=True)

        # 清理 NAT 规则
        run_ok(
            "iptables -t nat -D POSTROUTING -o $(ip route show default | awk '{print $5; exit}') -j MASQUERADE 2>/dev/null || true"
        )

        self.ready = False
        print("[完成] USB Gadget 已禁用")
        return True, "USB Gadget 已禁用"

    def status(self) -> dict:
        """获取当前状态"""
        status = {
            "gadget_active": is_dir(self.gadget_path),
            "gadget_name": None,
            "iface_active": os.path.exists(f"/sys/class/net/{USB_GADGET_IFACE}"),
            "iface_ip": None,
            "udc_bound": False,
        }

        if status["gadget_active"]:
            try:
                status["gadget_name"] = os.listdir(USB_GADGET_PATH)[0]
                udc = read_file(os.path.join(self.gadget_path, "UDC"))
                status["udc_bound"] = bool(udc)
            except Exception as e:
                pass

        if status["iface_active"]:
            _, ip_out, _ = run(f"ip addr show {USB_GADGET_IFACE} | grep 'inet '")
            status["iface_ip"] = ip_out.strip()

        return status


# ── 交互式诊断报告 ──────────────────────────────────────────────


def print_diagnosis(info: DeviceInfo) -> None:
    """打印设备诊断信息"""
    print("\n" + "=" * 54)
    print("  USB Gadget 诊断报告")
    print("=" * 54)
    print(f"  设备平台: {info.summary()}")
    if info.platform:
        print(f"  具体型号: {info.platform}")
    print(f"  内核版本: {info.kernel_version}")
    print(f"  USB 控制器: {info.usb_controller}")
    print()
    print("  ── USB Gadget 支持 ──")
    print(f"  configfs 支持:    {'✅' if info.has_gadget else '❌'}")
    print(f"  g_ether 模块:     {'✅' if info.has_ether else '❌'}")
    print(f"  g_rndis 模块:     {'✅' if info.has_rndis else '❌'}")
    print(f"  DWC2 驱动:        {'✅' if info.has_dwc2 else '❌'}")
    print(f"  DWC3 驱动:        {'✅' if info.has_dwc3 else '❌'}")
    print()

    if info.current_gadget:
        print(f"  当前 Gadget:   {info.current_gadget} ✅")
    else:
        print("  当前 Gadget:   ❌ 未启用")
        print()
        print("  ── 当前 USB 连接状态 ──")
        if info.usb_connected:
            print("  ✅ 检测到 USB 连接（请确保 USB 线已插到 PC）")
        else:
            print("  ⚠️  未检测到 USB 连接")
            print("     请先：")
            print("     1. 用 USB 线将设备连接到 PC")
            print("     2. 等待 PC 识别设备")
            print("     3. 重新运行本脚本")

    print()
    if info.extra_info:
        for k, v in info.extra_info.items():
            if k != "family" and v:
                print(f"  {k}: {v}")

    print("=" * 54 + "\n")


def print_status(s: dict) -> None:
    """打印状态"""
    print("\n" + "=" * 50)
    print("  USB Gadget 状态")
    print("=" * 50)
    print(f"  Gadget 活跃:     {'✅' if s['gadget_active'] else '❌'}")
    if s["gadget_name"]:
        print(f"  Gadget 名称:     {s['gadget_name']}")
    print(f"  USB Gadget 网卡: {'✅' if s['iface_active'] else '❌'} ({USB_GADGET_IFACE})")
    if s["iface_ip"]:
        print(f"  网卡 IP:         {s['iface_ip']}")
    else:
        print(f"  网卡 IP:         ❌ 未配置")
        print(f"  （需要 PC 端设置 {USB_IP_HOST}/24）")
    print(f"  UDC 已绑定:      {'✅' if s['udc_bound'] else '❌'}")
    print("=" * 50 + "\n")


def print_usage() -> None:
    print(
        """
USB Gadget 一键启用脚本
========================

用法:
  sudo python3 setup_usb_gadget.py [选项]

选项:
  --enable        启用 USB Gadget（自动检测最优驱动）
  --driver DRV    指定驱动: rndis（推荐）/ ether
  --disable       禁用 USB Gadget
  --status        查看当前状态
  --diag          仅诊断，不修改

示例:
  sudo python3 setup_usb_gadget.py --enable
  sudo python3 setup_usb_gadget.py --enable --driver rndis
  sudo python3 setup_usb_gadget.py --status
  sudo python3 setup_usb_gadget.py --diag

PC 端配置（启用后）:
  Windows:
    1. 设备管理器 -> 网络适配器 -> 找到 USB RNDIS 适配器
    2. 双击 -> IPv4 属性 -> 设置 IP: {host_ip}/24
       （自动获取也可，但建议手动: {host_ip}）
    3. ping {device_ip} 验证连接
    4. ssh root@{device_ip}

  Linux:
    sudo ip addr add {host_ip}/24 dev usb0
    ping {device_ip}

  macOS:
    系统偏好设置 -> 网络 -> 找到 USB 适配器 -> 设置 IP

""".format(
            host_ip=USB_IP_HOST,
            device_ip=USB_IP_DEVICE,
        )
    )


# ── 主入口 ──────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="USB Gadget 一键启用脚本")
    parser.add_argument("--enable", action="store_true", help="启用 USB Gadget")
    parser.add_argument(
        "--driver", choices=["rndis", "ether"], default="rndis", help="USB 驱动类型（默认: rndis）"
    )
    parser.add_argument("--disable", action="store_true", help="禁用 USB Gadget")
    parser.add_argument("--status", action="store_true", help="查看当前状态")
    parser.add_argument("--diag", action="store_true", help="仅诊断，不修改")
    args = parser.parse_args()

    if not is_root() and not args.diag:
        print("[错误] 需要 root 权限，请用 sudo 运行\n")
        print_usage()
        return 1

    # 检测设备
    info = detect_device()

    if args.diag:
        print_diagnosis(info)
        return 0

    if args.status:
        s = USBGadgetSetup().status()
        print_status(s)
        return 0

    if args.disable:
        setup = USBGadgetSetup()
        ok, msg = setup.disable()
        if ok:
            print(msg)
            return 0
        else:
            print(f"[错误] {msg}")
            return 1

    if args.enable:
        print_diagnosis(info)

        setup = USBGadgetSetup(driver=args.driver)
        ok, msg = setup.enable(info)

        if ok:
            print(f"\n✅ {msg}")
            print(f"\n📋 PC 端配置步骤（Windows）:")
            print(f"   1. 打开设备管理器，找到「USB RNDIS 适配器」")
            print(f"   2. 设置 IP: {USB_IP_HOST}  子网掩码: 255.255.255.0")
            print(f"   3. ping {USB_IP_DEVICE}  验证连接")
            print(f"   4. ssh root@{USB_IP_DEVICE}  远程访问设备")
            return 0
        else:
            print(f"\n❌ {msg}")
            print("\n如有问题，请运行: sudo python3 setup_usb_gadget.py --diag")
            return 1

    # 默认：诊断 + 帮助
    print_diagnosis(info)
    print_usage()
    return 0


if __name__ == "__main__":
    sys.exit(main())
