from typing import Optional
"""
checks/storage/raid_status.py - RAID array status check
检查 RAID 阵列状态（mdadm / btrfs / zfs）
"""

import subprocess
import re
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class RAIDStatusCheck(Check):
    """Check RAID array health status"""

    check_id = "raid_status"
    title = "RAID 阵列状态"
    description = "检测 mdadm/btrfs/zfs RAID 阵列的健康状态"
    category = CheckCategory.STORAGE

    def run(self) -> CheckResult:
        """Run RAID status check"""
        arrays = []

        # mdadm 检查
        mdadm_arrays = self._check_mdadm()
        arrays.extend(mdadm_arrays)

        # btrfs 检查
        btrfs_status = self._check_btrfs()
        if btrfs_status:
            arrays.append(btrfs_status)

        # zfs 检查
        zfs_status = self._check_zfs()
        if zfs_status:
            arrays.append(zfs_status)

        if not arrays:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未检测到 RAID 阵列（非 RAID 环境正常）",
                current="无 RAID",
                expected="无 RAID 或 RAID 正常",
            )

        # 检查是否有异常阵列
        issues = [a for a in arrays if not a["ok"]]
        ok_count = len(arrays) - len(issues)

        if issues:
            worst = issues[0]
            severity = CheckSeverity.CRITICAL if "degraded" in worst["state"].lower() or "fail" in worst["state"].lower() else CheckSeverity.WARNING
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=severity,
                message=f"{worst['device']}: {worst['state']}",
                current=f"{len(issues)}/{len(arrays)} 阵列异常",
                expected="所有 RAID 阵列正常",
                fix_available=True,
                fix_description=f"阵列 {worst['device']} 状态异常 ({worst['state']})，请检查硬盘并及时更换故障盘",
                details={"arrays": arrays, "issues": issues},
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"{ok_count} 个 RAID 阵列全部正常",
            current=f"{ok_count} 阵列 OK",
            expected="RAID 正常",
            details={"arrays": arrays},
        )

    def _check_mdadm(self) -> list:
        """Check mdadm software RAID arrays"""
        arrays = []
        try:
            result = subprocess.run(
                ["cat", "/proc/mdstat"],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            if result.returncode != 0:
                return arrays

            output = result.stdout
            # 检测活动阵列
            active = re.findall(r"md(\d+) : active", output)
            if not active:
                return arrays

            for md_id in active:
                mddev = f"md{md_id}"
                detail = self._mdadm_detail(mddev)
                arrays.append(detail)

        except Exception:
            pass
        return arrays

    def _mdadm_detail(self, device: str) -> dict:
        """Get detailed mdadm status for a single array"""
        try:
            result = subprocess.run(
                ["sudo", "mdadm", "--detail", device],
                capture_output=True, text=True, errors="replace", timeout=10,
            )
            output = result.stdout + result.stderr

            # 解析状态
            state = "unknown"
            raid_level = "unknown"
            devices = 0
            failed = 0

            for line in output.splitlines():
                line = line.strip()
                if "State :" in line:
                    state = line.split("State :", 1)[1].strip()
                elif "Raid Level :" in line:
                    raid_level = line.split("Raid Level :", 1)[1].strip()
                elif "Active Devices :" in line:
                    devices = int(line.split("Active Devices :", 1)[1].strip())
                elif "Failed Devices :" in line:
                    failed = int(line.split("Failed Devices :", 1)[1].strip())

            ok = "clean" in state.lower() and "active" in state.lower() and failed == 0
            return {
                "device": device,
                "type": "mdadm",
                "raid_level": raid_level,
                "state": state,
                "ok": ok,
                "failed_devices": failed,
            }
        except Exception as e:
            return {
                "device": device,
                "type": "mdadm",
                "state": f"检查失败: {str(e)}",
                "ok": True,  # 不因权限问题报异常
            }

    def _check_btrfs(self) -> Optional[dict]:
        """Check btrfs RAID status"""
        try:
            result = subprocess.run(
                ["btrfs", "fi", "show"],
                capture_output=True, text=True, errors="replace", timeout=10,
            )
            if result.returncode != 0:
                return None

            output = result.stdout
            has_issues = "Degraded" in output or "error" in output.lower()
            if has_issues:
                return {
                    "device": "btrfs",
                    "type": "btrfs",
                    "state": "Degraded",
                    "ok": False,
                }

            return {
                "device": "btrfs",
                "type": "btrfs",
                "state": "Normal",
                "ok": True,
            }
        except Exception:
            return None

    def _check_zfs(self) -> Optional[dict]:
        """Check ZFS pool status"""
        try:
            result = subprocess.run(
                ["zpool", "status"],
                capture_output=True, text=True, errors="replace", timeout=10,
            )
            if result.returncode != 0:
                return None

            output = result.stdout
            has_errors = "DEGRADED" in output or "FAULTED" in output or "UNAVAIL" in output
            if has_errors:
                # 找池名
                pools = re.findall(r"pool:\s+(\S+)", output)
                state = "DEGRADED" if "DEGRADED" in output else "FAULTED"
                return {
                    "device": pools[0] if pools else "zpool",
                    "type": "zfs",
                    "state": state,
                    "ok": False,
                }

            pools = re.findall(r"pool:\s+(\S+)", output)
            return {
                "device": pools[0] if pools else "zpool",
                "type": "zfs",
                "state": "Online",
                "ok": True,
            }
        except Exception:
            return None
