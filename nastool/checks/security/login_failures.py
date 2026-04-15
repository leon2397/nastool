from typing import Optional
"""
checks/security/login_failures.py - SSH login failure check
检测 SSH 登录失败次数，识别暴力破解攻击
"""

import subprocess
import re
from datetime import datetime, timedelta
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class LoginFailuresCheck(Check):
    """Check SSH login failure attempts"""

    check_id = "login_failures"
    title = "SSH 登录失败检测"
    description = "分析 SSH 登录日志，检测暴力破解和异常登录"
    category = CheckCategory.SECURITY

    # 警告阈值：最近 N 小时内的失败次数
    WARNING_FAIL_COUNT = 10
    CRITICAL_FAIL_COUNT = 50

    def run(self) -> CheckResult:
        """Run login failure check"""
        # 尝试多种日志源
        failures = self._get_auth_failures()

        if failures is None:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="无法读取登录日志（权限不足或无日志文件）",
                current="无法分析",
                expected="能够读取 /var/log/auth 或 /var/log/secure",
            )

        if not failures:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.PASSED,
                message="近期无登录失败记录",
                current="0 次失败",
                expected="少量失败或无失败",
            )

        total = len(failures)
        by_ip = self._group_by_ip(failures)
        by_user = self._group_by_user(failures)

        # 找最高频来源
        top_ip = max(by_ip.items(), key=lambda x: len(x[1])) if by_ip else (None, [])
        top_user = max(by_user.items(), key=lambda x: len(x[1])) if by_user else (None, [])

        # 判断严重程度
        if total >= self.CRITICAL_FAIL_COUNT:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"检测到 {total} 次登录失败！疑似暴力破解（来源: {top_ip[0]}）",
                current=f"{total} 次失败",
                expected=f"< {self.WARNING_FAIL_COUNT} 次",
                fix_available=True,
                fix_description=f"发现 {total} 次 SSH 登录失败，建议：1) 使用密钥登录替代密码；2) 启用 fail2ban；3) 修改 SSH 端口",
                details={
                    "total_failures": total,
                    "top_ip": {"ip": top_ip[0], "count": len(top_ip[1])},
                    "top_user": {"user": top_user[0], "count": len(top_user[1])},
                    "by_ip": {ip: len(f) for ip, f in by_ip.items()},
                    "by_user": {u: len(f) for u, f in by_user.items()},
                },
            )

        if total >= self.WARNING_FAIL_COUNT:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"检测到 {total} 次登录失败",
                current=f"{total} 次失败",
                expected=f"< {self.WARNING_FAIL_COUNT} 次",
                details={
                    "total_failures": total,
                    "top_ip": {"ip": top_ip[0], "count": len(top_ip[1])},
                    "by_ip": {ip: len(f) for ip, f in by_ip.items()},
                },
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"登录失败次数正常（{total} 次，均为正常操作）",
            current=f"{total} 次失败",
            expected=f"< {self.WARNING_FAIL_COUNT} 次",
            details={"total_failures": total},
        )

    def _get_auth_failures(self) -> Optional[list]:
        """Get recent SSH auth failure entries"""
        failures = []

        # 常见日志路径
        log_files = [
            "/var/log/auth.log",
            "/var/log/secure",
            "/var/log/auth.log.1",
            "/var/log/secure.1",
        ]

        log_content = ""
        for log_file in log_files:
            try:
                result = subprocess.run(
                    ["sudo", "tail", "-n", "500", log_file],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0 and result.stdout:
                    log_content += result.stdout + "\n"
                    break
            except Exception:
                pass

        if not log_content:
            # 尝试 journalctl
            try:
                result = subprocess.run(
                    ["journalctl", "-u", "ssh", "--no-pager", "-n", "500"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    log_content = result.stdout
            except Exception:
                pass

        if not log_content:
            return None

        # 解析失败记录
        for line in log_content.splitlines():
            if self._is_failed_login(line):
                info = self._parse_failed_login(line)
                if info:
                    failures.append(info)

        # 限制为最近 24 小时
        cutoff = datetime.now() - timedelta(hours=24)
        recent = [f for f in failures if f.get("time", datetime.min) > cutoff]
        return recent

    def _is_failed_login(self, line: str) -> bool:
        """Check if a log line is a failed login"""
        fail_patterns = [
            "Failed password",
            "Failed publickey",
            "authentication failure",
            "BREAK-IN",
            "Invalid user",
            "ROOT LOGIN REFUSED",
        ]
        return any(p in line for p in fail_patterns)

    def _parse_failed_login(self, line: str) -> dict:
        """Parse a failed login log line"""
        info = {"raw": line.strip()}

        # 提取 IP
        ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
        if ip_match:
            info["ip"] = ip_match.group(1)

        # 提取用户名
        user_match = re.search(r"(?:user|from)\s+(\S+)", line, re.IGNORECASE)
        if user_match:
            info["user"] = user_match.group(1)
        else:
            user_match2 = re.search(r"Invalid user\s+(\S+)", line)
            if user_match2:
                info["user"] = user_match2.group(1)

        # 提取时间
        time_match = re.search(r"(\w{3}\s+\d+\s+\d+:\d+:\d+)", line)
        if time_match:
            try:
                info["time"] = datetime.strptime(time_match.group(1), "%b %d %H:%M:%S")
                info["time"] = info["time"].replace(year=datetime.now().year)
            except Exception:
                info["time"] = datetime.now()

        return info

    def _group_by_ip(self, failures: list) -> dict:
        """Group failures by source IP"""
        groups = {}
        for f in failures:
            ip = f.get("ip", "unknown")
            if ip not in groups:
                groups[ip] = []
            groups[ip].append(f)
        return groups

    def _group_by_user(self, failures: list) -> dict:
        """Group failures by username"""
        groups = {}
        for f in failures:
            user = f.get("user", "unknown")
            if user not in groups:
                groups[user] = []
            groups[user].append(f)
        return groups
