# -*- coding: utf-8 -*-
"""备份任务状态检测"""
import os, subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class BackupStatusCheck(Check):
    check_id = "backup_status"
    title = "备份状态"
    description = "检测定时备份任务是否正常运行"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        backup_dirs = ["/backup", "/backups", "/mnt/backup"]
        found = []
        for d in backup_dirs:
            if os.path.exists(d) and os.access(d, os.R_OK):
                try:
                    cnt = len(os.listdir(d))
                    found.append(f"{d}: {cnt} files")
                except Exception:
                    pass

        backup_tasks = []
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if any(kw in line.lower() for kw in ["backup", "rsync", "restic", "borg", "duplicati"]):
                        backup_tasks.append(line.strip())
        except Exception:
            pass

        if found or backup_tasks:
            msg = "; ".join(found[:2])
            if backup_tasks:
                msg += f"; {len(backup_tasks)} 个备份任务"
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.PASSED,
                message=msg or "备份相关任务存在",
                current="configured", expected="running",
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.WARNING,
            message="未检测到备份任务",
            current="not configured", expected="configured",
            fix_available=True, fix_id="setup_backup",
            fix_description="配置定时备份任务（rsync/restic/borg）",
            fix_risk="medium",
        )
