# -*- coding: utf-8 -*-
"""
core/system_health.py — 系统健康检测
CPU 温度 / 启动时间 / 趋势 / Docker / 内存 / 磁盘
"""

import os
import re
import subprocess
import time
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class ServiceStatus(Enum):
    """服务状态"""

    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class CPUInfo:
    """CPU 信息"""

    model: str = ""
    cores: int = 0
    threads: int = 0
    frequency_mhz: float = 0.0
    temperature_c: float = 0.0
    usage_percent: float = 0.0
    load_avg_1: float = 0.0
    load_avg_5: float = 0.0
    load_avg_15: float = 0.0


@dataclass
class MemoryInfo:
    """内存信息"""

    total_mb: int = 0
    used_mb: int = 0
    free_mb: int = 0
    available_mb: int = 0
    buffers_mb: int = 0
    cached_mb: int = 0
    swap_total_mb: int = 0
    swap_used_mb: int = 0
    usage_percent: float = 0.0


@dataclass
class DiskInfo:
    """磁盘信息"""

    device: str = ""
    mount_point: str = ""
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    usage_percent: float = 0.0
    filesystem: str = ""


@dataclass
class DockerInfo:
    """Docker 信息"""

    installed: bool = False
    version: str = ""
    running: bool = False
    containers_total: int = 0
    containers_running: int = 0
    containers_stopped: int = 0
    images_total: int = 0
    disk_usage_gb: float = 0.0
    error: str = ""


@dataclass
class ServiceInfo:
    """服务信息"""

    name: str
    status: ServiceStatus
    enabled: bool = False
    uptime_seconds: int = 0
    pid: int = 0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0


@dataclass
class SystemHealthReport:
    """系统健康报告"""

    timestamp: str
    hostname: str = ""
    uptime_seconds: int = 0
    uptime_human: str = ""
    cpu: CPUInfo = field(default_factory=CPUInfo)
    memory: MemoryInfo = field(default_factory=MemoryInfo)
    disks: List[DiskInfo] = field(default_factory=list)
    docker: DockerInfo = field(default_factory=DockerInfo)
    services: List[ServiceInfo] = field(default_factory=list)
    health_score: int = 0
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


def _read_file(path: str) -> str:
    """读取文件内容"""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception as e:
        return ""


# ══════════════════════════════════════════════════════════════════
# CPU 信息
# ══════════════════════════════════════════════════════════════════


