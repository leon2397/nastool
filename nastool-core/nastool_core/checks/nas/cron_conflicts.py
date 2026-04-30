from typing import Optional
"""
checks/nas/cron_conflicts.py - Scheduled task conflict check
检测定时任务配置冲突
"""

import subprocess
import re
from collections import defaultdict
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class CronConflictsCheck(Check):
    """Check scheduled task conflicts"""

    check_id = "cron_conflicts"
    title = "定时任务冲突"
    description = "检测定时任务冲突，识别同一时刻执行过多任务的情况"
    category = CheckCategory.NAS

    # 警告阈值：同一分钟执行超过此数量任务
    WARNING_COUNT = 3
    CRITICAL_COUNT = 5

    def run(self) -> CheckResult:
        """Run cron conflict check"""
        tasks = self._get_cron_tasks()

        if tasks is None:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="无法读取定时任务（权限不足）",
                current="无数据",
                expected="定时任务正常",
            ))

        if not tasks:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="无定时任务配置",
                current="0 个任务",
                expected="正常",
            ))

        # 按执行时间分组
        conflicts = self._find_conflicts(tasks)

        critical_conflicts = [c for c in conflicts if len(c["tasks"]) >= self.CRITICAL_COUNT]
        warning_conflicts = [c for c in conflicts if self.WARNING_COUNT <= len(c["tasks"]) < self.CRITICAL_COUNT]

        if critical_conflicts:
            worst = critical_conflicts[0]
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"发现 {len(critical_conflicts)} 个严重任务冲突：{worst['time']} 同时执行 {len(worst['tasks'])} 个任务",
                current=f"{len(tasks)} 个任务，{len(critical_conflicts)} 个严重冲突",
                expected="任务错峰执行",
                details={
                    "total_tasks": len(tasks),
                    "critical_conflicts": critical_conflicts,
                    "warning_conflicts": warning_conflicts,
                    "all_conflicts": conflicts,
                },
            )

        if warning_conflicts:
            worst = warning_conflicts[0]
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.WARNING,
                message=f"发现 {len(warning_conflicts)} 个任务冲突：{worst['time']} 同时 {len(worst['tasks'])} 个",
                current=f"{len(tasks)} 个任务，{len(warning_conflicts)} 个冲突",
                expected="任务合理分配",
                details={
                    "total_tasks": len(tasks),
                    "warning_conflicts": warning_conflicts,
                },
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"{len(tasks)} 个定时任务，无冲突",
            current=f"{len(tasks)} 个任务",
            expected="无冲突",
            details={"total_tasks": len(tasks), "tasks": tasks[:20]},
        )

    def _get_cron_tasks(self) -> Optional[list]:
        """Get all cron tasks from system"""
        tasks = []

        # 系统 crontab
        try:
            result = subprocess.run(
                ["cat", "/etc/crontab"],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            if result.returncode == 0:
                tasks.extend(self._parse_crontab(result.stdout, source="/etc/crontab"))
        except Exception:
            pass

        # 用户 crontab
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                tasks.extend(self._parse_crontab(result.stdout, source="user crontab"))
        except Exception:
            pass

        # cron.d/
        try:
            result = subprocess.run(
                ["find", "/etc/cron.d", "-type", "f", "-exec", "cat", "{}"],
                capture_output=True, text=True, errors="replace", timeout=10,
            )
            if result.returncode == 0:
                tasks.extend(self._parse_crontab(result.stdout, source="/etc/cron.d"))
        except Exception:
            pass

        if not tasks:
            return None
        return tasks

    def _parse_crontab(self, content: str, source: str) -> list:
        """Parse crontab content into task list"""
        tasks = []
        for line in content.splitlines():
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue
            # 跳过环境变量
            if "=" in line and not line.startswith("*") and line.split()[0].count(" ") == 0:
                continue

            parts = line.split()
            if len(parts) < 6:
                continue

            # 解析时间字段（前5个）
            try:
                minute, hour, day, month, weekday = parts[:5]
                command = " ".join(parts[5:])
                tasks.append({
                    "minute": minute,
                    "hour": hour,
                    "day": day,
                    "month": month,
                    "weekday": weekday,
                    "command": command[:80],  # 截断长命令
                    "source": source,
                })
            except Exception:
                continue

        return tasks

    def _find_conflicts(self, tasks: list) -> list:
        """Find time slots with multiple tasks"""
        slots = defaultdict(list)

        for task in tasks:
            # 简化：只按 minute+hour 分组（忽略 */n 格式）
            time_key = f"{task['hour']}:{task['minute']}"
            slots[time_key].append(task)

        conflicts = []
        for time_key, task_list in slots.items():
            if len(task_list) >= self.WARNING_COUNT:
                conflicts.append({
                    "time": time_key,
                    "count": len(task_list),
                    "tasks": task_list,
                })

        conflicts.sort(key=lambda x: -x["count"])
        return conflicts
