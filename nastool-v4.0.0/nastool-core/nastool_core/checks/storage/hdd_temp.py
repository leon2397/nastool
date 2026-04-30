from typing import Optional
"""
checks/storage/hdd_temp.py - HDD/SSD temperature check
检查硬盘温度是否正常
"""

import subprocess
import re
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class HDDTempCheck(Check):
    """Check HDD and SSD temperatures"""

    check_id = "hdd_temperature"
    title = "硬盘温度检测"
    description = "监测硬盘温度，检测过热前兆"
    category = CheckCategory.STORAGE

    # 温度阈值（摄氏度）
    TEMP_WARNING = 50   # 警告阈值
    TEMP_CRITICAL = 65  # 严重阈值

    def run(self) -> CheckResult:
        """Run HDD temperature check"""
        temps = self._get_hdd_temps()

        if not temps:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未检测到可读取温度的硬盘",
                current="无数据",
                expected=f"所有硬盘温度 < {self.TEMP_WARNING}°C",
            )

        # 找最高温度
        max_temp = max(t["temp"] for t in temps)
        max_entry = next(t for t in temps if t["temp"] == max_temp)

        if max_temp >= self.TEMP_CRITICAL:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"{max_entry['device']} 温度 {max_temp}°C（严重）",
                current=f"最高 {max_temp}°C",
                expected=f"所有硬盘 < {self.TEMP_WARNING}°C",
                fix_available=True,
                fix_description="硬盘温度过高，建议检查散热：清理灰尘、检查风扇、确保机箱通风",
                details={"disks": temps},
            )

        if max_temp >= self.TEMP_WARNING:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"{max_entry['device']} 温度 {max_temp}°C（警告）",
                current=f"最高 {max_temp}°C",
                expected=f"所有硬盘 < {self.TEMP_WARNING}°C",
                details={"disks": temps},
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"所有硬盘温度正常（最高 {max_temp}°C）",
            current=f"最高 {max_temp}°C",
            expected=f"< {self.TEMP_WARNING}°C",
            details={"disks": temps},
        )

    def _get_hdd_temps(self) -> list:
        """Get temperatures for all detected disks"""
        temps = []

        # 方法1: smartctl
        disks = self._detect_disks()
        for dev in disks:
            temp = self._smartctl_temp(dev)
            if temp is not None:
                temps.append({"device": dev, "temp": temp, "source": "smartctl"})

        # 方法2: hddtemp（支持更多设备）
        hddtemp_temps = self._hddtemp_temps()
        temps.extend(hddtemp_temps)

        # 方法3: nvme smartctl
        for dev in disks:
            if "nvme" in dev.lower() or "nvm" in dev.lower():
                temp = self._smartctl_temp(dev)
                if temp is not None:
                    temps.append({"device": dev, "temp": temp, "source": "smartctl-nvme"})

        # 去重（同一设备取最高值）
        seen = {}
        for t in temps:
            key = t["device"]
            if key not in seen or t["temp"] > seen[key]["temp"]:
                seen[key] = t
        return list(seen.values())

    def _detect_disks(self) -> list:
        """Detect available disks"""
        devices = []
        try:
            result = subprocess.run(
                ["lsblk", "-d", "-n", "-o", "NAME,TYPE"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "disk":
                    devices.append(f"/dev/{parts[0]}")
        except Exception:
            pass
        return devices

    def _smartctl_temp(self, device: str) -> Optional[int]:
        """Get temperature via smartctl"""
        try:
            result = subprocess.run(
                ["smartctl", "-A", device],
                capture_output=True, text=True, timeout=8,
            )
            if result.returncode != 0:
                return None
            # 查找温度属性 (ID 194 = Temperature Celsius)
            for line in result.stdout.splitlines():
                if "Temperature" in line or "194" in line:
                    parts = line.split()
                    try:
                        raw_idx = next(
                            i for i, p in enumerate(parts) if p == "194"
                        )
                        temp = int(parts[raw_idx + 2])
                        if 0 < temp < 150:
                            return temp
                    except (StopIteration, ValueError, IndexError):
                        pass
        except Exception:
            pass
        return None

    def _hddtemp_temps(self) -> list:
        """Get temperatures via hddtemp daemon"""
        temps = []
        try:
            result = subprocess.run(
                ["hddtemp", "-q", "-u", "C", "-n", "/dev/sda", "/dev/sdb", "/dev/sdc"],
                capture_output=True, text=True, timeout=5,
            )
            devs = ["/dev/sda", "/dev/sdb", "/dev/sdc"]
            for i, line in enumerate(result.stdout.strip().splitlines()):
                try:
                    temp = int(float(line.strip()))
                    if 0 < temp < 150:
                        devs[i]["temp"] = temp
                        temps.append({"device": devs[i], "temp": temp, "source": "hddtemp"})
                except (ValueError, IndexError):
                    pass
        except Exception:
            pass
        return temps
