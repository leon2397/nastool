# -*- coding: utf-8 -*-
"""
nastool/usb/ — V4.2 USB 连接模块

统一 USB 连接管理器，支持四种方式：
  ADB / USB Gadget / CDC-ACM / MTP

Usage:
    from nastool.usb import USBManager, detect_all, USBDevice, ConnectionMode

    mgr = USBManager()
    devices = mgr.detect_all()
    for dev in devices:
        ok, out = mgr.run_command(dev, "hostname")
        print(out)
"""

from .manager import (
    USBManager,
    USBBackend,
    USBDevice,
    ConnectionMode,
    get_manager,
    detect_all,
)

__all__ = [
    "USBManager",
    "USBBackend",
    "USBDevice",
    "ConnectionMode",
    "get_manager",
    "detect_all",
]

__version__ = "4.2.0"
