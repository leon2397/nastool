# -*- coding: utf-8 -*-
"""
core/storage_health.py — 存储健康检测
SMART 状态 / 磁盘温度 / RAID 状态 / 历史趋势
"""

import os
import re
import json
import subprocess
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum


class SMARTStatus(Enum):
    """SMART 健康状态"""

    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    UNKNOWN = "unknown"


class RAIDStatus(Enum):
    """RAID 状态"""

    CLEAN = "clean"  # 正常
    ACTIVE = "active"  # 活跃（可能有重建）
    DEGRADED = "degraded"  # 降级
    REBUILDING = "rebuilding"  # 重建中
    FAILED = "failed"  # 失败
    UNKNOWN = "unknown"


@dataclass
class SMARTAttribute:
    """SMART 属性"""

    id: int
    name: str
    value: int  # 当前值
    worst: int  # 最差值
    threshold: int  # 阈值
    raw: int  # 原始值
    status: str  # ok / warning / critical


@dataclass
class SMARTInfo:
    """单个磁盘 SMART 信息"""

    device: str
    model: str = ""
    serial: str = ""
    firmware: str = ""
    capacity_gb: float = 0.0
    status: SMARTStatus = SMARTStatus.UNKNOWN
    temperature: int = 0  # 摄氏度
    power_on_hours: int = 0
    power_cycle_count: int = 0
    reallocated_sectors: int = 0
    pending_sectors: int = 0
    uncorrectable_errors: int = 0
    attributes: List[SMARTAttribute] = field(default_factory=list)
    error: str = ""


@dataclass
class RAIDMember:
    """RAID 成员磁盘"""

    device: str
    state: str  # active / spare / faulty / rebuilding
    role: str  # 0, 1, 2... 或 "spare"


@dataclass
class RAIDInfo:
    """单个 RAID 阵列信息"""

    device: str  # /dev/md0, /dev/md1...
    name: str = ""
    level: str = ""  # raid0, raid1, raid5, raid6, raid10
    status: RAIDStatus = RAIDStatus.UNKNOWN
    members: List[RAIDMember] = field(default_factory=list)
    total_devices: int = 0
    active_devices: int = 0
    spare_devices: int = 0
    failed_devices: int = 0
    size_gb: float = 0.0
    used_gb: float = 0.0
    rebuild_progress: float = 0.0  # 0-100
    speed_mbps: float = 0.0  # 重建速度
    estimated_minutes: int = 0  # 预计完成时间


@dataclass
class StorageHealthReport:
    """存储健康报告"""

    timestamp: str
    smart_data: List[SMARTInfo] = field(default_factory=list)
    raid_data: List[RAIDInfo] = field(default_factory=list)
    temperature_summary: Dict[str, Any] = field(default_factory=dict)
    health_score: int = 0  # 0-100
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ok: bool = True


