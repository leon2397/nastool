"""
checks/system/memory_check.py - Memory availability check
"""

import os
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check
from core.config_loader import get_config


@register_check
class MemoryCheck(Check):
    """Check available memory"""

    check_id = "memory_check"
    category = CheckCategory.SYSTEM
    title = "Memory"
    description = "Check if system has enough memory"

    def _get_memory_info(self) -> tuple:
        """Get memory info from /proc/meminfo"""
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()

            total_kb = 0
            available_kb = 0

            for line in lines:
                if line.startswith("MemTotal:"):
                    total_kb = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    available_kb = int(line.split()[1])

            return total_kb // 1024, available_kb // 1024
        except Exception as e:
            return 0, 0

    def run(self) -> CheckResult:
        # 从配置读取阈值
        config = get_config()
        min_memory_mb = config.system.memory_min_mb
        recommended_memory_mb = config.system.memory_recommended_mb

        if os.name == "nt":
            # Windows
            import ctypes

            kernel32 = ctypes.windll.kernel32
            c_ulong = ctypes.c_ulong

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", c_ulong),
                    ("dwMemoryLoad", c_ulong),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))

            total_mb = stat.ullTotalPhys // (1024 * 1024)
            available_mb = stat.ullAvailPhys // (1024 * 1024)
        else:
            total_mb, available_mb = self._get_memory_info()

        if total_mb >= recommended_memory_mb:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"Memory {total_mb}MB total, {available_mb}MB available (recommended)"
        elif total_mb >= min_memory_mb:
            severity = CheckSeverity.WARNING
            passed = True
            message = (
                f"Memory {total_mb}MB meets minimum, but {recommended_memory_mb}MB recommended"
            )
        else:
            severity = CheckSeverity.CRITICAL
            passed = False
            message = f"Memory {total_mb}MB below minimum {min_memory_mb}MB"

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current=f"{total_mb}MB",
            expected=f">= {min_memory_mb}MB",
            message=message,
            fix_available=False,  # Can't fix memory via software
            fix_description="Upgrade hardware or add swap" if total_mb < min_memory_mb else None,
            fix_risk="none",
            details={"total_mb": total_mb, "available_mb": available_mb},
        )
