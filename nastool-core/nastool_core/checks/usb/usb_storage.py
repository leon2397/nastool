# -*- coding: utf-8 -*-
"""
checks/usb/usb_storage.py - USB storage mount check
v5.0.3
"""

import os
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


def _get_usb_mounts() -> list:
    """Get USB storage mount points via /proc/mounts."""
    mounts = []
    try:
        with open("/proc/mounts", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2:
                    continue
                device, path = parts[0], parts[1]
                fs_type = parts[2] if len(parts) > 2 else ""
                if "/dev/sd" in device:
                    fs_ok = any(t in fs_type for t in [
                        "ext4", "vfat", "ntfs", "exfat", "fuseblk", "fuse"
                    ])
                    if fs_ok:
                        mounts.append({"source": device, "target": path, "fs": fs_type})
    except FileNotFoundError:
        pass
    return mounts


@register_check
class USBStorageCheck(Check):
    """Check USB storage mount status"""

    check_id = "usb_storage_mount"
    category = CheckCategory.USB
    title = "USB Storage Mount"
    description = "Check USB storage mount status"

    def run(self) -> CheckResult:
        mounts = _get_usb_mounts()

        if not mounts:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.INFO,
                passed=True,
                title=self.title,
                current="No USB storage mounted",
                expected="N/A",
                message="No USB storage devices are currently mounted.",
            ))

        lines = [f"{m['source']} ({m['fs']}) -> {m['target']}" for m in mounts]
        current = f"{len(mounts)} USB storage(s) mounted"
        msg = f"{current}: {'; '.join(lines)}"

        return self._enhance_result_with_accuracy(CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=CheckSeverity.PASSED,
            passed=True,
            title=self.title,
            current=current,
            expected="N/A",
            message=msg,
        ))
