# -*- coding: utf-8 -*-
"""NFS 服务状态检测"""

import subprocess

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class NFSServiceCheck(Check):
    """检测 NFS 服务状态"""

    check_id = "nfs_service"
    title = "NFS 服务状态"
    description = "检测 NFS 服务是否运行，导出目录是否可访问"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        # 检查 nfsd 进程
        try:
            result = subprocess.run(
                ["pgrep", "-f", "nfsd"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                process_count = len(result.stdout.strip().splitlines())
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message=f"NFS 服务运行中（{process_count} 个 nfsd 进程）",
                    current="running",
                    expected="running",
                )
        except Exception:
            pass

        # 检查 rpcbind / portmap
        try:
            result = subprocess.run(
                ["pgrep", "-f", "rpcbind"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.WARNING,
                    message="rpcbind 运行中但 NFS 服务未检测到",
                    current="partial",
                    expected="running",
                )
        except Exception:
            pass

        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="NFS 服务未运行",
            current="not running",
            expected="running",
            fix_available=True,
            fix_id="start_nfs",
            fix_command="systemctl start nfs-server",
            fix_description="启动 NFS 服务",
            fix_risk="medium",
        )
