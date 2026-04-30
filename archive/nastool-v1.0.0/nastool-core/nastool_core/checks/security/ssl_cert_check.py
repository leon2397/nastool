# -*- coding: utf-8 -*-
"""SSL 证书有效期检测"""
import subprocess, os, glob
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class SSLCertCheck(Check):
    check_id = "ssl_cert_days"
    title = "SSL 证书"
    description = "检测 SSL 证书剩余有效期"
    category = CheckCategory.SECURITY

    WARNING_DAYS = 30
    CRITICAL_DAYS = 7

    def run(self) -> CheckResult:
        cert_paths = [
            "/etc/ssl/certs/*.pem",
            "/etc/nginx/*.pem",
            "/etc/letsencrypt/live/*/fullchain.pem",
            "/root/.acme.sh/*/ *.cer",
        ]
        import datetime
        import re
        now = datetime.datetime.now(datetime.timezone.utc)
        issues = []
        ok_certs = []

        for pattern in cert_paths:
            for cert_file in glob.glob(pattern):
                try:
                    result = subprocess.run(
                        ["openssl", "x509", "-in", cert_file, "-noout", "-enddate"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        date_str = result.stdout.split("=")[1].strip()
                        # 移除时区部分，因为%Z在Python中处理不可靠
                        date_str_no_tz = re.sub(r'\s+[A-Z]+$', '', date_str)
                        # 解析日期（不包含时区）
                        exp_date = datetime.datetime.strptime(date_str_no_tz, "%b %d %H:%M:%S %Y")
                        # 假设证书日期是UTC时间
                        exp_date = exp_date.replace(tzinfo=datetime.timezone.utc)
                        # 计算剩余天数
                        days_left = (exp_date - now).days
                        name = os.path.basename(os.path.dirname(cert_file)) or cert_file
                        if days_left <= self.CRITICAL_DAYS:
                            issues.append(f"{name}: {days_left} 天（严重）")
                        elif days_left <= self.WARNING_DAYS:
                            issues.append(f"{name}: {days_left} 天（警告）")
                        else:
                            ok_certs.append(f"{name}: {days_left} 天")
                except Exception as e:
                    # 记录异常但继续处理其他证书
                    pass

        if issues:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.CRITICAL,
                message="; ".join(issues),
                current="expiring", expected=">30 days",
                fix_available=True, fix_id="renew_ssl",
                fix_description="续期 SSL 证书",
                fix_risk="medium",
            )
        if ok_certs:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.PASSED,
                message=f"证书正常: {ok_certs[0]}",
                current="ok", expected=">30 days",
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.INFO,
            message="未检测到 SSL 证书",
            current="none", expected=">30 days",
        )
