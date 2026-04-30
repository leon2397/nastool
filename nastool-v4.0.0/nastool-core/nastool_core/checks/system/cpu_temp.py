"""
checks/system/cpu_temp.py - CPU temperature check
检查 CPU 温度是否正常

改进版本 (v4.1):
- 多源数据收集：thermal_zone, sensors, hwmon, vcgencmd
- 自适应阈值：基于设备类型动态调整
- 数据融合：加权平均提高准确性
- 置信度评估：评估检测结果的可靠程度
"""

import subprocess
import re
import os
from typing import Dict, Callable, Optional
from ..base import Check, CheckResult, CheckSeverity, CheckCategory, DataSourceInfo, FusionResult
from ..registry import register_check


@register_check
class CPUTempCheck(Check):
    """Check CPU temperature with multi-source data fusion"""

    check_id = "cpu_temperature"
    title = "CPU 温度检测"
    description = "监测 CPU 温度，检测过热前兆"
    category = CheckCategory.SYSTEM

    def run(self) -> CheckResult:
        """Run CPU temperature check with multi-source data fusion"""
        device_type = self._get_device_type()
        thresholds = self._get_thresholds(device_type)

        temps, fusion_result, sources_info = self._collect_temps_multi_source()

        if not temps:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未检测到 CPU 温度（可能是虚拟化环境）",
                current="无数据",
                expected=f"CPU 温度 < {thresholds['warning']}°C",
                data_sources=sources_info,
                fusion_result=fusion_result,
                confidence=0.0
            )

        max_temp = max(t["temp"] for t in temps)
        max_core = next(t for t in temps if t["temp"] == max_temp)["core"]

        warning_threshold = thresholds["warning"]
        critical_threshold = thresholds["critical"]

        if max_temp >= critical_threshold:
            result = CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"{max_core} 温度 {max_temp}°C（严重过热！）",
                current=f"最高 {max_temp}°C",
                expected=f"< {warning_threshold}°C",
                fix_available=True,
                fix_description="CPU 过热！建议：检查散热器、清理灰尘、涂抹硅脂、降低工作负载",
                data_sources=sources_info,
                fusion_result=fusion_result,
                confidence=fusion_result.confidence if fusion_result else 0.5,
                details={"cores": temps, "device_type": device_type}
            )
            return result

        if max_temp >= warning_threshold:
            result = CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"{max_core} 温度 {max_temp}°C（警告）",
                current=f"最高 {max_temp}°C",
                expected=f"< {warning_threshold}°C",
                data_sources=sources_info,
                fusion_result=fusion_result,
                confidence=fusion_result.confidence if fusion_result else 0.5,
                details={"cores": temps, "device_type": device_type}
            )
            return result

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"CPU 温度正常（最高 {max_temp}°C）",
            current=f"最高 {max_temp}°C",
            expected=f"< {warning_threshold}°C",
            data_sources=sources_info,
            fusion_result=fusion_result,
            confidence=fusion_result.confidence if fusion_result else 0.5,
            details={"cores": temps, "device_type": device_type}
        )

    def _get_device_type(self) -> str:
        """Get device type for threshold selection"""
        try:
            from nastool_core.utils.device_identifier import identify_device
            device_info = identify_device()
            return device_info.device_type.value
        except Exception:
            return "generic"

    def _get_thresholds(self, device_type: str) -> Dict[str, float]:
        """Get thresholds based on device type"""
        try:
            from nastool_core.utils.threshold_config import get_threshold
            threshold_config = get_threshold(self.check_id, device_type)
            return {
                "warning": threshold_config.warning,
                "critical": threshold_config.critical,
                "optimal": threshold_config.optimal or 50.0
            }
        except Exception:
            return {"warning": 75.0, "critical": 85.0, "optimal": 50.0}

    def _collect_temps_multi_source(self) -> tuple:
        """
        Collect temperatures from multiple sources with data fusion.

        Returns:
            Tuple of (list of temps, FusionResult, list of DataSourceInfo)
        """
        source_methods: Dict[str, Callable] = {}

        if os.path.exists("/sys/class/thermal"):
            source_methods["thermal_zone"] = self._thermal_zones

        source_methods["sensors"] = self._sensors_temps

        if os.path.exists("/sys/class/hwmon"):
            source_methods["hwmon"] = self._hwmon_temps

        source_methods["vcgencmd"] = self._vcgencmd_temp

        if not source_methods:
            return [], None, []

        fused_temps, fusion_result, sources_info = self._collect_from_sources(
            source_methods,
            fusion_method="weighted_average"
        )

        if fused_temps is None:
            return [], None, sources_info

        if isinstance(fused_temps, (int, float)):
            temps = [{"core": "CPU", "temp": fused_temps, "source": "fused"}]
        else:
            temps = fused_temps if isinstance(fused_temps, list) else []

        return temps, fusion_result, sources_info

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
                            temp_mc = int(f.read().strip())
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
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return []

            current_core = "CPU"
            for line in result.stdout.splitlines():
                line = line.strip()
                if "Adapter:" in line or line.startswith("-" * 10):
                    continue
                if not line:
                    current_core = "CPU"
                    continue
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

    def _hwmon_temps(self) -> list:
        """Get temps from /sys/class/hwmon"""
        temps = []
        try:
            base = "/sys/class/hwmon"
            if not os.path.exists(base):
                return []

            for hwmon in os.listdir(base):
                hwmon_path = os.path.join(base, hwmon)
                name_file = os.path.join(hwmon_path, "name")
                if not os.path.exists(name_file):
                    continue

                with open(name_file) as f:
                    name = f.read().strip()

                if name not in ["coretemp", "cpu", "cpu_thermal"]:
                    continue

                for i in range(10):
                    temp_input = os.path.join(hwmon_path, f"temp{i}_input")
                    if os.path.exists(temp_input):
                        try:
                            with open(temp_input) as f:
                                temp_mc = int(f.read().strip())
                                temp = temp_mc / 1000
                                if 0 < temp < 120:
                                    temps.append({
                                        "core": f"hwmon{i}",
                                        "temp": temp,
                                        "source": "hwmon"
                                    })
                        except (ValueError, IOError):
                            pass
        except Exception:
            pass
        return temps

    def _vcgencmd_temp(self) -> Optional[float]:
        """Get GPU temperature via vcgencmd (Raspberry Pi)"""
        try:
            result = subprocess.run(
                ["vcgencmd", "measure_temp"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                match = re.search(r"temp=(\d+\.\d+)", result.stdout)
                if match:
                    return float(match.group(1))
        except Exception:
            pass
        return None
