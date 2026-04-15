# -*- coding: utf-8 -*-
"""进程数量检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class ProcessCountCheck(Check):
    check_id = "process_count"
    title = "进程数量"
    description = "检测系统进程数量，发现进程泄露"
    category = CheckCategory.SYSTEM

    def run(self) -> CheckResult:
        count = 0
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                count = len(result.stdout.splitlines()) - 1
        except Exception:
            try:
                result = subprocess.run(
                    ["powershell", "-Command", "(Get-Process).Count"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    count = int(result.stdout.strip())
            except Exception:
                pass

        if count == 0:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.INFO,
                message="无法统计进程数量",
                current="unknown", expected="<500",
            )
        if count >= 500:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"进程数量 {count} 过多，可能存在进程泄露",
                current=f"{count} procs", expected="<500",
                fix_available=True, fix_id="check_procs",
                fix_description="检查异常进程",
                fix_risk="medium",
            )
        elif count >= 300:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.WARNING,
                message=f"进程数量 {count} 偏高",
                current=f"{count} procs", expected="<300",
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.PASSED,
            message=f"进程数量 {count}，正常",
            current=f"{count} procs", expected="<300",
        )
