# -*- coding: utf-8 -*-
"""
core/security_health.py — 安全健康检测
登录失败 / 防火墙 / SSL / 自动更新 / SSH 加固
"""

import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class FirewallStatus(Enum):
    """防火墙状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    NOT_INSTALLED = "not_installed"
    UNKNOWN = "unknown"


class SSLStatus(Enum):
    """SSL 证书状态"""

    VALID = "valid"
    EXPIRED = "expired"
    EXPIRING_SOON = "expiring_soon"
    INVALID = "invalid"
    NOT_FOUND = "not_found"


@dataclass
class LoginFailure:
    """登录失败记录"""

    username: str
    ip: str
    timestamp: str
    service: str = "ssh"


@dataclass
class FirewallInfo:
    """防火墙信息"""

    status: FirewallStatus = FirewallStatus.UNKNOWN
    backend: str = ""  # ufw, firewalld, iptables
    open_ports: List[int] = field(default_factory=list)
    rules_count: int = 0
    default_policy: str = ""


@dataclass
class SSLCertificate:
    """SSL 证书信息"""

    domain: str
    status: SSLStatus = SSLStatus.NOT_FOUND
    issuer: str = ""
    subject: str = ""
    not_before: str = ""
    not_after: str = ""
    days_remaining: int = 0
    chain_valid: bool = False
    error: str = ""


@dataclass
class UpdateStatus:
    """更新状态"""

    security_updates: int = 0
    regular_updates: int = 0
    kernel_update: bool = False
    last_update: str = ""
    auto_update_enabled: bool = False
    reboot_required: bool = False


@dataclass
class SSHConfig:
    """SSH 配置"""

    permit_root_login: bool = True
    password_authentication: bool = True
    pubkey_authentication: bool = True
    port: int = 22
    max_auth_tries: int = 6
    empty_passwords: bool = False
    x11_forwarding: bool = False
    issues: List[str] = field(default_factory=list)


@dataclass
class SecurityHealthReport:
    """安全健康报告"""

    timestamp: str
    login_failures: List[LoginFailure] = field(default_factory=list)
    login_failure_count_24h: int = 0
    brute_force_ips: List[str] = field(default_factory=list)
    firewall: FirewallInfo = field(default_factory=FirewallInfo)
    ssl_certificates: List[SSLCertificate] = field(default_factory=list)
    updates: UpdateStatus = field(default_factory=UpdateStatus)
    ssh_config: SSHConfig = field(default_factory=SSHConfig)
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
# 登录失败检测
# ══════════════════════════════════════════════════════════════════


def get_login_failures(hours: int = 24, limit: int = 100) -> List[LoginFailure]:
    """
    获取登录失败记录

    Args:
        hours: 查询最近多少小时
        limit: 最大返回数量
    """
    failures = []

    # 从 /var/log/auth.log 或 /var/log/secure 读取
    log_paths = [
        "/var/log/auth.log",
        "/var/log/auth.log.1",
        "/var/log/secure",
        "/var/log/secure.1",
    ]

    cutoff_time = datetime.now() - timedelta(hours=hours)

    for log_path in log_paths:
        if not os.path.exists(log_path):
            continue

        try:
            with open(log_path, "r", errors="ignore") as f:
                for line in f:
                    # 解析失败日志
                    # 格式: Apr 13 10:00:00 hostname sshd[12345]: Failed password for user from 192.168.1.1 port 22 ssh2
                    if "Failed password" in line or "authentication failure" in line:
                        failure = parse_auth_log_line(line)
                        if failure:
                            failures.append(failure)

                    if len(failures) >= limit:
                        break

        except Exception as e:
            pass

        if len(failures) >= limit:
            break

    # 按时间排序（最新的在前）
    # 简单处理：直接返回
    return failures[:limit]


def parse_auth_log_line(line: str) -> Optional[LoginFailure]:
    """解析 auth.log 行"""
    # Failed password for user from 192.168.1.1 port 22 ssh2
    match = re.search(
        r"Failed password for (?:invalid user )?(\S+) from (\d+\.\d+\.\d+\.\d+)", line
    )
    if match:
        # 解析时间
        # Apr 13 10:00:00
        time_match = re.match(r"(\w+\s+\d+\s+\d+:\d+:\d+)", line)
        timestamp = time_match.group(1) if time_match else ""

        return LoginFailure(
            username=match.group(1), ip=match.group(2), timestamp=timestamp, service="ssh"
        )

    return None


def detect_brute_force(failures: List[LoginFailure], threshold: int = 5) -> List[str]:
    """
    检测暴力破解 IP

    Args:
        failures: 登录失败记录
        threshold: 失败次数阈值
    """
    ip_counts: Dict[str, int] = {}

    for f in failures:
        ip_counts[f.ip] = ip_counts.get(f.ip, 0) + 1

    brute_force_ips = [ip for ip, count in ip_counts.items() if count >= threshold]
    return brute_force_ips


# ══════════════════════════════════════════════════════════════════
# 防火墙检测
# ══════════════════════════════════════════════════════════════════


def get_firewall_info() -> FirewallInfo:
    """获取防火墙信息"""
    fw = FirewallInfo()

    # 检查 ufw
    ufw_status = _run("ufw status 2>/dev/null")
    if ufw_status:
        fw.backend = "ufw"

        if "Status: active" in ufw_status:
            fw.status = FirewallStatus.ACTIVE
        elif "Status: inactive" in ufw_status:
            fw.status = FirewallStatus.INACTIVE

        # 解析开放端口
        for line in ufw_status.splitlines():
            match = re.match(r"(\d+)/tcp\s+ALLOW", line)
            if match:
                fw.open_ports.append(int(match.group(1)))

        # 规则数量
        fw.rules_count = len([l for l in ufw_status.splitlines() if "ALLOW" in l or "DENY" in l])

        # 默认策略
        default_out = _run("ufw status verbose 2>/dev/null | grep Default")
        if default_out:
            fw.default_policy = default_out

        return fw

    # 检查 firewalld
    firewalld_status = _run("systemctl is-active firewalld 2>/dev/null")
    if firewalld_status == "active":
        fw.backend = "firewalld"
        fw.status = FirewallStatus.ACTIVE

        # 获取开放端口
        ports_out = _run("firewall-cmd --list-ports 2>/dev/null")
        if ports_out:
            for port_str in ports_out.split():
                match = re.match(r"(\d+)/tcp", port_str)
                if match:
                    fw.open_ports.append(int(match.group(1)))

        return fw

    # 检查 iptables
    iptables_out = _run("iptables -L -n 2>/dev/null | head -20")
    if iptables_out:
        fw.backend = "iptables"
        # 简单判断是否有规则
        if "ACCEPT" in iptables_out or "DROP" in iptables_out:
            fw.status = FirewallStatus.ACTIVE
            fw.rules_count = len([l for l in iptables_out.splitlines() if l.strip()])

        return fw

    # 无防火墙
    fw.status = FirewallStatus.NOT_INSTALLED
    return fw


# ══════════════════════════════════════════════════════════════════
# SSL 证书检测
# ══════════════════════════════════════════════════════════════════


def check_ssl_certificate(domain: str, port: int = 443) -> SSLCertificate:
    """
    检查 SSL 证书

    Args:
        domain: 域名
        port: 端口
    """
    cert = SSLCertificate(domain=domain)

    # 使用 openssl 检查
    cmd = f"echo | openssl s_client -connect {domain}:{port} -servername {domain} 2>/dev/null | openssl x509 -noout -dates -issuer -subject 2>/dev/null"
    output = _run(cmd, timeout=10)

    if not output:
        cert.status = SSLStatus.NOT_FOUND
        return cert

    # 解析输出
    for line in output.splitlines():
        if "notBefore=" in line:
            match = re.search(r"notBefore=(.+)", line)
            if match:
                cert.not_before = match.group(1).strip()
        elif "notAfter=" in line:
            match = re.search(r"notAfter=(.+)", line)
            if match:
                cert.not_after = match.group(1).strip()
        elif "issuer=" in line:
            match = re.search(r"issuer=(.+)", line)
            if match:
                cert.issuer = match.group(1).strip()
        elif "subject=" in line:
            match = re.search(r"subject=(.+)", line)
            if match:
                cert.subject = match.group(1).strip()

    # 计算剩余天数
    if cert.not_after:
        try:
            # 解析时间格式: Apr 13 10:00:00 2026 GMT
            not_after = datetime.strptime(cert.not_after, "%b %d %H:%M:%S %Y %Z")
            cert.days_remaining = (not_after - datetime.now()).days

            if cert.days_remaining < 0:
                cert.status = SSLStatus.EXPIRED
            elif cert.days_remaining < 30:
                cert.status = SSLStatus.EXPIRING_SOON
            else:
                cert.status = SSLStatus.VALID
        except Exception as e:
            cert.status = SSLStatus.INVALID

    return cert


def check_ssl_certificates(domains: List[str]) -> List[SSLCertificate]:
    """检查多个域名的 SSL 证书"""
    return [check_ssl_certificate(d) for d in domains]


# ══════════════════════════════════════════════════════════════════
# 自动更新检测
# ══════════════════════════════════════════════════════════════════


def get_update_status() -> UpdateStatus:
    """获取更新状态"""
    status = UpdateStatus()

    # 检查可用的安全更新
    # apt
    apt_check = _run("apt list --upgradable 2>/dev/null | grep -i security | wc -l")
    if apt_check:
        try:
            status.security_updates = int(apt_check)
        except Exception as e:
            pass

    # 检查所有可更新包
    all_updates = _run("apt list --upgradable 2>/dev/null | wc -l")
    if all_updates:
        try:
            status.regular_updates = int(all_updates) - 1  # 减去标题行
        except Exception as e:
            pass

    # 检查内核更新
    kernel_check = _run("apt list --upgradable 2>/dev/null | grep -i linux-image")
    status.kernel_update = bool(kernel_check)

    # 检查自动更新是否启用
    # unattended-upgrades
    auto_update_config = _read_file("/etc/apt/apt.conf.d/20auto-upgrades")
    if auto_update_config:
        status.auto_update_enabled = (
            'Update-Package-Lists "1"' in auto_update_config
            and 'Unattended-Upgrade "1"' in auto_update_config
        )

    # 检查是否需要重启
    reboot_required = os.path.exists("/var/run/reboot-required")
    status.reboot_required = reboot_required

    # 最后更新时间
    log_path = "/var/log/apt/history.log"
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if "Start-Date:" in line:
                        match = re.search(r"Start-Date:\s+(.+)", line)
                        if match:
                            status.last_update = match.group(1).strip()
                        break
        except Exception as e:
            pass

    return status


# ══════════════════════════════════════════════════════════════════
# SSH 配置检测
# ══════════════════════════════════════════════════════════════════


def get_ssh_config() -> SSHConfig:
    """获取 SSH 配置"""
    config = SSHConfig()

    sshd_config = _read_file("/etc/ssh/sshd_config")
    if not sshd_config:
        return config

    # 解析配置
    for line in sshd_config.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        key = parts[0].lower()
        value = parts[1].lower()

        if key == "permitrootlogin":
            config.permit_root_login = value in ("yes", "prohibit-password", "without-password")
        elif key == "passwordauthentication":
            config.password_authentication = value == "yes"
        elif key == "pubkeyauthentication":
            config.pubkey_authentication = value == "yes"
        elif key == "port":
            try:
                config.port = int(parts[1])
            except Exception as e:
                pass
        elif key == "maxauthtries":
            try:
                config.max_auth_tries = int(parts[1])
            except Exception as e:
                pass
        elif key == "permitemptypasswords":
            config.empty_passwords = value == "yes"
        elif key == "x11forwarding":
            config.x11_forwarding = value == "yes"

    # 检查安全问题
    if config.permit_root_login:
        config.issues.append("允许 root 登录")
    if config.password_authentication:
        config.issues.append("允许密码认证（建议仅使用密钥）")
    if config.empty_passwords:
        config.issues.append("允许空密码")
    if config.max_auth_tries > 3:
        config.issues.append(f"最大认证尝试次数过高 ({config.max_auth_tries})")
    if config.port == 22:
        config.issues.append("使用默认端口 22（建议修改）")

    return config


# ══════════════════════════════════════════════════════════════════
# 综合检测
# ══════════════════════════════════════════════════════════════════


def check_security_health(
    check_login_failures: bool = True,
    check_firewall: bool = True,
    check_ssl: bool = False,
    ssl_domains: Optional[List[str]] = None,
    check_updates: bool = True,
    check_ssh: bool = True,
) -> SecurityHealthReport:
    """
    主入口：安全健康检测

    Args:
        check_login_failures: 是否检查登录失败
        check_firewall: 是否检查防火墙
        check_ssl: 是否检查 SSL 证书
        ssl_domains: 要检查的域名列表
        check_updates: 是否检查更新
        check_ssh: 是否检查 SSH 配置
    """
    report = SecurityHealthReport(timestamp=datetime.now().isoformat())

    # 1. 登录失败
    if check_login_failures:
        report.login_failures = get_login_failures(hours=24)
        report.login_failure_count_24h = len(report.login_failures)
        report.brute_force_ips = detect_brute_force(report.login_failures)

    # 2. 防火墙
    if check_firewall:
        report.firewall = get_firewall_info()

    # 3. SSL 证书
    if check_ssl and ssl_domains:
        report.ssl_certificates = check_ssl_certificates(ssl_domains)

    # 4. 更新
    if check_updates:
        report.updates = get_update_status()

    # 5. SSH 配置
    if check_ssh:
        report.ssh_config = get_ssh_config()

    # 计算健康分数
    report.health_score = calculate_security_health_score(report)

    # 收集问题
    # 登录失败
    if report.login_failure_count_24h > 50:
        report.issues.append(f"24小时内登录失败次数过多: {report.login_failure_count_24h}")
    elif report.login_failure_count_24h > 20:
        report.warnings.append(f"24小时内登录失败次数偏高: {report.login_failure_count_24h}")

    # 暴力破解
    if report.brute_force_ips:
        report.warnings.append(f"检测到 {len(report.brute_force_ips)} 个暴力破解 IP")

    # 防火墙
    if report.firewall.status == FirewallStatus.INACTIVE:
        report.issues.append("防火墙未启用")
    elif report.firewall.status == FirewallStatus.NOT_INSTALLED:
        report.warnings.append("未检测到防火墙")

    # SSL 证书
    for cert in report.ssl_certificates:
        if cert.status == SSLStatus.EXPIRED:
            report.issues.append(f"SSL 证书已过期: {cert.domain}")
        elif cert.status == SSLStatus.EXPIRING_SOON:
            report.warnings.append(
                f"SSL 证书即将过期: {cert.domain}（剩余 {cert.days_remaining} 天）"
            )

    # 更新
    if report.updates.security_updates > 0:
        report.issues.append(f"有 {report.updates.security_updates} 个安全更新待安装")
    if report.updates.reboot_required:
        report.warnings.append("系统需要重启以完成更新")

    # SSH 配置
    for issue in report.ssh_config.issues:
        report.warnings.append(f"SSH: {issue}")

    # 综合判断
    report.ok = len(report.issues) == 0

    return report


def calculate_security_health_score(report: SecurityHealthReport) -> int:
    """
    计算安全健康分数（0-100）

    评分规则：
    - 基础分 100
    - 防火墙未启用: -20
    - 无防火墙: -10
    - SSH 允许 root 登录: -10
    - SSH 允许密码认证: -5
    - 登录失败 > 50: -15
    - 登录失败 > 20: -5
    - 暴力破解 IP > 0: -5 每个（最多 -20）
    - SSL 证书过期: -20 每个
    - SSL 证书即将过期: -5 每个
    - 安全更新待安装: -10
    """
    score = 100

    # 防火墙
    if report.firewall.status == FirewallStatus.INACTIVE:
        score -= 20
    elif report.firewall.status == FirewallStatus.NOT_INSTALLED:
        score -= 10

    # SSH
    if report.ssh_config.permit_root_login:
        score -= 10
    if report.ssh_config.password_authentication:
        score -= 5

    # 登录失败
    if report.login_failure_count_24h > 50:
        score -= 15
    elif report.login_failure_count_24h > 20:
        score -= 5

    # 暴力破解
    brute_force_penalty = min(len(report.brute_force_ips) * 5, 20)
    score -= brute_force_penalty

    # SSL 证书
    for cert in report.ssl_certificates:
        if cert.status == SSLStatus.EXPIRED:
            score -= 20
        elif cert.status == SSLStatus.EXPIRING_SOON:
            score -= 5

    # 安全更新
    if report.updates.security_updates > 0:
        score -= 10

    return max(0, min(100, score))


def format_report(report: SecurityHealthReport, verbose: bool = False) -> str:
    """格式化报告为文本"""
    lines = []

    # 标题
    lines.append("=" * 60)
    lines.append("安全健康报告")
    lines.append(f"时间: {report.timestamp}")
    lines.append(f"健康分数: {report.health_score}/100")
    lines.append("=" * 60)
    lines.append("")

    # 登录失败
    lines.append("🔐 登录失败（24小时）:")
    lines.append(f"  失败次数: {report.login_failure_count_24h}")
    if report.brute_force_ips:
        lines.append(f"  暴力破解 IP: {', '.join(report.brute_force_ips[:10])}")
    if verbose and report.login_failures:
        lines.append("  最近失败:")
        for f in report.login_failures[:10]:
            lines.append(f"    - {f.username}@{f.ip} ({f.timestamp})")
    lines.append("")

    # 防火墙
    lines.append("🔥 防火墙:")
    lines.append(f"  后端: {report.firewall.backend or '未检测到'}")
    status_str = (
        "✅ 已启用"
        if report.firewall.status == FirewallStatus.ACTIVE
        else "❌ 未启用"
        if report.firewall.status == FirewallStatus.INACTIVE
        else "⚠️ 未安装"
        if report.firewall.status == FirewallStatus.NOT_INSTALLED
        else "未知"
    )
    lines.append(f"  状态: {status_str}")
    if report.firewall.open_ports:
        lines.append(f"  开放端口: {', '.join(map(str, report.firewall.open_ports))}")
    lines.append("")

    # SSL 证书
    if report.ssl_certificates:
        lines.append("🔒 SSL 证书:")
        for cert in report.ssl_certificates:
            status_str = (
                "✅ 有效"
                if cert.status == SSLStatus.VALID
                else "❌ 已过期"
                if cert.status == SSLStatus.EXPIRED
                else "⚠️ 即将过期"
                if cert.status == SSLStatus.EXPIRING_SOON
                else "无效"
            )
            lines.append(f"  {status_str} {cert.domain}: 剩余 {cert.days_remaining} 天")
        lines.append("")

    # 更新
    lines.append("📦 系统更新:")
    lines.append(f"  安全更新: {report.updates.security_updates}")
    lines.append(f"  常规更新: {report.updates.regular_updates}")
    lines.append(
        f"  自动更新: {'✅ 已启用' if report.updates.auto_update_enabled else '❌ 未启用'}"
    )
    if report.updates.reboot_required:
        lines.append("  ⚠️ 需要重启")
    lines.append("")

    # SSH 配置
    lines.append("🔑 SSH 配置:")
    lines.append(f"  端口: {report.ssh_config.port}")
    lines.append(f"  Root 登录: {'❌ 允许' if report.ssh_config.permit_root_login else '✅ 禁止'}")
    lines.append(
        f"  密码认证: {'⚠️ 允许' if report.ssh_config.password_authentication else '✅ 仅密钥'}"
    )
    lines.append(f"  最大尝试: {report.ssh_config.max_auth_tries}")
    if report.ssh_config.issues:
        lines.append("  问题:")
        for issue in report.ssh_config.issues:
            lines.append(f"    - {issue}")
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
        lines.append("✅ 安全状态良好")
    else:
        lines.append("❌ 存在安全隐患")

    return "\n".join(lines)
