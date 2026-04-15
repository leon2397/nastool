# -*- coding: utf-8 -*-
"""SMB/CIFS 服务检测"""

import subprocess

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class SMBServiceCheck(Check):
    """检测 SMB/CIFS 服务状态"""

    check_id = "smb_service"
    title = "SMB 服务状态"
    description = "检测 Samba (smbd) 服务是否运行"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        # 检查 smbd 进程
        try:
            result = subprocess.run(
                ["pgrep", "-f", "smbd"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                processes = len(result.stdout.strip().splitlines())
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message=f"SMB 服务运行中（{processes} 个进程）",
                    current="running",
                    expected="running",
                )
        except Exception:
            pass

        # Windows: 检查服务
        try:
            result = subprocess.run(
                ["sc", "query", "LanmanServer"],
                capture_output=True, text=True, timeout=10
            )
            if "RUNNING" in result.stdout or "START_PENDING" in result.stdout:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message="SMB 服务运行中（Windows Server 服务）",
                    current="running",
                    expected="running",
                )
        except Exception:
            pass

        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="SMB 服务未运行",
            current="not running",
            expected="running",
        )
