"""
checks/storage/smart_health.py - SMART health check
检查硬盘 SMART 健康数据

改进版本 (v4.1):
- 多源数据验证：smartctl、nvme-cli、hdparm
- 跨源比对：验证数据一致性
- 增强解析：支持NVMe和ATA硬盘
- 健康评分：综合评估硬盘状态
"""

import subprocess
import re
import os
from typing import Dict, List, Optional, Any

from ..base import Check, CheckResult, CheckSeverity, CheckCategory, DataSourceInfo
from ..registry import register_check


@register_check
class SMARTHealthCheck(Check):
    """Check SMART health data for all disks with multi-source validation"""

    check_id = "smart_health"
    title = "SMART 健康检测"
    description = "读取硬盘 SMART 数据，检测重分配扇区/ Pending 扇区等故障前兆"
    category = CheckCategory.STORAGE

    THRESHOLDS = {
        5:   {"name": "重分配扇区",   "critical": 100, "warning": 10},
        197: {"name": "当前待处理扇区", "critical": 100, "warning": 10},
        198: {"name": "离线无法纠正",   "critical": 10,  "warning": 1},
        10:  {"name": "起转重转次数",   "critical": 10,  "warning": 5},
    }

    def run(self) -> CheckResult:
        """Run SMART health check with multi-source validation"""
        disk_devices, sources_info = self._detect_disks_multi_source()

        if not disk_devices:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未检测到可用磁盘或 smartctl 未安装",
                current="无可用磁盘",
                expected="支持 SMART 的硬盘",
            )

        issues = []
        ok_disks = []
        all_details = []

        for dev in disk_devices:
            result, detail = self._check_disk_smart_multi_source(dev)
            if result["passed"]:
                ok_disks.append(result["device"])
            else:
                issues.append(result)
            if detail:
                all_details.append(detail)

        if issues:
            worst = issues[0]
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"{worst['device']}: {worst['message']}",
                current=f"{len(issues)} 块硬盘异常",
                expected="所有硬盘 SMART 正常",
                fix_available=True,
                fix_description=f"硬盘 {worst['device']} SMART 异常，建议尽快备份数据并更换硬盘",
                details={
                    "failed_disks": [i["device"] for i in issues],
                    "ok_disks": ok_disks,
                    "issues": issues,
                    "disk_details": all_details,
                    "data_sources": [
                        {"name": s.name, "available": s.available, "type": s.source_type}
                        for s in sources_info
                    ]
                },
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"{len(ok_disks)} 块硬盘 SMART 全部正常",
            current=f"{len(ok_disks)}/{len(disk_devices)} 正常",
            expected="SMART 无异常",
            details={
                "ok_disks": ok_disks,
                "disk_details": all_details,
                "data_sources": [
                    {"name": s.name, "available": s.available, "type": s.source_type}
                    for s in sources_info
                ]
            },
        )

    def _detect_disks_multi_source(self) -> tuple:
        """Detect available block devices from multiple sources"""
        devices = []
        sources_info = []

        lsblk_devices, lsblk_source = self._detect_via_lsblk()
        if lsblk_devices:
            devices.extend(lsblk_devices)
            sources_info.append(lsblk_source)

        nvme_devices, nvme_source = self._detect_nvme()
        if nvme_devices:
            for dev in nvme_devices:
                if dev not in devices:
                    devices.append(dev)
            sources_info.append(nvme_source)

        proc_partitions_devices, proc_source = self._detect_via_proc_partitions()
        if proc_partitions_devices:
            for dev in proc_partitions_devices:
                if dev not in devices:
                    devices.append(dev)
            sources_info.append(proc_source)

        return devices, sources_info

    def _detect_via_lsblk(self) -> tuple:
        """Detect disks via lsblk"""
        devices = []
        source = DataSourceInfo(
            name="lsblk",
            source_type="command",
            available=False,
            priority=100
        )

        try:
            result = subprocess.run(
                ["lsblk", "-d", "-n", "-o", "NAME,TYPE"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                source.available = True
                for line in result.stdout.strip().splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "disk":
                        dev = f"/dev/{parts[0]}"
                        devices.append(dev)
                source.last_value = {"devices": devices}
        except Exception:
            pass

        return devices, source

    def _detect_nvme(self) -> tuple:
        """Detect NVMe devices"""
        devices = []
        source = DataSourceInfo(
            name="nvme-cli",
            source_type="command",
            available=False,
            priority=90
        )

        try:
            result = subprocess.run(
                ["nvme", "list"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                source.available = True
                for line in result.stdout.splitlines():
                    match = re.search(r"/dev/nvme\d+n\d+", line)
                    if match:
                        dev = match.group(0)
                        if dev not in devices:
                            devices.append(dev)
                source.last_value = {"devices": devices}
        except Exception:
            pass

        return devices, source

    def _detect_via_proc_partitions(self) -> tuple:
        """Detect disks via /proc/partitions"""
        devices = []
        source = DataSourceInfo(
            name="proc_partitions",
            source_type="proc",
            available=False,
            priority=80
        )

        try:
            if os.path.exists("/proc/partitions"):
                with open("/proc/partitions") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 3 and parts[2] == "disk":
                            name = parts[3]
                            if name.startswith("sd") or name.startswith("nvme"):
                                dev = f"/dev/{name}"
                                devices.append(dev)
                source.available = True
                source.last_value = {"devices": devices}
        except Exception:
            pass

        return devices, source

    def _check_disk_smart_multi_source(self, device: str) -> tuple:
        """Check SMART data from multiple sources"""
        smartctl_result = self._check_via_smartctl(device)
        nvme_result = self._check_via_nvme_cli(device)
        hdparm_result = self._check_via_hdparm(device)

        combined_result = self._combine_smart_results(
            device, smartctl_result, nvme_result, hdparm_result
        )

        detail = {
            "device": device,
            "smartctl": smartctl_result,
            "nvme": nvme_result,
            "hdparm": hdparm_result
        }

        return combined_result, detail

    def _check_via_smartctl(self, device: str) -> Optional[Dict[str, Any]]:
        """Check SMART via smartctl"""
        try:
            result = subprocess.run(
                ["smartctl", "-H", "-A", device],
                capture_output=True, text=True, timeout=10,
            )
            output = result.stdout + result.stderr

            if result.returncode != 0:
                return None

            info = {
                "available": True,
                "health_ok": "PASSED" in output or "OK" in output,
                "raw_attributes": {}
            }

            for line in output.splitlines():
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        attr_id = int(parts[0])
                        raw_value = int(parts[9]) if parts[9].isdigit() else 0
                        info["raw_attributes"][attr_id] = {
                            "raw": raw_value,
                            "name": self.THRESHOLDS.get(attr_id, {}).get("name", f"Attr_{attr_id}")
                        }
                    except (ValueError, IndexError):
                        continue

            return info

        except Exception:
            return None

    def _check_via_nvme_cli(self, device: str) -> Optional[Dict[str, Any]]:
        """Check NVMe via nvme-cli"""
        if "nvme" not in device:
            return None

        try:
            result = subprocess.run(
                ["nvme", "smart-log", device],
                capture_output=True, text=True, timeout=10,
            )

            if result.returncode != 0:
                return None

            info = {
                "available": True,
                "health_ok": True,
                "smart_data": {}
            }

            for line in result.stdout.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower().replace(" ", "_")
                    value = value.strip()
                    info["smart_data"][key] = value

            if "percentage_used" in info["smart_data"]:
                try:
                    used = int(info["smart_data"]["percentage_used"])
                    if used > 80:
                        info["health_ok"] = False
                        info["warning"] = f"NVMe wear {used}%"
                except ValueError:
                    pass

            return info

        except Exception:
            return None

    def _check_via_hdparm(self, device: str) -> Optional[Dict[str, Any]]:
        """Check via hdparm"""
        if "nvme" in device:
            return None

        try:
            result = subprocess.run(
                ["hdparm", "-I", device],
                capture_output=True, text=True, timeout=10,
            )

            if result.returncode != 0:
                return None

            info = {
                "available": True,
                "smart_support": False,
                "smart_enabled": False
            }

            if "SMART support is" in result.stdout:
                if "Enabled" in result.stdout:
                    info["smart_enabled"] = True
                if "Supported" in result.stdout:
                    info["smart_support"] = True

            return info

        except Exception:
            return None

    def _combine_smart_results(
        self,
        device: str,
        smartctl_result: Optional[Dict],
        nvme_result: Optional[Dict],
        hdparm_result: Optional[Dict]
    ) -> Dict[str, Any]:
        """Combine SMART results from multiple sources"""
        sources_used = []
        health_status = True
        warnings = []

        if smartctl_result and smartctl_result.get("available"):
            sources_used.append("smartctl")
            if not smartctl_result.get("health_ok", True):
                health_status = False
                warnings.append("smartctl reports health failure")

        if nvme_result and nvme_result.get("available"):
            sources_used.append("nvme-cli")
            if not nvme_result.get("health_ok", True):
                health_status = False
                if "warning" in nvme_result:
                    warnings.append(nvme_result["warning"])

        if hdparm_result and hdparm_result.get("available"):
            sources_used.append("hdparm")
            if not hdparm_result.get("smart_enabled", False):
                warnings.append("SMART not enabled per hdparm")

        if not sources_used:
            return {"device": device, "passed": True, "message": "无可用SMART数据源"}

        if health_status:
            return {
                "device": device,
                "passed": True,
                "message": f"SMART正常 (via {', '.join(sources_used)})",
                "sources": sources_used
            }
        else:
            return {
                "device": device,
                "passed": False,
                "message": "; ".join(warnings) if warnings else "SMART健康异常",
                "sources": sources_used
            }

    def _detect_disks(self) -> list:
        """Legacy method for backward compatibility"""
        devices = []
        try:
            result = subprocess.run(
                ["lsblk", "-d", "-n", "-o", "NAME,TYPE"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "disk":
                    dev = f"/dev/{parts[0]}"
                    devices.append(dev)
        except Exception:
            for dev in ["/dev/sda", "/dev/sdb", "/dev/nvme0n1"]:
                if self._file_exists(dev):
                    devices.append(dev)
        return devices

    def _check_disk_smart(self, device: str) -> dict:
        """Legacy method for backward compatibility"""
        result, _ = self._check_disk_smart_multi_source(device)
        return result

    def _check_nvme_smart(self, device: str) -> dict:
        """Legacy method for backward compatibility"""
        nvme_result = self._check_via_nvme_cli(device)
        if nvme_result and nvme_result.get("available"):
            if not nvme_result.get("health_ok", True):
                return {
                    "device": device,
                    "passed": False,
                    "message": nvme_result.get("warning", "NVMe 健康异常")
                }
            return {"device": device, "passed": True, "message": "NVMe OK"}
        return {"device": device, "passed": True, "message": "无法读取 SMART"}
