# -*- coding: utf-8 -*-
"""系统日志异常检测"""
import subprocess, os
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class SystemLogsCheck(Check):
    check_id = "system_logs"
    title = "系统日志"
    description = "检测系统日志中近期的错误和警告"
    category = CheckCategory.SYSTEM

    def run(self) -> CheckResult:
        errors = []
        for log in ["/var/log/syslog", "/var/log/messages", "/var/log/dmesg"]:
            if not os.path.exists(log):
                continue
            try:
                result = subprocess.run(["tail", "-n", "200", log], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        lower = line.lower()
                        if any(kw in lower for kw in ["error", "failed", "fault", "panic", "out of memory"]):
                            errors.append(line.strip()[:100])
                            if len(errors) >= 5:
                                break
            except Exception:
                pass
            if len(errors) >= 5:
                break

        if errors:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.WARNING,
                message=f"发现 {len(errors)} 条异常日志: {errors[0][:60]}",
                current="errors found", expected="clean",
                fix_available=True, fix_id="check_logs",
                fix_description="检查系统日志处理错误",
                fix_risk="medium",
                details={"errors": errors[:5]},
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.PASSED,
            message="近 200 行日志无明显异常",
            current="clean", expected="clean",
        )
