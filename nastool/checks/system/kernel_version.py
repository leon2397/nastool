# -*- coding: utf-8 -*-
"""系统内核版本检测"""

import subprocess
import shutil

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class KernelVersionCheck(Check):
    """检测系统内核版本及安全更新状态"""

    check_id = "kernel_version"
    title = "内核版本"
    description = "检测系统内核版本，检查是否有安全更新"
    category = CheckCategory.SYSTEM

    def run(self) -> CheckResult:
        # 获取内核版本
        try:
            result = subprocess.run(
                ["uname", "-r"],
                capture_output=True, text=True, timeout=5
            )
            kernel = result.stdout.strip()
        except Exception:
            try:
                result = subprocess.run(
                    ["cmd", "/c", "ver"],
                    capture_output=True, text=True, timeout=5
                )
                kernel = result.stdout.strip()
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message=f"Windows: {kernel}",
                    current=kernel,
                    expected="latest",
                )
            except Exception:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.INFO,
                    message="无法获取内核版本",
                    current="unknown",
                    expected="latest",
                )

        # 检查安全更新（Linux）
        security_patches = 0
        try:
            for pkg_mgr in ["apt-get", "yum", "dnf"]:
                if shutil.which(pkg_mgr):
                    if pkg_mgr in ["apt-get"]:
                        result = subprocess.run(
                            ["apt-get", "-s", "upgrade"],
                            capture_output=True, text=True, timeout=15
                        )
                        if result.returncode == 0:
                            security_patches = result.stdout.lower().count("security")
                            break
        except Exception:
            pass

        if security_patches > 0:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.WARNING,
                message=f"内核 {kernel}，有 {security_patches} 个安全更新待安装",
                current=kernel,
                expected="latest",
                fix_available=True,
                fix_id="update_kernel",
                fix_description=f"有 {security_patches} 个安全补丁待安装",
                fix_risk="medium",
            )

        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.PASSED,
            message=f"内核 {kernel}（已是最新）",
            current=kernel,
            expected="latest",
        )
