# -*- coding: utf-8 -*-
"""NAS 温度检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class NASTemperatureCheck(Check):
    check_id = "nas_temperature"
    title = "NAS 温度"
    description = "检测 NAS 设备温度（CPU/硬盘/环境）"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        temps = {}
        try:
            # 尝试 hddtemp
            result = subprocess.run(["hddtemp", "-w", "/dev/sda"], capture_output=True, text=True, errors="replace", timeout=5)
            if result.returncode == 0 and result.stdout:
                import re
                m = re.search(r"(\d+)\s*C", result.stdout)
                if m:
                    temps["sda"] = int(m.group(1))
        except Exception:
            pass

        try:
            # 尝试 smartctl
            result = subprocess.run(
                ["smartctl", "-A", "/dev/sda"],
                capture_output=True, text=True, errors="replace", timeout=10
            )
            if result.returncode == 0:
                import re
                for line in result.stdout.splitlines():
                    if "Temperature_Celsius" in line or "Airflow_Temperature_Cel" in line:
                        parts = line.split()
                        if len(parts) >= 10:
                            try:
                                val = int(parts[9])
                                temps["hdd"] = val
                            except ValueError:
                                pass
        except Exception:
            pass

        if temps:
            issues = []
            for name, t in temps.items():
                if t > 50:
                    issues.append(f"{name}: {t}C 过热")
            if issues:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=False,
                    severity=CheckSeverity.WARNING,
                    message="; ".join(issues),
                    current=f"{temps}", expected="<50C",
                )
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.PASSED,
                message=f"温度正常: {', '.join(f'{k}={v}C' for k,v in temps.items())}",
                current=str(temps), expected="<50C",
            )

        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.INFO,
            message="温度检测工具不可用（hddtemp/smartctl）",
            current="unknown", expected="<50C",
        )
