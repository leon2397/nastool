# -*- coding: utf-8 -*-
"""MTU 检测"""
import subprocess, re
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class MTUCheck(Check):
    check_id = "mtu_size"
    title = "MTU 大小"
    description = "检测网卡 MTU 设置是否合理"
    category = CheckCategory.NETWORK

    def run(self) -> CheckResult:
        issues, ok_nics = [], []
        try:
            result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "mtu" in line:
                        m = re.search(r"mtu\s+(\d+)", line)
                        if m:
                            mtu = int(m.group(1))
                            iface = line.split(":")[1].strip() if ":" in line else "?"
                            if mtu < 1400:
                                issues.append(f"{iface}: {mtu} 过小")
                            elif mtu >= 9000:
                                ok_nics.append(f"{iface}: {mtu} (Jumbo)")
                            else:
                                ok_nics.append(f"{iface}: {mtu}")
        except Exception:
            pass

        if issues:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.WARNING,
                message="; ".join(issues),
                current="MTU too small", expected="1400+",
                fix_available=True, fix_id="set_mtu",
                fix_description="调整 MTU",
                fix_risk="medium",
            )
        if ok_nics:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.PASSED,
                message=", ".join(ok_nics[:3]),
                current="normal", expected="1400+",
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.INFO,
            message="无法获取 MTU 信息",
            current="unknown", expected="1400+",
        )
