# -*- coding: utf-8 -*-
"""系统更新检测"""
import subprocess, shutil
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class PackageUpdatesCheck(Check):
    check_id = "package_updates"
    title = "系统更新"
    description = "检测待安装的系统包更新数量"
    category = CheckCategory.SYSTEM

    def run(self) -> CheckResult:
        for pkg_mgr in ["apt-get", "yum", "dnf", "pacman"]:
            if not shutil.which(pkg_mgr):
                continue
            try:
                if pkg_mgr == "apt-get":
                    result = subprocess.run(
                        ["apt-get", "-s", "upgrade"],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        count = result.stdout.count("\n")
                        if count >= 50:
                            return CheckResult(
                                check_id=self.check_id, title=self.title,
                                category=self.category, passed=False,
                                severity=CheckSeverity.CRITICAL,
                                message=f"有 {count} 个包待更新",
                                current=f"{count} updates", expected="up to date",
                                fix_available=True, fix_id="update_system",
                                fix_command="apt update && apt upgrade -y",
                                fix_description="执行系统更新",
                                fix_risk="medium",
                            )
                        elif count >= 10:
                            return CheckResult(
                                check_id=self.check_id, title=self.title,
                                category=self.category, passed=False,
                                severity=CheckSeverity.WARNING,
                                message=f"有 {count} 个包待更新",
                                current=f"{count} updates", expected="up to date",
                                fix_available=True, fix_id="update_system",
                                fix_command="apt update && apt upgrade -y",
                                fix_description="执行系统更新",
                                fix_risk="medium",
                            )
                        return CheckResult(
                            check_id=self.check_id, title=self.title,
                            category=self.category, passed=True,
                            severity=CheckSeverity.PASSED,
                            message="系统已是最新",
                            current="up to date", expected="up to date",
                        )
            except Exception:
                pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.INFO,
            message="无法检测更新（权限不足或非 Linux）",
            current="unknown", expected="up to date",
        )
