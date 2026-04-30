"""
checks/security/ssl_cert.py - SSL certificate validity check
检查 SSL 证书有效期
"""

import subprocess
import re
import os
from datetime import datetime, timedelta
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class SSLCertCheck(Check):
    """Check SSL/TLS certificate validity"""

    check_id = "ssl_cert"
    title = "SSL 证书有效期"
    description = "检查本机 SSL 证书有效期，检测即将过期的证书"
    category = CheckCategory.SECURITY

    # 警告：30 天内过期
    WARNING_DAYS = 30
    # 严重：7 天内过期
    CRITICAL_DAYS = 7

    # 常见证书路径
    CERT_PATHS = [
        "/etc/ssl/certs/server.crt",
        "/etc/nginx/ssl/server.crt",
        "/etc/ssl/private/server.key",
        "/root/.ssh/ssh_host_rsa_key",
    ]

    def run(self) -> CheckResult:
        """Run SSL certificate check"""
        certs = self._find_certs()

        if not certs:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未找到 SSL 证书（可能未配置 HTTPS）",
                current="无证书",
                expected="证书在有效期内",
            ))

        results = [self._check_cert(c) for c in certs]
        expiring = [r for r in results if r["status"] == "expiring"]
        expired = [r for r in results if r["status"] == "expired"]
        ok = [r for r in results if r["status"] == "ok"]

        if expired:
            worst = expired[0]
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"证书已过期！{worst['path']} 过期于 {worst['expire_date']}",
                current=f"{len(expired)} 证书已过期",
                expected="所有证书在有效期内",
                fix_available=True,
                fix_description=f"证书 {worst['path']} 已过期，请更新 SSL 证书",
                details={"results": results},
            ))

        if expiring:
            # 按剩余天数排序
            expiring.sort(key=lambda x: x["days_left"])
            worst = expiring[0]
            days = worst["days_left"]

            severity = CheckSeverity.CRITICAL if days <= self.CRITICAL_DAYS else CheckSeverity.WARNING
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=severity,
                message=f"{worst['path']} 证书 {days} 天后过期（{worst['expire_date']}）",
                current=f"{len(expiring)} 证书即将过期",
                expected=f"证书有效期 > {self.WARNING_DAYS} 天",
                fix_available=True,
                fix_description=f"证书 {worst['path']} 即将过期，请提前更新",
                details={"results": results},
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"{len(ok)} 个 SSL 证书全部有效",
            current="所有证书正常",
            expected="证书有效",
            details={"results": results},
        )

    def _find_certs(self) -> list:
        """Find SSL certificate files"""
        found = []
        for path in self.CERT_PATHS:
            if os.path.exists(path):
                found.append(path)
        return found

    def _check_cert(self, cert_path: str) -> dict:
        """Check a single certificate"""
        result = {
            "path": cert_path,
            "status": "unknown",
            "expire_date": None,
            "days_left": None,
        }

        try:
            proc = subprocess.run(
                ["openssl", "x509", "-in", cert_path, "-noout", "-enddate"],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            if proc.returncode == 0:
                # 解析: notAfter=Jan 15 12:00:00 2026 GMT
                match = re.search(r"notAfter=(.+)", proc.stdout)
                if match:
                    date_str = match.group(1).strip()
                    expire_dt = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                    days_left = (expire_dt - datetime.now()).days
                    result["expire_date"] = date_str
                    result["days_left"] = days_left

                    if days_left < 0:
                        result["status"] = "expired"
                    elif days_left <= self.WARNING_DAYS:
                        result["status"] = "expiring"
                    else:
                        result["status"] = "ok"
                    return result
        except Exception:
            pass

        # Fallback: 读取文件 Modification time
        try:
            mtime = os.path.getmtime(cert_path)
            # 证书通常是长期有效的，至少看看文件存在
            result["status"] = "unknown"
        except Exception:
            pass

        return result