def get_cpu_info() -> CPUInfo:
    """获取 CPU 信息"""
    cpu = CPUInfo()

    # CPU 型号
    model_info = _read_file("/proc/cpuinfo")
    if model_info:
        for line in model_info.splitlines():
            if "model name" in line.lower():
                match = re.search(r"model name\s*:\s*(.+)", line, re.IGNORECASE)
                if match:
                    cpu.model = match.group(1).strip()
                break

    # 核心数
    cores = _read_file("/sys/devices/system/cpu/present")
    if cores:
        # 格式: 0-7
        match = re.match(r"0-(\d+)", cores)
        if match:
            cpu.cores = int(match.group(1)) + 1
    else:
        # 备选：lscpu
        lscpu = _run("lscpu 2>/dev/null | grep 'CPU(s)' | awk '{print $2}'")
        if lscpu:
            cpu.cores = int(lscpu)
            cpu.threads = cpu.cores

    # 频率
    freq = _read_file("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    if freq:
        cpu.frequency_mhz = int(freq) / 1000
    else:
        # 备选：从 /proc/cpuinfo
        if model_info:
            for line in model_info.splitlines():
                if "cpu MHz" in line:
                    match = re.search(r"cpu MHz\s*:\s*([\d.]+)", line)
                    if match:
                        cpu.frequency_mhz = float(match.group(1))
                    break

    # 温度
    cpu.temperature_c = get_cpu_temperature()

    # 使用率
    cpu.usage_percent = get_cpu_usage()

    # 负载
    loadavg = _read_file("/proc/loadavg")
    if loadavg:
        parts = loadavg.split()
        if len(parts) >= 3:
            cpu.load_avg_1 = float(parts[0])
            cpu.load_avg_5 = float(parts[1])
            cpu.load_avg_15 = float(parts[2])

    return cpu


def get_cpu_temperature() -> float:
    """获取 CPU 温度"""
    # 方法 1: thermal_zone
    thermal_path = "/sys/class/thermal/thermal_zone0/temp"
    if os.path.exists(thermal_path):
        temp_str = _read_file(thermal_path)
        if temp_str:
            try:
                # 通常单位是毫度
                return int(temp_str) / 1000.0
            except Exception as e:
                pass

    # 方法 2: sensors (lm-sensors)
    sensors_out = _run("sensors 2>/dev/null | grep -i 'core 0' | head -1")
    if sensors_out:
        match = re.search(r"([\d.]+)°C", sensors_out)
        if match:
            return float(match.group(1))

    # 方法 3: /sys/class/hwmon
    for hwmon in os.listdir("/sys/class/hwmon"):
        temp_path = f"/sys/class/hwmon/{hwmon}/temp1_input"
        if os.path.exists(temp_path):
            temp_str = _read_file(temp_path)
            if temp_str:
                try:
                    return int(temp_str) / 1000.0
                except Exception as e:
                    pass

    return 0.0


def get_cpu_usage() -> float:
    """获取 CPU 使用率"""

    # 读取 /proc/stat 两次计算
    def read_stat():
        stat = _read_file("/proc/stat")
        if not stat:
            return None
        line = stat.splitlines()[0]
        parts = line.split()
        # user nice system idle iowait irq softirq steal guest guest_nice
        return [int(x) for x in parts[1:9]]

    stat1 = read_stat()
    if not stat1:
        return 0.0

    time.sleep(0.5)

    stat2 = read_stat()
    if not stat2:
        return 0.0

    # 计算
    idle1 = stat1[3] + stat1[4]  # idle + iowait
    idle2 = stat2[3] + stat2[4]

    total1 = sum(stat1)
    total2 = sum(stat2)

    idle_delta = idle2 - idle1
    total_delta = total2 - total1

    if total_delta == 0:
        return 0.0

    usage = 100.0 * (1 - idle_delta / total_delta)
    return round(usage, 1)


# ══════════════════════════════════════════════════════════════════
# 内存信息
# ══════════════════════════════════════════════════════════════════


def get_memory_info() -> MemoryInfo:
    """获取内存信息"""
    mem = MemoryInfo()

    meminfo = _read_file("/proc/meminfo")
    if not meminfo:
        return mem

    data = {}
    for line in meminfo.splitlines():
        match = re.match(r"(\w+):\s*(\d+)", line)
        if match:
            data[match.group(1)] = int(match.group(2))

    # 单位是 KB
    mem.total_mb = data.get("MemTotal", 0) // 1024
    mem.free_mb = data.get("MemFree", 0) // 1024
    mem.available_mb = data.get("MemAvailable", 0) // 1024
    mem.buffers_mb = data.get("Buffers", 0) // 1024
    mem.cached_mb = data.get("Cached", 0) // 1024
    mem.used_mb = mem.total_mb - mem.available_mb

    mem.swap_total_mb = data.get("SwapTotal", 0) // 1024
    mem.swap_used_mb = mem.swap_total_mb - data.get("SwapFree", 0) // 1024

    if mem.total_mb > 0:
        mem.usage_percent = round(100.0 * mem.used_mb / mem.total_mb, 1)

    return mem


# ══════════════════════════════════════════════════════════════════
# 磁盘信息
# ══════════════════════════════════════════════════════════════════


def get_disk_info() -> List[DiskInfo]:
    """获取磁盘信息"""
    disks = []

    df_out = _run("df -h -x tmpfs -x devtmpfs -x squashfs 2>/dev/null | tail -n +2")
    if not df_out:
        return disks

    for line in df_out.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue

        disk = DiskInfo()
        disk.device = parts[0]
        disk.total_gb = _parse_size(parts[1])
        disk.used_gb = _parse_size(parts[2])
        disk.free_gb = _parse_size(parts[3])
        disk.mount_point = parts[5]
        disk.filesystem = parts[0].split("/")[-1] if "/" in parts[0] else parts[0]

        # 使用率
        if disk.total_gb > 0:
            disk.usage_percent = round(100.0 * disk.used_gb / disk.total_gb, 1)

        disks.append(disk)

    return disks


def _parse_size(s: str) -> float:
    """解析大小字符串（如 100G, 50M）"""
    match = re.match(r"([\d.]+)([KMGTPE]?)", s, re.IGNORECASE)
    if not match:
        return 0.0

    value = float(match.group(1))
    unit = match.group(2).upper()

    multipliers = {
        "K": 1 / 1024,
        "M": 1 / 1024 / 1024,
        "G": 1,
        "T": 1024,
        "P": 1024 * 1024,
        "E": 1024 * 1024 * 1024,
    }

    return value * multipliers.get(unit, 1)


# ══════════════════════════════════════════════════════════════════
# Docker 信息
# ══════════════════════════════════════════════════════════════════


def get_docker_info() -> DockerInfo:
    """获取 Docker 信息"""
    docker = DockerInfo()

    # 检查是否安装
    version_out = _run("docker --version 2>/dev/null")
    if not version_out:
        docker.installed = False
        return docker

    docker.installed = True

    # 解析版本
    match = re.search(r"Docker version ([\d.]+)", version_out)
    if match:
        docker.version = match.group(1)

    # 检查是否运行
    info_out = _run("docker info 2>/dev/null")
    if info_out:
        docker.running = True

        # 容器数量
        containers_out = _run("docker ps -a --format '{{.Status}}' 2>/dev/null")
        if containers_out:
            lines = containers_out.splitlines()
            docker.containers_total = len(lines)
            docker.containers_running = sum(1 for l in lines if "Up" in l)
            docker.containers_stopped = docker.containers_total - docker.containers_running

        # 镜像数量
        images_out = _run("docker images --format '{{.ID}}' 2>/dev/null")
        if images_out:
            docker.images_total = len(images_out.splitlines())

        # 磁盘使用
        disk_out = _run("docker system df --format '{{.Size}}' 2>/dev/null | head -1")
        if disk_out:
            docker.disk_usage_gb = _parse_size(disk_out)

    else:
        docker.running = False
        docker.error = "Docker daemon not running"

    return docker


# ══════════════════════════════════════════════════════════════════
# 服务信息
# ══════════════════════════════════════════════════════════════════


def get_service_info(service_name: str) -> ServiceInfo:
    """获取服务信息"""
    service = ServiceInfo(name=service_name, status=ServiceStatus.UNKNOWN)

    # systemctl status
    status_out = _run(
        f"systemctl show {service_name} --property=ActiveState,SubState,MainPID,ActiveEnterTimestamp 2>/dev/null"
    )
    if status_out:
        for line in status_out.splitlines():
            if "ActiveState=" in line:
                state = line.split("=")[1]
                if state == "active":
                    service.status = ServiceStatus.RUNNING
                elif state == "inactive":
                    service.status = ServiceStatus.STOPPED
                elif state == "failed":
                    service.status = ServiceStatus.FAILED
            elif "MainPID=" in line:
                service.pid = int(line.split("=")[1])

    # 是否开机启动
    enabled_out = _run(f"systemctl is-enabled {service_name} 2>/dev/null")
    service.enabled = enabled_out == "enabled"

    # 运行时间
    if service.status == ServiceStatus.RUNNING and service.pid > 0:
        # 从 /proc/{pid}/stat 获取启动时间
        stat_path = f"/proc/{service.pid}/stat"
        if os.path.exists(stat_path):
            try:
                stat = _read_file(stat_path)
                parts = stat.split()
                # 第 22 个字段是启动时间（jiffies）
                start_jiffies = int(parts[21])
                # 获取系统启动时间
                btime = 0
                for line in _read_file("/proc/stat").splitlines():
                    if line.startswith("btime"):
                        btime = int(line.split()[1])
                        break
                # 获取 HZ
                hz = os.sysconf("SC_CLK_TCK")
                # 计算启动时间
                start_time = btime + start_jiffies / hz
                service.uptime_seconds = int(time.time() - start_time)
            except Exception as e:
                pass

    return service


def get_services_info(services: List[str]) -> List[ServiceInfo]:
    """获取多个服务信息"""
    return [get_service_info(s) for s in services]


# ══════════════════════════════════════════════════════════════════
# 系统运行时间
# ══════════════════════════════════════════════════════════════════


def get_uptime() -> tuple:
    """获取系统运行时间"""
    uptime_str = _read_file("/proc/uptime")
    if not uptime_str:
        return 0, ""

    uptime_seconds = int(float(uptime_str.split()[0]))

    # 格式化
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60

    if days > 0:
        uptime_human = f"{days}天 {hours}小时 {minutes}分钟"
    elif hours > 0:
        uptime_human = f"{hours}小时 {minutes}分钟"
    else:
        uptime_human = f"{minutes}分钟"

    return uptime_seconds, uptime_human


# ══════════════════════════════════════════════════════════════════
# 趋势数据
# ══════════════════════════════════════════════════════════════════

HISTORY_FILE = "/var/lib/nastool/system_history.json"
MAX_HISTORY_DAYS = 30


def save_history(report: SystemHealthReport):
    """保存历史数据"""
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
        "cpu_temp": report.cpu.temperature_c,
        "cpu_usage": report.cpu.usage_percent,
        "mem_usage": report.memory.usage_percent,
        "load_avg": report.cpu.load_avg_1,
    }
    history.append(record)

    # 清理旧记录
    cutoff = (datetime.now() - timedelta(days=MAX_HISTORY_DAYS)).isoformat()
    history = [r for r in history if r["timestamp"] > cutoff]

    # 保存
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        pass


