"""
checks/system/cpu_temp.py - CPU temperature check
检查 CPU 温度是否正常
"""

import subprocess
import re
import os
from datetime import datetime
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check
from ...utils.data_source import DataFusionEngine, DataSourceResult, FusionMethod
from ...utils.confidence_scorer import ConfidenceScorer


@register_check
class CPUTempCheck(Check):
    """Check CPU temperature"""

    check_id = "cpu_temperature"
    title = "CPU 温度检测"
    description = "监测 CPU 温度，检测过热前兆"
    category = CheckCategory.SYSTEM

    TEMP_WARNING = 75   # 警告阈值（°C）
    TEMP_CRITICAL = 85  # 严重阈值（°C）

    def __init__(self):
        """Initialize CPUTempCheck"""
        super().__init__()
        self.fusion_engine = DataFusionEngine()
        self.confidence_scorer = ConfidenceScorer()

    def run(self) -> CheckResult:
        """Run CPU temperature check"""
        results = self._collect_temps_multi_source()

        if not results:
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

        # Fuse data from multiple sources
        fused_value, metadata = self.fusion_engine.fuse_data(results, FusionMethod.WEIGHTED_AVERAGE)

        if fused_value is None:
            # Fallback to simple average if fusion fails
            temp_values = [r.value for r in results if isinstance(r.value, (int, float))]
            if temp_values:
                fused_value = sum(temp_values) / len(temp_values)
            else:
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=True,
                    severity=CheckSeverity.INFO,
                    message="无法融合温度数据",
                    current="无数据",
                    expected=f"CPU 温度 < {self.TEMP_WARNING}°C",
                )

        # Calculate confidence score
        confidence = self.confidence_scorer.calculate_confidence(results, check_id=self.check_id)

        # Determine severity based on fused temperature
        if fused_value >= self.TEMP_CRITICAL:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"CPU 温度 {fused_value:.1f}°C（严重过热！）",
                current=f"{fused_value:.1f}°C",
                expected=f"< {self.TEMP_WARNING}°C",
                fix_available=True,
                fix_description="CPU 过热！建议：检查散热器、清理灰尘、涂抹硅脂、降低工作负载",
                details={
                    "sources": [r.source for r in results],
                    "confidence": confidence.score,
                    "fusion_method": "weighted_average"
                },
            )

        if fused_value >= self.TEMP_WARNING:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"CPU 温度 {fused_value:.1f}°C（警告）",
                current=f"{fused_value:.1f}°C",
                expected=f"< {self.TEMP_WARNING}°C",
                details={
                    "sources": [r.source for r in results],
                    "confidence": confidence.score,
                    "fusion_method": "weighted_average"
                },
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"CPU 温度正常（{fused_value:.1f}°C）",
            current=f"{fused_value:.1f}°C",
            expected=f"< {self.TEMP_WARNING}°C",
            details={
                "sources": [r.source for r in results],
                "confidence": confidence.score,
                "fusion_method": "weighted_average"
            },
        )

    def _collect_temps_multi_source(self) -> list:
        """Collect temperatures from multiple sources"""
        results = []
        timestamp = datetime.now().timestamp()

        # 方法1: thermal_zone（Linux 标准）
        tz_temps = self._thermal_zones()
        for temp_info in tz_temps:
            results.append(DataSourceResult(
                value=temp_info["temp"],
                source=temp_info["source"],
                timestamp=timestamp,
                confidence=0.9
            ))

        # 方法2: sensors 命令
        sensor_temps = self._sensors_temps()
        for temp_info in sensor_temps:
            results.append(DataSourceResult(
                value=temp_info["temp"],
                source=temp_info["source"],
                timestamp=timestamp,
                confidence=0.85
            ))

        # 方法3: hwmon（硬件监控）
        hwmon_temps = self._hwmon_temps()
        for temp_info in hwmon_temps:
            results.append(DataSourceResult(
                value=temp_info["temp"],
                source=temp_info["source"],
                timestamp=timestamp,
                confidence=0.95
            ))

        # 方法4: vcgencmd（树莓派）
        vcgencmd_temp = self._vcgencmd_temp()
        if vcgencmd_temp:
            results.append(DataSourceResult(
                value=vcgencmd_temp,
                source="vcgencmd",
                timestamp=timestamp,
                confidence=0.9
            ))

        return results

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
                capture_output=True, text=True, errors="replace", timeout=5,
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

    def _hwmon_temps(self) -> list:
        """Read from /sys/class/hwmon"""
        temps = []
        try:
            base = "/sys/class/hwmon"
            if not os.path.exists(base):
                return []
            for hwmon in os.listdir(base):
                if not hwmon.startswith("hwmon"):
                    continue
                hwmon_path = os.path.join(base, hwmon)
                for file in os.listdir(hwmon_path):
                    if file.startswith("temp") and file.endswith("_input"):
                        temp_file = os.path.join(hwmon_path, file)
                        try:
                            with open(temp_file) as f:
                                temp_mc = int(f.read().strip())  # millidegree
                                temp = temp_mc / 1000
                                if 0 < temp < 120:
                                    label_file = os.path.join(hwmon_path, file.replace("_input", "_label"))
                                    label = "unknown"
                                    if os.path.exists(label_file):
                                        with open(label_file) as lf:
                                            label = lf.read().strip()
                                    core_name = f"{hwmon}_{file.replace('_input', '')}({label})"
                                    temps.append({"core": core_name, "temp": temp, "source": "hwmon"})
                        except (ValueError, IOError):
                            pass
        except Exception:
            pass
        return temps

    def _vcgencmd_temp(self) -> float:
        """Get temperature via vcgencmd (Raspberry Pi)"""
        try:
            result = subprocess.run(
                ["vcgencmd", "measure_temp"],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            if result.returncode != 0:
                return None
            match = re.search(r"temp=(\d+\.\d+)',", result.stdout)
            if match:
                temp = float(match.group(1))
                if 0 < temp < 120:
                    return temp
        except Exception:
            pass
        return None
