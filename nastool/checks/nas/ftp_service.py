# -*- coding: utf-8 -*-
"""FTP 服务检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class FTPServiceCheck(Check):
    check_id = "ftp_service"
    title = "FTP 服务"
    description = "检测 FTP 服务状态（vsftpd/proftpd/pure-ftpd）"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        for proc in ["vsftpd", "proftpd", "pure-ftpd"]:
            try:
                result = subprocess.run(["pgrep", "-f", proc], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return CheckResult(
                        check_id=self.check_id, title=self.title,
                        category=self.category, passed=True,
                        severity=CheckSeverity.PASSED,
                        message=f"{proc} 运行中",
                        current="running", expected="running",
                    )
            except Exception:
                pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="FTP 服务未运行",
            current="not running", expected="running",
        )
