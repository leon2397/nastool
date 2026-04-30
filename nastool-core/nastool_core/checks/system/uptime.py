from typing import Optional

"""
checks/system/uptime.py - System uptime check
检查系统运行时间和负载
"""

import os
import subprocess
import time
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class UptimeCheck(Check):
    """Check system uptime and load"""

    check_id = "system_uptime"
    title = "系统运行时间"
    description = "检测系统启动时间、运行天数和负载状态"
    category = CheckCategory.SYSTEM

    # 警告阈值：运行超过此天数未重启
    UPTIME_WARNING_DAYS = 30
    # 严重阈值
    UPTIME_CRITICAL_DAYS = 90

    def run(self) -> CheckResult:
        """Run uptime check"""
        uptime_info = self._get_uptime()

        if uptime_info is None:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="无法获取系统运行时间",
                current="未知",
                expected="正常",
            ))

        days = uptime_info["days"]
        hours = uptime_info["hours"]
        load = uptime_info["load"]
        boot_time = uptime_info["boot_time"]

        # 格式化运行时间
        if days > 0:
            uptime_str = f"{days} 天 {hours} 小时"
        else:
            uptime_str = f"{hours} 小时"

        # 判断负载
        load_status = self._evaluate_load(load)

        # 运行时间过长警告
        if days >= self.UPTIME_CRITICAL_DAYS:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"系统已连续运行 {uptime_str}（建议重启以应用更新）",
                current=f"{uptime_str} | 负载 {load}",
                expected=f"建议每 {self.UPTIME_WARNING_DAYS} 天重启一次",
                details={
                    "days": days,
                    "hours": hours,
                    "load_1m": load.get("1m"),
                    "load_5m": load.get("5m"),
                    "boot_time": boot_time,
                },
            ))

        if days >= self.UPTIME_WARNING_DAYS:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.WARNING,
                message=f"系统已运行 {uptime_str}，建议近期重启",
                current=f"{uptime_str} | 负载 {load}",
                expected=f"< {self.UPTIME_WARNING_DAYS} 天或负载正常",
            )

        # 负载异常
        if load_status != "normal":
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"系统运行正常（{uptime_str}），但负载偏高: {load}",
                current=f"{uptime_str} | 负载 {load_status}",
                expected="负载正常",
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"系统运行正常（{uptime_str}），负载平稳",
            current=f"{uptime_str} | 负载 {load}",
            expected="运行良好",
            details={
                "days": days,
                "hours": hours,
                "boot_time": boot_time,
            },
        )

    def _get_uptime(self) -> Optional[dict]:
        """Get system uptime information"""
        try:
            # 方法1: /proc/uptime
            with open("/proc/uptime") as f:
                uptime_seconds = float(f.read().split()[0])

            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)

            # 获取启动时间
            boot_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - uptime_seconds))

            # 获取负载
            load = self._get_loadavg()

            return {
                "days": days,
                "hours": hours,
                "seconds": uptime_seconds,
                "boot_time": boot_time,
                "load": load,
            }
        except Exception:
            return None

    def _get_loadavg(self) -> dict:
        """Get system load averages"""
        try:
            with open("/proc/loadavg") as f:
                parts = f.read().strip().split()
                return {
                    "1m": float(parts[0]),
                    "5m": float(parts[1]),
                    "15m": float(parts[2]),
                }
        except Exception:
            return {"1m": 0.0, "5m": 0.0, "15m": 0.0}

    def _evaluate_load(self, load: dict) -> str:
        """Evaluate if load is normal"""
        try:
            # 简单评估：以 1m load 为参考
            load_1m = load.get("1m", 0)
            cpu_count = os.cpu_count() or 1
            load_per_cpu = load_1m / cpu_count

            if load_per_cpu > 5:
                return "critical"
            elif load_per_cpu > 2:
                return "warning"
            return "normal"
        except Exception:
            return "unknown"
