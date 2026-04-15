# -*- coding: utf-8 -*-
"""
core/nas_health.py — NAS 系统健康检测
DSM 版本 / 账号 / 共享 / UPS / cron / 日志
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


class UPSStatus(Enum):
    """UPS 状态"""

    ONLINE = "online"  # 市电正常
    ON_BATTERY = "on_battery"  # 使用电池
    LOW_BATTERY = "low_battery"  # 低电量
    UNKNOWN = "unknown"


class ServiceStatus(Enum):
    """服务状态"""

    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class DSMInfo:
    """DSM 系统信息"""

    version: str = ""
    build: str = ""
    model: str = ""
    serial: str = ""
    uptime: str = ""
    temperature: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


@dataclass
class AccountInfo:
    """账号信息"""

    username: str
    uid: int = 0
    gid: int = 0
    home: str = ""
    shell: str = ""
    groups: List[str] = field(default_factory=list)
    last_login: str = ""
    is_admin: bool = False


@dataclass
class ShareInfo:
    """共享文件夹信息"""

    name: str
    path: str = ""
    size_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    usage_percent: float = 0.0
    permissions: str = ""
    nfs_enabled: bool = False
    smb_enabled: bool = False


@dataclass
class UPSInfo:
    """UPS 信息"""

    status: UPSStatus = UPSStatus.UNKNOWN
    model: str = ""
    battery_charge: int = 0
    battery_runtime: int = 0  # 秒
    load_percent: int = 0
    input_voltage: int = 0
    output_voltage: int = 0
    last_update: str = ""


@dataclass
class CronJob:
    """Cron 任务"""

    schedule: str
    command: str
    user: str = "root"
    enabled: bool = True
    last_run: str = ""
    next_run: str = ""


@dataclass
class LogEntry:
    """日志条目"""

    timestamp: str
    level: str
    source: str
    message: str


@dataclass
class NASHealthReport:
    """NAS 健康报告"""

    timestamp: str
    dsm: DSMInfo = field(default_factory=DSMInfo)
    accounts: List[AccountInfo] = field(default_factory=list)
    shares: List[ShareInfo] = field(default_factory=list)
    ups: UPSInfo = field(default_factory=UPSInfo)
    cron_jobs: List[CronJob] = field(default_factory=list)
    recent_logs: List[LogEntry] = field(default_factory=list)
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
            return f.read()
    except Exception as e:
        return ""


# ══════════════════════════════════════════════════════════════════
# DSM 系统信息
# ══════════════════════════════════════════════════════════════════


def get_dsm_info() -> DSMInfo:
    """获取 DSM 系统信息"""
    dsm = DSMInfo()

    # DSM 版本
    version_file = "/etc/synoinfo.conf"
    if os.path.exists(version_file):
        content = _read_file(version_file)
        for line in content.splitlines():
            if line.startswith("majorversion="):
                major = line.split("=")[1].strip('"')
            elif line.startswith("minorversion="):
                minor = line.split("=")[1].strip('"')
            elif line.startswith("buildnumber="):
                dsm.build = line.split("=")[1].strip('"')
            elif line.startswith("model="):
                dsm.model = line.split("=")[1].strip('"')
            elif line.startswith("serial="):
                dsm.serial = line.split("=")[1].strip('"')

        # 组合版本号
        if "major" in locals() and "minor" in locals():
            dsm.version = f"{major}.{minor}"

    # 运行时间
    uptime_str = _read_file("/proc/uptime")
    if uptime_str:
        uptime_seconds = int(float(uptime_str.split()[0]))
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        dsm.uptime = f"{days}天 {hours}小时"

    # 温度（群晖）
    temp_out = _run(
        "syno_temperature 2>/dev/null || cat /sys/class/hwmon/hwmon0/temp1_input 2>/dev/null"
    )
    if temp_out:
        try:
            dsm.temperature = int(temp_out) / 1000.0
        except Exception as e:
            pass

    # CPU 使用率
    dsm.cpu_usage = get_cpu_usage()

    # 内存使用率
    dsm.memory_usage = get_memory_usage()

    return dsm


def get_cpu_usage() -> float:
    """获取 CPU 使用率"""
    stat1 = _read_file("/proc/stat").splitlines()[0]
    if not stat1:
        return 0.0

    parts1 = stat1.split()[1:9]
    idle1 = int(parts1[3]) + int(parts1[4])
    total1 = sum(int(x) for x in parts1)

    time.sleep(0.5)

    stat2 = _read_file("/proc/stat").splitlines()[0]
    if not stat2:
        return 0.0

    parts2 = stat2.split()[1:9]
    idle2 = int(parts2[3]) + int(parts2[4])
    total2 = sum(int(x) for x in parts2)

    idle_delta = idle2 - idle1
    total_delta = total2 - total1

    if total_delta == 0:
        return 0.0

    return round(100.0 * (1 - idle_delta / total_delta), 1)


def get_memory_usage() -> float:
    """获取内存使用率"""
    meminfo = _read_file("/proc/meminfo")
    if not meminfo:
        return 0.0

    data = {}
    for line in meminfo.splitlines():
        match = re.match(r"(\w+):\s*(\d+)", line)
        if match:
            data[match.group(1)] = int(match.group(1))

    total = data.get("MemTotal", 0)
    available = data.get("MemAvailable", 0)

    if total == 0:
        return 0.0

    return round(100.0 * (total - available) / total, 1)


# ══════════════════════════════════════════════════════════════════
# 账号信息
# ══════════════════════════════════════════════════════════════════


def get_accounts() -> List[AccountInfo]:
    """获取系统账号列表"""
    accounts = []

    # 读取 /etc/passwd
    passwd = _read_file("/etc/passwd")
    if not passwd:
        return accounts

    for line in passwd.splitlines():
        parts = line.split(":")
        if len(parts) < 7:
            continue

        username = parts[0]
        uid = int(parts[2])
        gid = int(parts[3])
        home = parts[5]
        shell = parts[6]

        # 跳过系统账号
        if uid < 1000 and username not in ["admin", "nobody"]:
            continue

        account = AccountInfo(username=username, uid=uid, gid=gid, home=home, shell=shell)

        # 检查是否是管理员
        account.is_admin = uid == 0 or username == "admin"

        # 获取用户组
        groups_out = _run(f"groups {username} 2>/dev/null")
        if groups_out:
            account.groups = groups_out.split()[1:]  # 跳过用户名

        accounts.append(account)

    return accounts


def get_login_history(hours: int = 24) -> List[Dict[str, str]]:
    """获取登录历史"""
    logins = []

    # 从 last 命令获取
    last_out = _run(f"last -n 50 -x 2>/dev/null | head -50")
    if last_out:
        for line in last_out.splitlines():
            if not line.strip() or line.startswith("reboot") or line.startswith("wtmp"):
                continue

            parts = line.split()
            if len(parts) >= 4:
                logins.append(
                    {
                        "user": parts[0],
                        "terminal": parts[1],
                        "host": parts[2] if len(parts) > 2 else "",
                        "time": " ".join(parts[3:7]) if len(parts) > 6 else "",
                    }
                )

    return logins


# ══════════════════════════════════════════════════════════════════
# 共享文件夹
# ══════════════════════════════════════════════════════════════════


def get_shares() -> List[ShareInfo]:
    """获取共享文件夹列表"""
    shares = []

    # 群晖：从 /etc/samba/smb.conf 读取
    smb_conf = _read_file("/etc/samba/smb.conf")
    if smb_conf:
        current_share = None
        for line in smb_conf.splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                share_name = line[1:-1]
                if share_name not in ["global", "homes", "printers", "print$"]:
                    current_share = ShareInfo(name=share_name)
                    shares.append(current_share)
            elif current_share and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().lower()
                value = value.strip()

                if key == "path":
                    current_share.path = value
                elif key == "comment":
                    pass  # 可以用作描述

    # 获取每个共享的大小
    for share in shares:
        if share.path and os.path.exists(share.path):
            df_out = _run(f"df -BG {share.path} 2>/dev/null | tail -1")
            if df_out:
                parts = df_out.split()
                if len(parts) >= 4:
                    share.size_gb = float(parts[1].replace("G", ""))
                    share.used_gb = float(parts[2].replace("G", ""))
                    share.free_gb = float(parts[3].replace("G", ""))
                    if share.size_gb > 0:
                        share.usage_percent = round(100.0 * share.used_gb / share.size_gb, 1)

    return shares


def get_nfs_exports() -> List[Dict[str, str]]:
    """获取 NFS 导出"""
    exports = []

    exports_file = _read_file("/etc/exports")
    if exports_file:
        for line in exports_file.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if parts:
                exports.append({"path": parts[0], "clients": " ".join(parts[1:])})

    return exports


# ══════════════════════════════════════════════════════════════════
# UPS 信息
# ══════════════════════════════════════════════════════════════════


def get_ups_info() -> UPSInfo:
    """获取 UPS 信息"""
    ups = UPSInfo()

    # 检查 apcupsd
    apcaccess = _run("apcaccess 2>/dev/null")
    if apcaccess:
        ups.model = "APC UPS"
        ups.last_update = datetime.now().isoformat()

        for line in apcaccess.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().upper()
                value = value.strip()

                if key == "STATUS":
                    if "ONLINE" in value:
                        ups.status = UPSStatus.ONLINE
                    elif "ONBATT" in value:
                        ups.status = UPSStatus.ON_BATTERY
                    elif "LOWBATT" in value:
                        ups.status = UPSStatus.LOW_BATTERY
                elif key == "BCHARGE":
                    match = re.match(r"(\d+)", value)
                    if match:
                        ups.battery_charge = int(match.group(1))
                elif key == "TIMELEFT":
                    # 格式: 10.5 Minutes
                    match = re.match(r"([\d.]+)", value)
                    if match:
                        ups.battery_runtime = int(float(match.group(1)) * 60)
                elif key == "LOADPCT":
                    match = re.match(r"([\d.]+)", value)
                    if match:
                        ups.load_percent = int(float(match.group(1)))
                elif key == "LINEV":
                    match = re.match(r"(\d+)", value)
                    if match:
                        ups.input_voltage = int(match.group(1))
                elif key == "OUTPUTV":
                    match = re.match(r"(\d+)", value)
                    if match:
                        ups.output_voltage = int(match.group(1))

        return ups

    # 检查 nut (Network UPS Tools)
    upsc = _run("upsc -l 2>/dev/null | head -1")
    if upsc:
        ups_name = upsc.strip()
        ups_data = _run(f"upsc {ups_name} 2>/dev/null")

        if ups_data:
            ups.model = "NUT UPS"
            ups.last_update = datetime.now().isoformat()

            for line in ups_data.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    if key == "ups.status":
                        if "OL" in value:
                            ups.status = UPSStatus.ONLINE
                        elif "OB" in value:
                            ups.status = UPSStatus.ON_BATTERY
                        elif "LB" in value:
                            ups.status = UPSStatus.LOW_BATTERY
                    elif key == "battery.charge":
                        try:
                            ups.battery_charge = int(value)
                        except Exception as e:
                            pass
                    elif key == "battery.runtime":
                        try:
                            ups.battery_runtime = int(value)
                        except Exception as e:
                            pass
                    elif key == "ups.load":
                        try:
                            ups.load_percent = int(value)
                        except Exception as e:
                            pass

            return ups

    # 无 UPS
    return ups


# ══════════════════════════════════════════════════════════════════
# Cron 任务
# ══════════════════════════════════════════════════════════════════


def get_cron_jobs() -> List[CronJob]:
    """获取 Cron 任务列表"""
    jobs = []

    # 系统 crontab
    system_cron = _read_file("/etc/crontab")
    if system_cron:
        for line in system_cron.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) >= 6:
                schedule = " ".join(parts[:5])
                command = " ".join(parts[5:])
                user = "root"

                # 如果第 6 个字段是用户名
                if len(parts) >= 7 and parts[5] in ["root", "admin"]:
                    user = parts[5]
                    command = " ".join(parts[6:])

                job = CronJob(schedule=schedule, command=command, user=user)
                jobs.append(job)

    # 用户 crontab
    for user in ["root", "admin"]:
        crontab_out = _run(f"crontab -u {user} -l 2>/dev/null")
        if crontab_out:
            for line in crontab_out.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) >= 6:
                    schedule = " ".join(parts[:5])
                    command = " ".join(parts[5:])

                    job = CronJob(schedule=schedule, command=command, user=user)
                    jobs.append(job)

    return jobs


def check_cron_health(jobs: List[CronJob]) -> List[str]:
    """检查 Cron 任务健康"""
    issues = []

    # 检查是否有备份任务
    has_backup = any("backup" in j.command.lower() for j in jobs)
    if not has_backup:
        issues.append("未发现定时备份任务")

    # 检查是否有清理任务
    has_clean = any("clean" in j.command.lower() or "tmp" in j.command.lower() for j in jobs)
    if not has_clean:
        issues.append("未发现定时清理任务")

    return issues


# ══════════════════════════════════════════════════════════════════
# 日志
# ══════════════════════════════════════════════════════════════════


def get_recent_logs(hours: int = 1, limit: int = 100) -> List[LogEntry]:
    """获取最近日志"""
    logs = []

    log_files = [
        "/var/log/messages",
        "/var/log/syslog",
        "/var/log/synolog/synolog-ng.log",
        "/var/log/synolog/synolog-nginx.log",
    ]

    cutoff_time = datetime.now() - timedelta(hours=hours)

    for log_file in log_files:
        if not os.path.exists(log_file):
            continue

        try:
            # 使用 tail 读取最后 N 行
            tail_out = _run(f"tail -{limit * 2} {log_file} 2>/dev/null")

            for line in tail_out.splitlines():
                entry = parse_log_line(line)
                if entry:
                    logs.append(entry)

                if len(logs) >= limit:
                    break

        except Exception as e:
            pass

        if len(logs) >= limit:
            break

    return logs[:limit]


def parse_log_line(line: str) -> Optional[LogEntry]:
    """解析日志行"""
    # 格式: Apr 13 10:00:00 hostname process[pid]: message
    match = re.match(r"(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+(\S+):\s+(.+)", line)

    if match:
        return LogEntry(
            timestamp=match.group(1),
            level="info",  # 默认
            source=match.group(3),
            message=match.group(4),
        )

    return None


def analyze_logs(logs: List[LogEntry]) -> Dict[str, int]:
    """分析日志"""
    stats = {"error": 0, "warning": 0, "info": 0, "total": len(logs)}

    for log in logs:
        msg_lower = log.message.lower()

        if "error" in msg_lower or "fail" in msg_lower:
            stats["error"] += 1
            log.level = "error"
        elif "warn" in msg_lower:
            stats["warning"] += 1
            log.level = "warning"
        else:
            stats["info"] += 1

    return stats


# ══════════════════════════════════════════════════════════════════
# 综合检测
# ══════════════════════════════════════════════════════════════════


def check_nas_health(
    check_dsm: bool = True,
    check_accounts: bool = True,
    check_shares: bool = True,
    check_ups: bool = True,
    check_cron: bool = True,
    check_logs: bool = True,
) -> NASHealthReport:
    """
    主入口：NAS 健康检测

    Args:
        check_dsm: 是否检查 DSM 系统
        check_accounts: 是否检查账号
        check_shares: 是否检查共享文件夹
        check_ups: 是否检查 UPS
        check_cron: 是否检查 Cron
        check_logs: 是否检查日志
    """
    report = NASHealthReport(timestamp=datetime.now().isoformat())

    # 1. DSM 系统
    if check_dsm:
        report.dsm = get_dsm_info()

    # 2. 账号
    if check_accounts:
        report.accounts = get_accounts()

    # 3. 共享文件夹
    if check_shares:
        report.shares = get_shares()

    # 4. UPS
    if check_ups:
        report.ups = get_ups_info()

    # 5. Cron
    if check_cron:
        report.cron_jobs = get_cron_jobs()

    # 6. 日志
    if check_logs:
        report.recent_logs = get_recent_logs(hours=1)

    # 计算健康分数
    report.health_score = calculate_nas_health_score(report)

    # 收集问题
    # DSM
    if report.dsm.cpu_usage > 90:
        report.issues.append(f"CPU 使用率过高: {report.dsm.cpu_usage:.1f}%")
    elif report.dsm.cpu_usage > 80:
        report.warnings.append(f"CPU 使用率偏高: {report.dsm.cpu_usage:.1f}%")

    if report.dsm.memory_usage > 95:
        report.issues.append(f"内存使用率过高: {report.dsm.memory_usage:.1f}%")
    elif report.dsm.memory_usage > 85:
        report.warnings.append(f"内存使用率偏高: {report.dsm.memory_usage:.1f}%")

    # 共享文件夹
    for share in report.shares:
        if share.usage_percent > 95:
            report.issues.append(f"共享文件夹 {share.name} 空间不足: {share.usage_percent:.1f}%")
        elif share.usage_percent > 85:
            report.warnings.append(f"共享文件夹 {share.name} 空间紧张: {share.usage_percent:.1f}%")

    # UPS
    if report.ups.status == UPSStatus.ON_BATTERY:
        report.issues.append("UPS 使用电池供电")
    elif report.ups.status == UPSStatus.LOW_BATTERY:
        report.issues.append("UPS 电量过低")
    elif report.ups.status == UPSStatus.UNKNOWN:
        report.warnings.append("未检测到 UPS")

    # Cron
    cron_issues = check_cron_health(report.cron_jobs)
    for issue in cron_issues:
        report.warnings.append(f"Cron: {issue}")

    # 日志
    if report.recent_logs:
        log_stats = analyze_logs(report.recent_logs)
        if log_stats["error"] > 10:
            report.warnings.append(f"最近 1 小时有 {log_stats['error']} 条错误日志")

    # 综合判断
    report.ok = len(report.issues) == 0

    return report


def calculate_nas_health_score(report: NASHealthReport) -> int:
    """
    计算 NAS 健康分数（0-100）

    评分规则：
    - 基础分 100
    - CPU 使用率 > 90%: -15
    - 内存使用率 > 95%: -20
    - 共享空间 > 95%: -10 每个
    - UPS 使用电池: -20
    - UPS 低电量: -30
    """
    score = 100

    # CPU
    if report.dsm.cpu_usage > 90:
        score -= 15
    elif report.dsm.cpu_usage > 80:
        score -= 5

    # 内存
    if report.dsm.memory_usage > 95:
        score -= 20
    elif report.dsm.memory_usage > 85:
        score -= 10

    # 共享文件夹
    for share in report.shares:
        if share.usage_percent > 95:
            score -= 10
        elif share.usage_percent > 85:
            score -= 5

    # UPS
    if report.ups.status == UPSStatus.ON_BATTERY:
        score -= 20
    elif report.ups.status == UPSStatus.LOW_BATTERY:
        score -= 30

    return max(0, min(100, score))


def format_report(report: NASHealthReport, verbose: bool = False) -> str:
    """格式化报告为文本"""
    lines = []

    # 标题
    lines.append("=" * 60)
    lines.append("NAS 健康报告")
    lines.append(f"时间: {report.timestamp}")
    lines.append(f"健康分数: {report.health_score}/100")
    lines.append("=" * 60)
    lines.append("")

    # DSM
    lines.append("🖥️ DSM 系统:")
    lines.append(f"  版本: {report.dsm.version} (Build {report.dsm.build})")
    lines.append(f"  型号: {report.dsm.model}")
    lines.append(f"  运行时间: {report.dsm.uptime}")
    if report.dsm.temperature > 0:
        lines.append(f"  温度: {report.dsm.temperature:.1f}°C")
    lines.append(f"  CPU: {report.dsm.cpu_usage:.1f}%")
    lines.append(f"  内存: {report.dsm.memory_usage:.1f}%")
    lines.append("")

    # 账号
    if report.accounts:
        lines.append("👥 账号:")
        for account in report.accounts[:10]:
            admin_str = " (管理员)" if account.is_admin else ""
            lines.append(f"  - {account.username}{admin_str}")
        lines.append("")

    # 共享文件夹
    if report.shares:
        lines.append("📁 共享文件夹:")
        for share in report.shares:
            usage_str = f"{share.usage_percent:.1f}%" if share.usage_percent > 0 else "--"
            lines.append(
                f"  - {share.name}: {share.used_gb:.1f}/{share.size_gb:.1f} GB ({usage_str})"
            )
        lines.append("")

    # UPS
    lines.append("🔋 UPS:")
    if report.ups.status != UPSStatus.UNKNOWN:
        status_str = (
            "✅ 市电正常"
            if report.ups.status == UPSStatus.ONLINE
            else "⚠️ 使用电池"
            if report.ups.status == UPSStatus.ON_BATTERY
            else "❌ 低电量"
        )
        lines.append(f"  状态: {status_str}")
        lines.append(f"  电量: {report.ups.battery_charge}%")
        lines.append(f"  负载: {report.ups.load_percent}%")
    else:
        lines.append("  状态: 未检测到")
    lines.append("")

    # Cron
    if report.cron_jobs:
        lines.append("⏰ Cron 任务:")
        for job in report.cron_jobs[:10]:
            lines.append(f"  - [{job.schedule}] {job.command[:50]}")
        lines.append("")

    # 日志
    if report.recent_logs:
        log_stats = analyze_logs(report.recent_logs)
        lines.append("📋 日志统计（最近 1 小时）:")
        lines.append(f"  错误: {log_stats['error']}")
        lines.append(f"  警告: {log_stats['warning']}")
        lines.append(f"  信息: {log_stats['info']}")
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
        lines.append("✅ NAS 健康状态良好")
    else:
        lines.append("❌ NAS 需要维护")

    return "\n".join(lines)
