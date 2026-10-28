"""
checks/usb.py — 外设

只做两件真正有价值的事：
  · 清点挂着的 USB 设备（验机时能看出有没有偷偷插挖矿/加密狗/无线网卡）
  · 判断数据盘是不是挂在 USB 上（这是真实且常见的稳定性隐患）
"""
from __future__ import annotations

import os
import re

from ..collect.util import read_file, safe_listdir
from ..model import Status
from ..registry import check
from ._base import R, ev


def _target_block_device(ctx):
    """目标路径所在磁盘的块设备名（去掉分区号）。"""
    s = ctx.storage
    best, best_len = None, -1
    for d in s.disks:
        mp = d.mountpoint.rstrip("/") or "/"
        if s.target_path.startswith(mp) and len(mp) > best_len:
            best, best_len = d, len(mp)
    if best is None or not best.device.startswith("/dev/"):
        return ""

    base = os.path.basename(best.device)
    m = re.match(r"([a-zA-Z]+)", base)
    if not m:
        return ""
    name = m.group(1)
    # 排除 nvme0n1p1 / mmcblk0p1 这类带数字的命名
    return name


@check("usb.devices", "USB 设备", "usb", weight=1,
       platforms=["linux"], tags=["verify"])
def usb_devices(ctx):
    base = "/sys/bus/usb/devices"
    entries = safe_listdir(base)
    if not entries:
        return R(Status.SKIP, "系统不提供 USB 设备信息",
                 detail="无 USB 子系统（常见于虚拟机 / 容器 / ARM 板卡）")

    devices = []
    for name in entries:
        if "-" not in name and ":" not in name:
            continue          # 只看具体设备，不看 root hub
        if ":" in name:
            continue          # 接口节点，跳过
        vendor = read_file(f"{base}/{name}/manufacturer", "")
        product = read_file(f"{base}/{name}/product", "")
        vid = read_file(f"{base}/{name}/idVendor", "")
        pid = read_file(f"{base}/{name}/idProduct", "")
        cls = read_file(f"{base}/{name}/bDeviceClass", "")
        if cls == "09":
            continue          # hub
        label = " ".join(x for x in (vendor, product) if x) or f"{vid}:{pid}"
        devices.append((name, label, vid, pid))

    if not devices:
        return R(Status.PASS, "未接入 USB 设备", confidence=0.85)

    return R(Status.PASS, f"{len(devices)} 个 USB 设备接入",
             evidence=[ev("USB", name, label) for name, label, _, _ in devices[:10]],
             confidence=0.85)


@check("usb.storage_media", "数据盘连接方式", "usb", weight=4,
       platforms=["linux"], tags=["nas", "verify"])
def storage_media(ctx):
    name = _target_block_device(ctx)
    if not name:
        return R(Status.SKIP, "无法确定数据盘的块设备",
                 detail="路径可能在网络挂载 / 容器卷上")

    removable = read_file(f"/sys/block/{name}/removable", "")
    if removable not in ("0", "1"):
        return R(Status.UNKNOWN, f"无法读取 /sys/block/{name}/removable")

    # 传输类型：USB 设备通常同时具备 removable=1 或出现在 usb 总线下
    on_usb = removable == "1"
    evidence = [ev(f"/sys/block/{name}", "removable", removable),
                ev("挂载点", "device", f"/dev/{name}")]

    if on_usb:
        return R(Status.WARN, f"数据盘 /dev/{name} 挂在可移动总线（USB/SD）上",
                 detail="USB 桥接的硬盘会因供电不稳、休眠、线缆接触不良而掉盘，"
                        "RAID 场景下掉盘会直接触发降级",
                 suggestion="改用主板 SATA 接口；必须用 USB 时选择带独立供电的硬盘盒并关闭休眠",
                 evidence=evidence, confidence=0.85)

    return R(Status.PASS, f"数据盘 /dev/{name} 为内置接口连接", evidence=evidence,
             confidence=0.85)
