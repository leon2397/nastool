# -*- coding: utf-8 -*-
"""Inode 使用率检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class InodeCheck(Check):
    check_id = "inode_usage"
    title = "Inode 使用率"
    description = "检测文件系统 inode 使用率（文件数量限制）"
    category = CheckCategory.STORAGE

    def run(self) -> CheckResult:
        issues = []
        ok_parts = []
        try:
            result = subprocess.run(["df", "-i"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines()[1:]:
                    parts = [p.strip() for p in line.split()]
                    if len(parts) >= 6:
                        try:
                            use_pct = int(parts[4].replace("%", ""))
                            mount = parts[5]
                            if use_pct >= 95:
                                issues.append(f"{mount}: {use_pct}% inode 严重耗尽")
                            elif use_pct >= 80:
                                issues.append(f"{mount}: {use_pct}% inode 使用率高")
                            else:
                                ok_parts.append(f"{mount}: {use_pct}%")
                        except ValueError:
                            pass
        except Exception:
            pass

        if issues:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.CRITICAL,
                message="; ".join(issues),
                current="high inode", expected="<80%",
                fix_available=True, fix_id="clean_inodes",
                fix_description="清理小文件或增加 inode 数量",
                fix_risk="medium",
            )
        if ok_parts:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.PASSED,
                message=f"Inode 使用率正常: {ok_parts[0]}",
                current="normal", expected="<80%",
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.INFO,
            message="无法获取 inode 信息",
            current="unknown", expected="<80%",
        )