def get_trend(days: int = 7) -> Dict[str, Any]:
    """获取趋势数据"""
    if not os.path.exists(HISTORY_FILE):
        return {}

    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    except Exception as e:
        return {}

    # 过滤时间范围
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    history = [r for r in history if r["timestamp"] > cutoff]

    if not history:
        return {}

    # 统计
    health_scores = [r["health_score"] for r in history if "health_score" in r]
    cpu_temps = [r["cpu_temp"] for r in history if r.get("cpu_temp", 0) > 0]
    cpu_usages = [r["cpu_usage"] for r in history if "cpu_usage" in r]
    mem_usages = [r["mem_usage"] for r in history if "mem_usage" in r]

    return {
        "days": days,
        "records": len(history),
        "health_scores": health_scores,
        "cpu_temps": cpu_temps,
        "cpu_usages": cpu_usages,
        "mem_usages": mem_usages,
        "avg_health": sum(health_scores) / len(health_scores) if health_scores else 0,
        "avg_cpu_temp": sum(cpu_temps) / len(cpu_temps) if cpu_temps else 0,
        "avg_cpu_usage": sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0,
        "avg_mem_usage": sum(mem_usages) / len(mem_usages) if mem_usages else 0,
    }


# ══════════════════════════════════════════════════════════════════
# 综合检测
# ══════════════════════════════════════════════════════════════════


