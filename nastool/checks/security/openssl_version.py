# -*- coding: utf-8 -*-
"""OpenSSL 版本检测"""
import subprocess, re
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class OpenSSLVersionCheck(Check):
    check_id = "openssl_version"
    title = "OpenSSL 版本"
    description = "检测 OpenSSL 版本，识别已知漏洞"
    category = CheckCategory.SECURITY

    KNOWN_BAD_PREFIXES = ["1.0.0", "1.0.1", "1.0.2"]
    MIN_SAFE = "1.1.1"

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(["openssl", "version"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.INFO,
                    message="OpenSSL 命令不可用",
                    current="unknown", expected="1.1.1+",
                )
            m = re.search(r"OpenSSL\s+(\d+\.\d+\.\d+[a-z]?)", result.stdout)
            version = m.group(1) if m else "unknown"
            for bad in self.KNOWN_BAD_PREFIXES:
                if version.startswith(bad):
                    return CheckResult(
                        check_id=self.check_id, title=self.title,
                        category=self.category, passed=False,
                        severity=CheckSeverity.CRITICAL,
                        message=f"OpenSSL {version} 存在已知漏洞",
                        current=version, expected="1.1.1+",
                        fix_available=True, fix_id="update_openssl",
                        fix_description="更新 OpenSSL 到最新版本",
                        fix_risk="high",
                    )
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.PASSED,
                message=f"OpenSSL {version}",
                current=version, expected="1.1.1+",
            )
        except Exception as e:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.INFO,
                message=f"OpenSSL 检测跳过: {str(e)}",
                current="unknown", expected="1.1.1+",
            )
