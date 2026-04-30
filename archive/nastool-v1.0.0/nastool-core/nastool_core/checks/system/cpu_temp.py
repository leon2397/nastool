"""
checks/system/cpu_temp.py - CPU temperature check
检查 CPU 温度是否正常
"""

import subprocess
import re
import os
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class CPUTempCheck(Check):
    """Check CPU temperature"""

    check_id = "cpu_temperature"
    title = "CPU 温度检测"
    description = "监测 CPU 温度，检测过热前兆"
    category = CheckCategory.SYSTEM

    TEMP_WARNING = 75   # 警告阈值（°C）
    TEMP_CRITICAL = 85  # 严重阈值（°C）

    def run(self) -> CheckResult:
        """Run CPU temperature check"""
        temps = self._get_cpu_temps()

        if not temps:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未检测到 CPU 温度（可能是虚拟化环境）",
                current="无数据",
                expected=f"CPU 温度 < {self.TEMP_WARNING}°C",
            )

        max_temp = max(t["temp"] for t in temps)
        max_core = next(t for t in temps if t["temp"] == max_temp)["core"]

        if max_temp >= self.TEMP_CRITICAL:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"{max_core} 温度 {max_temp}°C（严重过热！）",
                current=f"最高 {max_temp}°C",
                expected=f"< {self.TEMP_WARNING}°C",
                fix_available=True,
                fix_description="CPU 过热！建议：检查散热器、清理灰尘、涂抹硅脂、降低工作负载",
            )

        if max_temp >= self.TEMP_WARNING:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"{max_core} 温度 {max_temp}°C（警告）",
                current=f"最高 {max_temp}°C",
                expected=f"< {self.TEMP_WARNING}°C",
                details={"cores": temps},
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"CPU 温度正常（最高 {max_temp}°C）",
            current=f"最高 {max_temp}°C",
            expected=f"< {self.TEMP_WARNING}°C",
            details={"cores": temps},
        )

    def _get_cpu_temps(self) -> list:
        """Get CPU temperatures via multiple methods"""
        temps = []

        # 方法1: thermal_zone（Linux 标准）
        tzs = self._thermal_zones()
        temps.extend(tzs)

        # 方法2: sensors 命令
        sensor_temps = self._sensors_temps()
        temps.extend(sensor_temps)

        # 去重
        seen = {}
        for t in temps:
            key = t["core"]
            if key not in seen or t["temp"] > seen[key]["temp"]:
                seen[key] = t
        return list(seen.values())

    def _thermal_zones(self) -> list:
        """Read from /sys/class/thermal"""
        temps = []
        try:
            base = "/sys/class/thermal"
            if not os.path.exists(base):
                return []
            for zone in os.listdir(base):
                if not zone.startswith("thermal_zone"):
                    continue
                zone_path = os.path.join(base, zone)
                type_file = os.path.join(zone_path, "type")
                temp_file = os.path.join(zone_path, "temp")

                if os.path.exists(temp_file):
                    try:
                        with open(temp_file) as f:
                            temp_mc = int(f.read().strip())  # millidegree
                            temp = temp_mc / 1000
                            if 0 < temp < 120:
                                zone_type = "unknown"
                                if os.path.exists(type_file):
                                    with open(type_file) as tf:
                                        zone_type = tf.read().strip()
                                core_name = f"{zone}({zone_type})"
                                temps.append({"core": core_name, "temp": temp, "source": "thermal_zone"})
                    except (ValueError, IOError):
                        pass
        except Exception:
            pass
        return temps

    def _sensors_temps(self) -> list:
        """Get temps via `sensors` command"""
        temps = []
        try:
            result = subprocess.run(
                ["sensors"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
            )
            if result.returncode != 0:
                return []

            # 解析 sensors 输出
            current_core = "CPU"
            for line in result.stdout.splitlines():
                line = line.strip()
                # 新芯片/适配器行
                if "Adapter:" in line or line.startswith("-" * 10):
                    continue
                # 空行，重置
                if not line:
                    current_core = "CPU"
                    continue
                # 温度行
                match = re.search(r"Core\s+(\d+):\s+\+?(\d+\.\d+)", line)
                if match:
                    core_id = match.group(1)
                    temp = float(match.group(2))
                    temps.append({
                        "core": f"Core {core_id}",
                        "temp": temp,
                        "source": "sensors",
                    })
                    continue
                # 通用温度行（x86_pkg_temp 等）
                match2 = re.search(r"Temp\s*\d*:\s+\+?(\d+\.\d+)", line)
                if match2:
                    temp = float(match2.group(1))
                    temps.append({
                        "core": current_core,
                        "temp": temp,
                        "source": "sensors",
                    })
        except Exception:
            pass
        return temps


import os
