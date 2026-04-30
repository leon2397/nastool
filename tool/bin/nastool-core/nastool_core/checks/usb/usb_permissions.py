# -*- coding: utf-8 -*-
"""
checks/usb/usb_permissions.py - USB device permissions check
v5.0.3
"""

import os
import stat
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


def _check_usb_permissions() -> list:
    """Check USB device node permissions and plugdev group membership."""
    issues = []
    usb_dir = "/dev/bus/usb"
    if not os.path.isdir(usb_dir):
        return []

    # Check if user is in plugdev group
    in_plugdev = False
    try:
        r = subprocess.run(
            ["groups"], capture_output=True, text=True, errors="replace", timeout=3
        )
        groups = r.stdout.split()
        in_plugdev = "plugdev" in groups or "usb" in groups
    except Exception:
        pass

    # Scan USB device nodes
    for bus_dir in sorted(os.listdir(usb_dir)):
        bus_path = os.path.join(usb_dir, bus_dir)
        if not os.path.isdir(bus_path):
            continue
        for dev_file in sorted(os.listdir(bus_path)):
            dev_path = os.path.join(bus_path, dev_file)
            try:
                st = os.stat(dev_path)
                mode = stat.S_IMODE(st.st_mode)
                # World-readable/writable OR group-accessible
                ok = (mode & stat.S_IRGRP) or (mode & stat.S_IROTH)
                if not ok and not in_plugdev:
                    issues.append(f"{dev_path} (add to plugdev group)")
            except PermissionError:
                if not in_plugdev:
                    issues.append(f"{dev_path} (permission denied)")
    return issues


@register_check
class USBPermissionsCheck(Check):
    """Check USB device node permissions"""

    check_id = "usb_permissions"
    category = CheckCategory.USB
    title = "USB Permissions"
    description = "Check USB device node permissions"

    def run(self) -> CheckResult:
        issues = _check_usb_permissions()

        if not issues:
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.PASSED,
                passed=True,
                title=self.title,
                current="All USB devices accessible",
                expected="Readable/writable",
                message="All USB device nodes have appropriate permissions.",
            )

        count = len(issues)
        current = f"{count} device(s) with permission issues"
        msg = f"Permission issues: {', '.join(issues[:3])}"
        if count > 3:
            msg += f" (+{count - 3} more)"

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=CheckSeverity.WARNING,
            passed=False,
            title=self.title,
            current=current,
            expected="Accessible",
            message=msg,
            fix_available=True,
            fix_description="Add user to plugdev group: sudo usermod -aG plugdev $USER",
        )
