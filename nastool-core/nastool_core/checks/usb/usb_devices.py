# -*- coding: utf-8 -*-
"""
checks/usb/usb_devices.py - USB device detection
v5.0.3
"""

import os
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


def _lsusb() -> str:
    """Run lsusb and return output, or mock on non-Linux."""
    if os.name != "posix":
        return "mock: non-Linux\n"
    try:
        r = subprocess.run(
            ["lsusb"], capture_output=True, text=True, errors="replace", timeout=5
        )
        return r.stdout or ""
    except FileNotFoundError:
        return "mock: lsusb not found\n"
    except subprocess.TimeoutExpired:
        return "mock: lsusb timeout\n"


@register_check
class USBDevicesCheck(Check):
    """Detect connected USB devices"""

    check_id = "usb_devices"
    category = CheckCategory.USB
    title = "USB Devices"
    description = "Detect connected USB devices"

    def run(self) -> CheckResult:
        output = _lsusb()
        lines = [l for l in output.strip().split("\n") if l and not l.startswith("mock:")]

        if not lines:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.INFO,
                passed=True,
                title=self.title,
                current="No USB devices detected",
                expected="Any",
                message="No USB devices currently connected.",
            ))

        count = len(lines)
        current = f"{count} device(s) detected"
        summary = lines[:4]
        extra = f" +{count - 4} more" if count > 4 else ""
        detail = "; ".join(summary) + extra

        return self._enhance_result_with_accuracy(CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=CheckSeverity.INFO,
            passed=True,
            title=self.title,
            current=current,
            expected="Any",
            message=f"{current}: {detail}",
        ))