def check_system_health(
    check_docker: bool = True, services: Optional[List[str]] = None
) -> SystemHealthReport:
    """
    主入口：系统健康检测

    Args:
        check_docker: 是否检查 Docker
        services: 要检查的服务列表
    """
    report = SystemHealthReport(timestamp=datetime.now().isoformat())

    # 主机名
    report.hostname = _run("hostname 2>/dev/null") or "unknown"

    # 运行时间
    report.uptime_seconds, report.uptime_human = get_uptime()

    # CPU
    report.cpu = get_cpu_info()

    # 内存
    report.memory = get_memory_info()

    # 磁盘
    report.disks = get_disk_info()

    # Docker
    if check_docker:
        report.docker = get_docker_info()

    # 服务
    if services:
        report.services = get_services_info(services)

    # 计算健康分数
    report.health_score = calculate_system_health_score(report)

    # 收集问题
    # CPU 温度
    if report.cpu.temperature_c > 80:
        report.issues.append(f"CPU 温度过高: {report.cpu.temperature_c:.1f}°C")
    elif report.cpu.temperature_c > 70:
        report.warnings.append(f"CPU 温度偏高: {report.cpu.temperature_c:.1f}°C")

    # CPU 使用率
    if report.cpu.usage_percent > 90:
        report.issues.append(f"CPU 使用率过高: {report.cpu.usage_percent:.1f}%")
    elif report.cpu.usage_percent > 80:
        report.warnings.append(f"CPU 使用率偏高: {report.cpu.usage_percent:.1f}%")

    # 内存
    if report.memory.usage_percent > 95:
        report.issues.append(f"内存使用率过高: {report.memory.usage_percent:.1f}%")
    elif report.memory.usage_percent > 85:
        report.warnings.append(f"内存使用率偏高: {report.memory.usage_percent:.1f}%")

    # 磁盘
    for disk in report.disks:
        if disk.usage_percent > 95:
            report.issues.append(f"磁盘 {disk.mount_point} 使用率过高: {disk.usage_percent:.1f}%")
        elif disk.usage_percent > 85:
            report.warnings.append(f"磁盘 {disk.mount_point} 使用率偏高: {disk.usage_percent:.1f}%")

    # Docker
    if check_docker and report.docker.installed and not report.docker.running:
        report.warnings.append("Docker 已安装但未运行")

    # 服务
    for service in report.services:
        if service.status == ServiceStatus.FAILED:
            report.issues.append(f"服务 {service.name} 状态异常: failed")
        elif service.status == ServiceStatus.STOPPED and service.enabled:
            report.warnings.append(f"服务 {service.name} 已启用但未运行")

    # 综合判断
    report.ok = len(report.issues) == 0

    # 保存历史
    save_history(report)

    return report


