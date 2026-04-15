# -*- coding: utf-8 -*-
"""定时任务检测"""
import subprocess, os
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class CronJobsCheck(Check):
    check_id = "cron_jobs"
    title = "定时任务"
    description = "检测定时任务配置，识别过多任务"
    category = CheckCategory.SYSTEM

    def run(self) -> CheckResult:
        total = 0
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                total += len([l for l in result.stdout.splitlines() if l.strip() and not l.strip().startswith("#")])
        except Exception:
            pass
        for path in ["/etc/crontab", "/etc/cron.d/", "/etc/cron.hourly/"]:
            if os.path.isdir(path):
                try:
                    total += len([f for f in os.listdir(path) if not f.startswith(".")])
                except Exception:
                    pass
            elif os.path.exists(path):
                total += 1

        if total > 30:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.WARNING,
                message=f"定时任务 {total} 个，偏多",
                current=f"{total} jobs", expected="<30",
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.PASSED,
            message=f"定时任务 {total} 个，正常",
            current=f"{total} jobs", expected="<30",
        )
