# -*- coding: utf-8 -*-
"""SFTP 服务检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class SFTPServiceCheck(Check):
    check_id = "sftp_service"
    title = "SFTP 服务"
    description = "检测 SFTP (SSH File Transfer) 服务状态"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(["pgrep", "-f", "sshd"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message=f"SSH/SFTP 服务运行中",
                    current="running", expected="running",
                )
        except Exception:
            pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="SFTP 服务未运行",
            current="not running", expected="running",
        )
