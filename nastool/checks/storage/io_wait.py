# -*- coding: utf-8 -*-
"""IO Wait 检测"""
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class IOWaitCheck(Check):
    check_id = "io_wait"
    title = "IO Wait"
    description = "检测系统 IO 等待率（CPU 等待磁盘 I/O 的比例）"
    category = CheckCategory.STORAGE

    def run(self) -> CheckResult:
        try:
            with open("/proc/stat") as f:
                fields = f.readline().split()
            idle = int(fields[4])
            iowait = int(fields[5])
            total = sum(int(f) for f in fields[1:8])
            iowait_pct = (iowait / total * 100) if total > 0 else 0

            if iowait_pct >= 50:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=False,
                    severity=CheckSeverity.CRITICAL,
                    message=f"IO Wait {iowait_pct:.1f}% 严重偏高（磁盘瓶颈）",
                    current=f"{iowait_pct:.1f}%", expected="<20%",
                    fix_available=True, fix_id="check_disk_io",
                    fix_description="检查磁盘性能",
                    fix_risk="medium",
                )
            elif iowait_pct >= 20:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=False,
                    severity=CheckSeverity.WARNING,
                    message=f"IO Wait {iowait_pct:.1f}% 偏高",
                    current=f"{iowait_pct:.1f}%", expected="<20%",
                )
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.PASSED,
                message=f"IO Wait {iowait_pct:.1f}% 正常",
                current=f"{iowait_pct:.1f}%", expected="<20%",
            )
        except Exception:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.INFO,
                message="IO Wait 检测跳过（Windows 或权限不足）",
                current="unknown", expected="<20%",
            )
