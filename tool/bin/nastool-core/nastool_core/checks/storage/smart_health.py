"""
checks/storage/smart_health.py - SMART health check
检查硬盘 SMART 健康数据
"""

import subprocess
import re
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class SMARTHealthCheck(Check):
    """Check SMART health data for all disks"""

    check_id = "smart_health"
    title = "SMART 健康检测"
    description = "读取硬盘 SMART 数据，检测重分配扇区/ Pending 扇区等故障前兆"
    category = CheckCategory.STORAGE

    # 关键 SMART 属性阈值
    THRESHOLDS = {
        5:   {"name": "重分配扇区",   "critical": 100, "warning": 10},
        197: {"name": "当前待处理扇区", "critical": 100, "warning": 10},
        198: {"name": "离线无法纠正",   "critical": 10,  "warning": 1},
        10:  {"name": "起转重试次数",   "critical": 10,  "warning": 5},
    }

    def run(self) -> CheckResult:
        """Run SMART health check"""
        # 尝试用 smartctl 检测可用磁盘
        disk_devices = self._detect_disks()

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

        for dev in disk_devices:
            result = self._check_disk_smart(dev)
            if result["passed"]:
                ok_disks.append(result["device"])
            else:
                issues.append(result)

        if issues:
            # 汇总最严重的问题
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
            details={"ok_disks": ok_disks},
        )

    def _detect_disks(self) -> list:
        """Detect available block devices"""
        # 首先检查smartctl是否安装
        if not self._is_smartctl_available():
            return []
            
        devices = []
        try:
            result = subprocess.run(
                ["lsblk", "-d", "-n", "-o", "NAME,TYPE"],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            for line in result.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "disk":
                    dev = f"/dev/{parts[0]}"
                    devices.append(dev)
        except Exception:
            # Fallback: 尝试常见设备
            for dev in ["/dev/sda", "/dev/sdb", "/dev/nvme0n1"]:
                if self._file_exists(dev):
                    devices.append(dev)
        return devices
    
    def _is_smartctl_available(self) -> bool:
        """Check if smartctl is available"""
        try:
            result = subprocess.run(
                ["which", "smartctl"],
                capture_output=True, text=True, timeout=2,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_disk_smart(self, device: str) -> dict:
        """Check SMART data for a single disk"""
        try:
            # 先尝试短测试
            subprocess.run(
                ["smartctl", "-t", "short", device],
                capture_output=True, timeout=2,
            )
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["smartctl", "-H", "-A", device],
                capture_output=True, text=True, errors="replace", timeout=10,
            )
            output = result.stdout + result.stderr

            if result.returncode != 0:
                # smartctl 失败，可能是 NVMe 或权限问题
                return self._check_nvme_smart(device)

            # 检查健康状态
            if "PASSED" in output or "OK" in output:
                return {"device": device, "passed": True, "message": "OK"}

            # 解析 SMART 属性
            for line in output.splitlines():
                parts = line.split()
                if len(parts) < 10:
                    continue
                try:
                    attr_id = int(parts[0])
                    if attr_id in self.THRESHOLDS:
                        raw_value = int(parts[9]) if parts[9].isdigit() else 0
                        threshold_info = self.THRESHOLDS[attr_id]
                        if raw_value >= threshold_info["critical"]:
                            return {
                                "device": device,
                                "passed": False,
                                "message": f"{threshold_info['name']}={raw_value} (严重)",
                            }
                        elif raw_value >= threshold_info["warning"]:
                            return {
                                "device": device,
                                "passed": False,
                                "message": f"{threshold_info['name']}={raw_value} (警告)",
                            }
                except (ValueError, IndexError):
                    continue

            return {"device": device, "passed": True, "message": "OK"}

        except subprocess.TimeoutExpired:
            return {"device": device, "passed": False, "message": "smartctl 超时"}
        except FileNotFoundError:
            return {"device": device, "passed": True, "message": "smartctl 未安装，跳过"}
        except Exception as e:
            return {"device": device, "passed": True, "message": f"检查失败: {str(e)}"}

    def _check_nvme_smart(self, device: str) -> dict:
        """Check NVMe SMART data"""
        try:
            result = subprocess.run(
                ["smartctl", "-a", device],
                capture_output=True, text=True, errors="replace", timeout=10,
            )
            if result.returncode == 0 and "NVMe" in result.stdout:
                # NVMe 设备
                if "Percentage Used" in result.stdout:
                    # 解析 NVMe 磨损
                    match = re.search(r"Percentage Used\s+:\s+(\d+)%", result.stdout)
                    if match:
                        used = int(match.group(1))
                        if used > 80:
                            return {
                                "device": device,
                                "passed": False,
                                "message": f"NVMe 磨损 {used}% (警告)",
                            }
                        elif used > 50:
                            return {
                                "device": device,
                                "passed": False,
                                "message": f"NVMe 磨损 {used}%",
                            }
                return {"device": device, "passed": True, "message": "NVMe OK"}
            return {"device": device, "passed": True, "message": "无法读取 SMART"}
        except Exception:
            return {"device": device, "passed": True, "message": "smartctl 不可用"}