def _run(cmd: str, timeout: int = 10) -> str:
    """执行命令并返回输出"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return ""


def _parse_smart_output(output: str) -> Dict[str, Any]:
    """解析 smartctl 输出"""
    result = {
        "model": "",
        "serial": "",
        "firmware": "",
        "status": SMARTStatus.UNKNOWN,
        "temperature": 0,
        "power_on_hours": 0,
        "power_cycle_count": 0,
        "reallocated_sectors": 0,
        "pending_sectors": 0,
        "uncorrectable_errors": 0,
        "attributes": [],
    }

    # 整体状态
    if "SMART overall-health self-assessment test result:" in output:
        if "PASSED" in output:
            result["status"] = SMARTStatus.PASSED
        elif "FAILED" in output:
            result["status"] = SMARTStatus.FAILED
        elif "WARNING" in output:
            result["status"] = SMARTStatus.WARNING

    # Model/Family
    for line in output.splitlines():
        if "Device Model:" in line or "Model Number:" in line:
            result["model"] = line.split(":", 1)[1].strip()
        elif "Serial Number:" in line:
            result["serial"] = line.split(":", 1)[1].strip()
        elif "Firmware Version:" in line:
            result["firmware"] = line.split(":", 1)[1].strip()
        elif "User Capacity:" in line:
            # 解析容量
            match = re.search(r"(\d+[\d,]*)\s*bytes", line)
            if match:
                bytes_val = int(match.group(1).replace(",", ""))
                result["capacity_gb"] = round(bytes_val / 1024**3, 1)

    # SMART 属性
    in_attrs = False
    for line in output.splitlines():
        if "ID#" in line and "ATTRIBUTE_NAME" in line:
            in_attrs = True
            continue
        if in_attrs and line.strip():
            parts = line.split()
            if len(parts) >= 10:
                try:
                    attr_id = int(parts[0])
                    attr_name = parts[1]
                    attr_value = int(parts[2])
                    attr_worst = int(parts[3])
                    attr_thresh = int(parts[4])
                    # raw 值可能在最后
                    raw_str = parts[-1]
                    try:
                        attr_raw = int(raw_str)
                    except Exception as e:
                        attr_raw = 0

                    # 判断状态
                    if attr_thresh > 0 and attr_value <= attr_thresh:
                        attr_status = "critical"
                    elif attr_value < attr_worst:
                        attr_status = "warning"
                    else:
                        attr_status = "ok"

                    attr = SMARTAttribute(
                        id=attr_id,
                        name=attr_name,
                        value=attr_value,
                        worst=attr_worst,
                        threshold=attr_thresh,
                        raw=attr_raw,
                        status=attr_status,
                    )
                    result["attributes"].append(attr)

                    # 提取关键属性
                    if attr_name == "Temperature_Celsius" or attr_name == "Temperature":
                        result["temperature"] = attr_raw if attr_raw < 200 else attr_value
                    elif attr_name == "Power_On_Hours":
                        result["power_on_hours"] = attr_raw
                    elif attr_name == "Power_Cycle_Count":
                        result["power_cycle_count"] = attr_raw
                    elif attr_name == "Reallocated_Sector_Ct":
                        result["reallocated_sectors"] = attr_raw
                    elif attr_name == "Current_Pending_Sector":
                        result["pending_sectors"] = attr_raw
                    elif attr_name == "Offline_Uncorrectable":
                        result["uncorrectable_errors"] = attr_raw

                except Exception as e:
                    continue

    return result


def get_smart_info(device: str) -> SMARTInfo:
    """
    获取单个磁盘 SMART 信息

    Args:
        device: 设备路径，如 /dev/sda
    """
    info = SMARTInfo(device=device)

    # 检查 smartctl 是否可用
    smartctl_check = _run("which smartctl")
    if not smartctl_check:
        info.error = "smartctl 未安装"
        return info

    # 获取 SMART 数据
    output = _run(f"sudo smartctl -a {device} 2>/dev/null", timeout=30)
    if not output:
        info.error = "无法获取 SMART 数据（可能需要 sudo）"
        return info

    # 解析
    parsed = _parse_smart_output(output)
    info.model = parsed.get("model", "")
    info.serial = parsed.get("serial", "")
    info.firmware = parsed.get("firmware", "")
    info.capacity_gb = parsed.get("capacity_gb", 0.0)
    info.status = parsed.get("status", SMARTStatus.UNKNOWN)
    info.temperature = parsed.get("temperature", 0)
    info.power_on_hours = parsed.get("power_on_hours", 0)
    info.power_cycle_count = parsed.get("power_cycle_count", 0)
    info.reallocated_sectors = parsed.get("reallocated_sectors", 0)
    info.pending_sectors = parsed.get("pending_sectors", 0)
    info.uncorrectable_errors = parsed.get("uncorrectable_errors", 0)
    info.attributes = parsed.get("attributes", [])

    return info


def get_all_smart_info() -> List[SMARTInfo]:
    """获取所有磁盘 SMART 信息"""
    results = []

    # 列出所有块设备
    devices_out = _run("lsblk -d -o NAME,TYPE -n 2>/dev/null | grep disk | awk '{print $1}'")
    if not devices_out:
        return results

    for dev in devices_out.splitlines():
        dev = dev.strip()
        if dev:
            device = f"/dev/{dev}"
            info = get_smart_info(device)
            results.append(info)

    return results


def _parse_mdstat(content: str) -> List[RAIDInfo]:
    """解析 /proc/mdstat"""
    raids = []

    # 示例输出：
    # md0 : active raid1 sda1[0] sdb1[1](F)
    #       976630272 blocks super 1.2 [2/1] [_U]
    # md1 : active raid5 sda2[0] sdb2[1] sdc2[2]

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith("Personalities"):
            i += 1
            continue

        # 匹配 md 设备行
        match = re.match(r"(md\d+)\s*:\s*(\w+)\s+(\w+)\s+(.*)", line)
        if match:
            raid = RAIDInfo(device=f"/dev/{match.group(1)}")
            raid.status = (
                RAIDStatus(match.group(2))
                if match.group(2) in ["active", "inactive"]
                else RAIDStatus.UNKNOWN
            )
            raid.level = match.group(3)

            # 解析成员
            members_str = match.group(4)
            for m in re.finditer(r"(\w+)\[(\d+)\](\([A-Z]\))?", members_str):
                device = f"/dev/{m.group(1)}"
                role = m.group(2)
                flag = m.group(3) if m.group(3) else ""

                if "(F)" in flag:
                    state = "faulty"
                elif "(S)" in flag:
                    state = "spare"
                elif "(R)" in flag or "(W)" in flag:
                    state = "rebuilding"
                else:
                    state = "active"

                raid.members.append(RAIDMember(device=device, state=state, role=role))

            # 检查下一行是否有 [n/m] 信息
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                state_match = re.search(r"\[(\d+)/(\d+)\]\s+\[([_U]+)\]", next_line)
                if state_match:
                    raid.total_devices = int(state_match.group(1))
                    raid.active_devices = int(state_match.group(2))
                    state_str = state_match.group(3)

                    # 从状态字符串判断
                    if "_" in state_str and "U" in state_str:
                        raid.status = RAIDStatus.DEGRADED
                    elif "_" in state_str and "U" not in state_str:
                        raid.status = RAIDStatus.FAILED
                    else:
                        raid.status = RAIDStatus.CLEAN

                    raid.failed_devices = raid.total_devices - raid.active_devices

                # 检查重建进度
                rebuild_match = re.search(r"recovery\s*=\s*([\d.]+)%", next_line)
                if rebuild_match:
                    raid.status = RAIDStatus.REBUILDING
                    raid.rebuild_progress = float(rebuild_match.group(1))

                # 重建速度
                speed_match = re.search(r"speed=(\d+)", next_line)
                if speed_match:
                    raid.speed_mbps = int(speed_match.group(1)) / 1024  # K/s -> MB/s

                # 预计完成时间
                finish_match = re.search(r"finish=([\d.]+)min", next_line)
                if finish_match:
                    raid.estimated_minutes = int(float(finish_match.group(1)))

            raids.append(raid)

        i += 1

    return raids


def get_raid_info() -> List[RAIDInfo]:
    """获取 RAID 阵列信息"""
    # 读取 /proc/mdstat
    mdstat = _run("cat /proc/mdstat 2>/dev/null")
    if not mdstat:
        return []

    raids = _parse_mdstat(mdstat)

    # 补充容量信息
    for raid in raids:
        size_out = _run(f"lsblk -b -o SIZE {raid.device} 2>/dev/null | tail -1")
        if size_out:
            try:
                raid.size_gb = round(int(size_out) / 1024**3, 1)
            except Exception as e:
                pass

        # 使用量
        df_out = _run(f"df -B1 {raid.device} 2>/dev/null | tail -1")
        if df_out:
            parts = df_out.split()
            if len(parts) >= 3:
                try:
                    raid.used_gb = round(int(parts[2]) / 1024**3, 1)
                except Exception as e:
                    pass

    return raids


def get_temperature_summary(smart_data: List[SMARTInfo]) -> Dict[str, Any]:
    """
    汇总温度信息

    Returns:
        {
            "max": 45,
            "min": 35,
            "avg": 40,
            "by_device": {"sda": 42, "sdb": 38},
            "hot_devices": ["sda"],  # > 50°C
            "overheat_devices": []   # > 60°C
        }
    """
    temps = [d.temperature for d in smart_data if d.temperature > 0]
    by_device = {os.path.basename(d.device): d.temperature for d in smart_data if d.temperature > 0}

    hot_threshold = 50
    overheat_threshold = 60

    hot = [
        os.path.basename(d.device)
        for d in smart_data
        if d.temperature >= hot_threshold and d.temperature < overheat_threshold
    ]
    overheat = [
        os.path.basename(d.device) for d in smart_data if d.temperature >= overheat_threshold
    ]

    return {
        "max": max(temps) if temps else 0,
        "min": min(temps) if temps else 0,
        "avg": round(sum(temps) / len(temps), 1) if temps else 0,
        "by_device": by_device,
        "hot_devices": hot,
        "overheat_devices": overheat,
    }


def calculate_health_score(smart_data: List[SMARTInfo], raid_data: List[RAIDInfo]) -> int:
    """
    计算存储健康分数（0-100）

    评分规则：
    - 基础分 100
    - SMART FAILED: -30
    - SMART WARNING: -10
    - 温度 > 60°C: -15
    - 温度 > 50°C: -5
    - RAID DEGRADED: -20
    - RAID REBUILDING: -10
    - RAID FAILED: -40
    - Reallocated Sectors > 0: -5
    - Pending Sectors > 0: -5
    """
    score = 100

    for d in smart_data:
        if d.status == SMARTStatus.FAILED:
            score -= 30
        elif d.status == SMARTStatus.WARNING:
            score -= 10

        if d.temperature >= 60:
            score -= 15
        elif d.temperature >= 50:
            score -= 5

        if d.reallocated_sectors > 0:
            score -= min(5, d.reallocated_sectors)
        if d.pending_sectors > 0:
            score -= min(5, d.pending_sectors)

    for r in raid_data:
        if r.status == RAIDStatus.FAILED:
            score -= 40
        elif r.status == RAIDStatus.DEGRADED:
            score -= 20
        elif r.status == RAIDStatus.REBUILDING:
            score -= 10

    return max(0, min(100, score))


def check_storage_health() -> StorageHealthReport:
    """
    主入口：检测存储健康状态

    Returns:
        StorageHealthReport
    """
    report = StorageHealthReport(timestamp=datetime.now().isoformat())

    # 1. SMART 信息
    report.smart_data = get_all_smart_info()

    # 2. RAID 信息
    report.raid_data = get_raid_info()

    # 3. 温度汇总
    report.temperature_summary = get_temperature_summary(report.smart_data)

    # 4. 计算健康分数
    report.health_score = calculate_health_score(report.smart_data, report.raid_data)

    # 5. 收集问题
    for d in report.smart_data:
        if d.status == SMARTStatus.FAILED:
            report.issues.append(f"{d.device} SMART 失败")
        elif d.status == SMARTStatus.WARNING:
            report.warnings.append(f"{d.device} SMART 警告")

        if d.temperature >= 60:
            report.issues.append(f"{d.device} 温度过高 ({d.temperature}°C)")
        elif d.temperature >= 50:
            report.warnings.append(f"{d.device} 温度偏高 ({d.temperature}°C)")

        if d.reallocated_sectors > 0:
            report.warnings.append(f"{d.device} 有 {d.reallocated_sectors} 个重分配扇区")
        if d.pending_sectors > 0:
            report.warnings.append(f"{d.device} 有 {d.pending_sectors} 个待处理扇区")

    for r in report.raid_data:
        if r.status == RAIDStatus.FAILED:
            report.issues.append(f"{r.device} RAID 失败")
        elif r.status == RAIDStatus.DEGRADED:
            report.warnings.append(f"{r.device} RAID 降级")
        elif r.status == RAIDStatus.REBUILDING:
            report.warnings.append(f"{r.device} RAID 重建中 ({r.rebuild_progress:.1f}%)")

    # 6. 综合判断
    report.ok = len(report.issues) == 0

    return report


# ══════════════════════════════════════════════════════════════════
# 历史趋势记录
# ══════════════════════════════════════════════════════════════════

HISTORY_FILE = "/var/lib/nastool/storage_history.json"


def save_history(report: StorageHealthReport, max_days: int = 30) -> None:
    """
    保存历史记录

    Args:
        report: 健康报告
        max_days: 保留天数
    """
    # 读取现有历史
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except Exception as e:
            pass

    # 添加新记录
    record = {
        "timestamp": report.timestamp,
        "health_score": report.health_score,
        "temperatures": report.temperature_summary.get("by_device", {}),
        "smart_status": {d.device: d.status.value for d in report.smart_data},
        "raid_status": {r.device: r.status.value for r in report.raid_data},
    }
    history.append(record)

    # 清理旧记录
    cutoff = datetime.now().timestamp() - max_days * 86400
    history = [h for h in history if datetime.fromisoformat(h["timestamp"]).timestamp() > cutoff]

    # 保存
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_trend(days: int = 7) -> Dict[str, Any]:
    """
    获取趋势数据

    Args:
        days: 查询天数

    Returns:
        {
            "health_scores": [85, 85, 80, ...],
            "temperature_trend": {"sda": [42, 43, 45, ...], ...},
            "smart_failures": 2,
            "raid_degraded_events": 1
        }
    """
    if not os.path.exists(HISTORY_FILE):
        return {}

    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    except Exception as e:
        return {}

    cutoff = datetime.now().timestamp() - days * 86400
    history = [h for h in history if datetime.fromisoformat(h["timestamp"]).timestamp() > cutoff]

    if not history:
        return {}

    result = {
        "health_scores": [h["health_score"] for h in history],
        "temperature_trend": {},
        "smart_failures": 0,
        "raid_degraded_events": 0,
    }

    # 温度趋势
    devices = set()
    for h in history:
        devices.update(h.get("temperatures", {}).keys())

    for dev in devices:
        result["temperature_trend"][dev] = [h.get("temperatures", {}).get(dev, 0) for h in history]

    # 统计事件
    for h in history:
        for status in h.get("smart_status", {}).values():
            if status == "failed":
                result["smart_failures"] += 1
        for status in h.get("raid_status", {}).values():
            if status in ["degraded", "failed"]:
                result["raid_degraded_events"] += 1

    return result


def format_report(report: StorageHealthReport, verbose: bool = False) -> str:
    """格式化报告为文本"""
    lines = []

    # 标题
    lines.append("=" * 60)
    lines.append("存储健康报告")
    lines.append(f"时间: {report.timestamp}")
    lines.append(f"健康分数: {report.health_score}/100")
    lines.append("=" * 60)
    lines.append("")

    # SMART 信息
    if report.smart_data:
        lines.append("📊 SMART 状态:")
        for d in report.smart_data:
            status_icon = (
                "✅"
                if d.status == SMARTStatus.PASSED
                else "⚠️"
                if d.status == SMARTStatus.WARNING
                else "❌"
            )
            temp_str = f", {d.temperature}°C" if d.temperature > 0 else ""
            lines.append(f"  {status_icon} {d.device}: {d.model}{temp_str}")

            if verbose and d.attributes:
                for attr in d.attributes[:5]:  # 只显示前 5 个关键属性
                    if attr.status != "ok":
                        lines.append(f"     - {attr.name}: {attr.value} (阈值 {attr.threshold})")
        lines.append("")

    # RAID 信息
    if report.raid_data:
        lines.append("💿 RAID 状态:")
        for r in report.raid_data:
            status_icon = (
                "✅"
                if r.status == RAIDStatus.CLEAN
                else "⚠️"
                if r.status in [RAIDStatus.DEGRADED, RAIDStatus.REBUILDING]
                else "❌"
            )
            lines.append(f"  {status_icon} {r.device}: {r.level} ({r.status.value})")
            lines.append(f"     容量: {r.size_gb:.1f} GB, 已用: {r.used_gb:.1f} GB")
            lines.append(f"     成员: {r.active_devices}/{r.total_devices} 活跃")

            if r.status == RAIDStatus.REBUILDING:
                lines.append(
                    f"     重建进度: {r.rebuild_progress:.1f}%, 速度: {r.speed_mbps:.1f} MB/s"
                )
                if r.estimated_minutes > 0:
                    lines.append(f"     预计完成: {r.estimated_minutes} 分钟")
        lines.append("")

    # 温度汇总
    if report.temperature_summary:
        ts = report.temperature_summary
        lines.append("🌡️ 温度汇总:")
        lines.append(f"  最高: {ts['max']}°C, 最低: {ts['min']}°C, 平均: {ts['avg']}°C")
        if ts["hot_devices"]:
            lines.append(f"  ⚠️ 偏热设备: {', '.join(ts['hot_devices'])}")
        if ts["overheat_devices"]:
            lines.append(f"  ❌ 过热设备: {', '.join(ts['overheat_devices'])}")
        lines.append("")

    # 问题
    if report.issues:
        lines.append("❌ 严重问题:")
        for issue in report.issues:
            lines.append(f"  - {issue}")
        lines.append("")

    if report.warnings:
        lines.append("⚠️ 警告:")
        for warning in report.warnings:
            lines.append(f"  - {warning}")
        lines.append("")

    # 总结
    if report.ok:
        lines.append("✅ 存储健康状态良好")
    else:
        lines.append("❌ 存储需要维护")

    return "\n".join(lines)
