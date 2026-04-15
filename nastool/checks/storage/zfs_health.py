# -*- coding: utf-8 -*-
"""ZFS 存储池健康检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class ZFSHealthCheck(Check):
    check_id = "zfs_pool"
    title = "ZFS 存储池"
    description = "检测 ZFS 存储池状态（仅 ZFS 系统）"
    category = CheckCategory.STORAGE

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(["zpool", "status"], capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.INFO,
                    message="未使用 ZFS 存储",
                    current="not ZFS", expected="ZFS healthy",
                )
            issues = []
            for kw in ["DEGRADED", "FAULTED", "UNAVAIL"]:
                if kw in result.stdout:
                    issues.append(kw)
            if issues:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=False,
                    severity=CheckSeverity.CRITICAL,
                    message="; ".join(issues),
                    current="error", expected="healthy",
                    fix_available=True, fix_id="fix_zfs",
                    fix_description="检查 ZFS 存储池状态",
                    fix_risk="high",
                )
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.PASSED,
                message="ZFS 存储池健康",
                current="healthy", expected="healthy",
            )
        except FileNotFoundError:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.INFO,
                message="未使用 ZFS 存储",
                current="not ZFS", expected="ZFS healthy",
            )
        except Exception as e:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.INFO,
                message=f"ZFS 检测跳过: {str(e)}",
                current="unknown", expected="ZFS healthy",
            )
