"""
adapters/generic.py -- 通用 ARM Linux 适配器（兜底）
"""

import os
import platform
import subprocess
from .base import BaseAdapter, AdapterReport


def _run(cmd: str, timeout: int = 5) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return ""


class GenericAdapter(BaseAdapter):
    name = f"Generic ARM ({platform.machine()})"
    chip_type = "cpu"

    def health_check(self) -> AdapterReport:
        report = AdapterReport(name=self.name, chip_type=self.chip_type)
        checks = {}

        # CPU 频率
        freq = _run(
            "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null | "
            "xargs -I{} python3 -c \"print(round(int({})/1e6, 2), 'GHz')\" 2>/dev/null || echo '未知'"
        )
        checks["cpu_freq_ghz"] = freq

        # Governors
        gov = _run(
            "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo '未知'"
        )
        checks["cpu_governor"] = gov

        report.specific_checks = checks
        report.ok = True
        return report

    def apply_tuning(self, profile: str = "default") -> list:
        if profile == "performance":
            r = subprocess.run(
                "for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do "
                "echo performance > $f 2>/dev/null; done",
                shell=True,
                timeout=10,
            )
            return [f"CPU governor -> performance: {'成功' if r.returncode == 0 else '部分成功'}"]
        return []
