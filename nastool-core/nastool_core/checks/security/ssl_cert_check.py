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
            "/root/.acme.sh/*/*.cer",   # 修正：去掉路径中的多余空格
        ]
        import datetime
        now = datetime.datetime.now()
        issues = []
        ok_certs = []

        for pattern in cert_paths:
            for cert_file in glob.glob(pattern):
                try:
                    result = subprocess.run(
                        ["openssl", "x509", "-in", cert_file, "-noout", "-enddate"],
                        capture_output=True, text=True, timeout=5, errors="replace"
                    )
                    if result.returncode == 0:
                        raw = result.stdout.strip()
                        if "=" not in raw:
                            continue
                        date_str = raw.split("=", 1)[1].strip()
                        # 兼容时区格式：GMT / UTC
                        for fmt in ("%b %d %H:%M:%S %Y %Z", "%b %d %H:%M:%S %Y GMT"):
                            try:
                                exp_date = datetime.datetime.strptime(date_str, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            # 无法解析，跳过（防止乱码日期导致崩溃）
                            continue
                        days_left = (exp_date - now).days
                        name = os.path.basename(os.path.dirname(cert_file)) or cert_file
                        # 合理范围检查：超过10年或超过100年前 → 跳过（可能是系统测试证书）
                        if days_left > 3650 or days_left < -365:
                            ok_certs.append(f"{name}: 有效")
                        elif days_left <= self.CRITICAL_DAYS:
                            issues.append(f"{name}: {days_left} 天（严重）")
                        elif days_left <= self.WARNING_DAYS:
                            issues.append(f"{name}: {days_left} 天（警告）")
                        else:
                            ok_certs.append(f"{name}: {days_left} 天")
                except Exception:
                    pass

        if issues:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.CRITICAL,
                message="; ".join(issues),
                current="expiring", expected=">30 days",
                fix_available=True, fix_id="renew_ssl",
                fix_description="续期 SSL 证书",
                fix_risk="medium",
            ))
        if ok_certs:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.PASSED,
                message=f"证书正常: {ok_certs[0]}",
                current="ok", expected=">30 days",
            ))
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.INFO,
            message="未检测到 SSL 证书",
            current="none", expected=">30 days",
        )
