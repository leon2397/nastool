from typing import Optional
"""
checks/nas/log_disk.py - Log disk space check
检查 /var/log 目录磁盘占用
"""

import subprocess
import os
import re
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class LogDiskCheck(Check):
    """Check /var/log disk space usage"""

    check_id = "log_disk"
    title = "日志磁盘空间"
    description = "检测 /var/log 目录占用，提前发现日志爆盘风险"
    category = CheckCategory.NAS

    # 警告阈值：日志目录超过此大小（GB）
    WARNING_SIZE_GB = 5
    # 严重阈值
    CRITICAL_SIZE_GB = 10

    # 超大文件阈值（MB）
    LARGE_FILE_MB = 500

    def run(self) -> CheckResult:
        """Run log disk check"""
        log_info = self._analyze_log_dir()

        if log_info is None:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="无法访问 /var/log 目录",
                current="无数据",
                expected="日志目录正常",
            ))

        total_mb = log_info["total_mb"]
        total_gb = total_mb / 1024
        large_files = log_info.get("large_files", [])
        top_files = log_info.get("top_files", [])

        # 数量限制
        large_count = len(large_files)

        if total_gb >= self.CRITICAL_SIZE_GB:
            biggest = top_files[0] if top_files else {}
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"日志目录已达 {total_gb:.1f} GB，严重占用空间！",
                current=f"{total_gb:.1f} GB",
                expected=f"< {self.WARNING_SIZE_GB} GB",
                fix_available=True,
                fix_description=f"日志目录过大（{total_gb:.1f} GB），建议清理旧日志：find /var/log -name '*.gz' -delete",
                fix_command="find /var/log -name '*.gz' -delete && find /var/log -name '*.log' -size +100M -exec truncate -s 0 {} \\;",
                details=log_info,
            ))

        if total_gb >= self.WARNING_SIZE_GB:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"日志目录占用 {total_gb:.1f} GB，建议清理",
                current=f"{total_gb:.1f} GB",
                expected=f"< {self.WARNING_SIZE_GB} GB",
                details=log_info,
            )

        if large_count > 0:
            biggest = top_files[0] if top_files else {}
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.WARNING,
                message=f"日志总量正常（{total_gb:.1f} GB），但有 {large_count} 个大日志文件",
                current=f"{total_gb:.1f} GB，{large_count} 个大文件",
                expected="日志目录干净",
                details=log_info,
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"日志目录状态良好（{total_gb:.1f} GB）",
            current=f"{total_gb:.1f} GB",
            expected=f"< {self.WARNING_SIZE_GB} GB",
            details=log_info,
        )

    def _analyze_log_dir(self) -> Optional[dict]:
        """Analyze /var/log directory size"""
        if not os.path.exists("/var/log"):
            return None

        try:
            # du 统计总大小
            result = subprocess.run(
                ["sudo", "du", "-sm", "/var/log"],
                capture_output=True, text=True, errors="replace", timeout=15,
            )
            total_mb = 0
            if result.returncode == 0:
                match = re.match(r"(\d+)", result.stdout)
                if match:
                    total_mb = int(match.group(1))

            # 找大文件
            large_files = []
            result2 = subprocess.run(
                ["sudo", "find", "/var/log", "-type", "f", "-size", f"+{self.LARGE_FILE_MB}M", "-exec", "ls", "-lh", "{}"],
                capture_output=True, text=True, errors="replace", timeout=30,
            )
            if result2.returncode == 0:
                for line in result2.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 9:
                        size_str = parts[4]
                        path = " ".join(parts[8:])
                        large_files.append({"path": path, "size": size_str})

            # 找最大文件（Top 5）
            top_files = []
            result3 = subprocess.run(
                ["sudo", "find", "/var/log", "-type", "f", "-exec", "ls", "-lhS", "{}"],
                capture_output=True, text=True, errors="replace", timeout=30,
            )
            if result3.returncode == 0:
                for line in result3.stdout.splitlines()[:5]:
                    parts = line.split()
                    if len(parts) >= 9:
                        top_files.append({
                            "size": parts[4],
                            "path": " ".join(parts[8:]),
                        })

            return {
                "total_mb": total_mb,
                "total_gb": total_mb / 1024,
                "large_files": large_files[:10],
                "top_files": top_files[:5],
            }
        except Exception:
            return None
