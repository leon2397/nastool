# -*- coding: utf-8 -*-
"""
checks/usb/usb_power.py - USB port power/health check
v5.0.3
"""

import os
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


def _usb_power_info() -> dict:
    """Get USB power status from /sys/bus/usb/devices."""
    info = {
        "overcurrent": False,
        "ports": [],
        "total": 0,
        "has_power_sys": False,
    }
    sys_usb = "/sys/bus/usb/devices"
    if not os.path.isdir(sys_usb):
        return info

    info["has_power_sys"] = True
    for name in os.listdir(sys_usb):
        power_path = os.path.join(sys_usb, name, "power", "active_duration")
        if os.path.isfile(power_path):
            try:
                with open(power_path, "r") as f:
                    val = f.read().strip()
                    if val and val != "0":
                        info["ports"].append({"port": name, "active_ms": val})
                        info["total"] += 1
            except (PermissionError, OSError):
                pass

    # Check overcurrent flag
    oc_path = "/sys/bus/usb/devices/usb1/power/over_current_change"
    if os.path.isfile(oc_path):
        try:
            with open(oc_path, "r") as f:
                if "1" in f.read():
                    info["overcurrent"] = True
        except OSError:
            pass

    return info


@register_check
class USBPowerCheck(Check):
    """Check USB port power status and overcurrent protection"""

    check_id = "usb_power"
    category = CheckCategory.USB
    title = "USB Port Power"
    description = "Check USB port power and overcurrent protection"

    def run(self) -> CheckResult:
        info = _usb_power_info()

        if info["overcurrent"]:
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.CRITICAL,
                passed=False,
                title=self.title,
                current="Overcurrent detected!",
                expected="Normal",
                message="USB overcurrent protection triggered - possible device damage or insufficient power supply. Unplug USB devices immediately.",
                fix_available=False,
                fix_description="Unplug all USB devices, check power supply, and restart.",
            )

        total = info["total"]
        if total == 0:
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.INFO,
                passed=True,
                title=self.title,
                current="USB subsystem active (no detailed power data)",
                expected="Normal",
                message="USB power subsystem detected, but no active power events recorded.",
            )

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=CheckSeverity.PASSED,
            passed=True,
            title=self.title,
            current=f"{total} USB port(s) power-managed",
            expected="Normal",
            message=f"USB power subsystem OK, {total} port(s) with power control data.",
        )