def calculate_system_health_score(report: SystemHealthReport) -> int:
    """
    计算系统健康分数（0-100）

    评分规则：
    - 基础分 100
    - CPU 温度 > 80°C: -20
    - CPU 温度 > 70°C: -10
    - CPU 使用率 > 90%: -15
    - CPU 使用率 > 80%: -5
    - 内存使用率 > 95%: -20
    - 内存使用率 > 85%: -10
    - 磁盘使用率 > 95%: -15 每个
    - 磁盘使用率 > 85%: -5 每个
    - Docker 未运行: -5
    - 服务 failed: -10 每个
    """
    score = 100

    # CPU 温度
    if report.cpu.temperature_c > 80:
        score -= 20
    elif report.cpu.temperature_c > 70:
        score -= 10

    # CPU 使用率
    if report.cpu.usage_percent > 90:
        score -= 15
    elif report.cpu.usage_percent > 80:
        score -= 5

    # 内存
    if report.memory.usage_percent > 95:
        score -= 20
    elif report.memory.usage_percent > 85:
        score -= 10

    # 磁盘
    for disk in report.disks:
        if disk.usage_percent > 95:
            score -= 15
        elif disk.usage_percent > 85:
            score -= 5

    # Docker
    if report.docker.installed and not report.docker.running:
        score -= 5

    # 服务
    for service in report.services:
        if service.status == ServiceStatus.FAILED:
            score -= 10

    return max(0, min(100, score))


def format_report(report: SystemHealthReport, verbose: bool = False) -> str:
    """格式化报告为文本"""
    lines = []

    # 标题
    lines.append("=" * 60)
    lines.append("系统健康报告")
    lines.append(f"主机: {report.hostname}")
    lines.append(f"时间: {report.timestamp}")
    lines.append(f"运行时间: {report.uptime_human}")
    lines.append(f"健康分数: {report.health_score}/100")
    lines.append("=" * 60)
    lines.append("")

    # CPU
    lines.append("🖥️ CPU:")
    lines.append(f"  型号: {report.cpu.model or '未知'}")
    lines.append(f"  核心: {report.cpu.cores}")
    if report.cpu.frequency_mhz > 0:
        lines.append(f"  频率: {report.cpu.frequency_mhz:.0f} MHz")
    if report.cpu.temperature_c > 0:
        temp_icon = "🔥" if report.cpu.temperature_c > 70 else "✅"
        lines.append(f"  温度: {temp_icon} {report.cpu.temperature_c:.1f}°C")
    lines.append(f"  使用率: {report.cpu.usage_percent:.1f}%")
    lines.append(
        f"  负载: {report.cpu.load_avg_1:.2f}, {report.cpu.load_avg_5:.2f}, {report.cpu.load_avg_15:.2f}"
    )
    lines.append("")

    # 内存
    lines.append("💾 内存:")
    lines.append(f"  总量: {report.memory.total_mb:,} MB")
    lines.append(f"  已用: {report.memory.used_mb:,} MB ({report.memory.usage_percent:.1f}%)")
    lines.append(f"  可用: {report.memory.available_mb:,} MB")
    if report.memory.swap_total_mb > 0:
        lines.append(f"  Swap: {report.memory.swap_used_mb}/{report.memory.swap_total_mb} MB")
    lines.append("")

    # 磁盘
    if report.disks:
        lines.append("💿 磁盘:")
        for disk in report.disks:
            usage_icon = "⚠️" if disk.usage_percent > 85 else "✅"
            lines.append(
                f"  {usage_icon} {disk.mount_point}: {disk.used_gb:.1f}/{disk.total_gb:.1f} GB ({disk.usage_percent:.1f}%)"
            )
        lines.append("")

    # Docker
    if report.docker.installed:
        lines.append("🐳 Docker:")
        lines.append(f"  版本: {report.docker.version}")
        status_icon = "✅" if report.docker.running else "❌"
        lines.append(f"  状态: {status_icon} {'运行中' if report.docker.running else '未运行'}")
        if report.docker.running:
            lines.append(
                f"  容器: {report.docker.containers_running} 运行 / {report.docker.containers_stopped} 停止"
            )
            lines.append(f"  镜像: {report.docker.images_total}")
        lines.append("")

    # 服务
    if report.services:
        lines.append("⚙️ 服务:")
        for service in report.services:
            status_icon = (
                "✅"
                if service.status == ServiceStatus.RUNNING
                else "❌"
                if service.status == ServiceStatus.FAILED
                else "⏸️"
            )
            enabled_str = " (开机启动)" if service.enabled else ""
            lines.append(f"  {status_icon} {service.name}: {service.status.value}{enabled_str}")
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
        lines.append("✅ 系统健康状态良好")
    else:
        lines.append("❌ 系统需要维护")

    return "\n".join(lines)
