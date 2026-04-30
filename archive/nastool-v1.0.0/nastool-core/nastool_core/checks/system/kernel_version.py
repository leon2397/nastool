# -*- coding: utf-8 -*-
"""内核版本检测"""
from __future__ import annotations

import subprocess
from nastool_core.checks.decorators import check


@check(id="kernel_version", category="SYSTEM", title="Kernel Version",
       description="检查 Linux 内核版本")
def kernel_version(ctx):
    try:
        r = subprocess.run("uname -r", shell=True,
                           capture_output=True, text=True, timeout=5)
        kernel = r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        kernel = "unknown"

    if kernel == "unknown":
        return ctx.passed(current="unknown",
                          expected="detectable",
                          message="Could not determine kernel version",
                          severity="WARNING")

    # Parse major version
    try:
        major = int(kernel.split("-")[0].split(".")[0])
        if major < 4:
            return ctx.failed(current=kernel,
                              expected=">= 4.0",
                              message=f"Kernel {kernel} is outdated (< 4.0)",
                              severity="WARNING",
                              fix_available=True,
                              fix_id="update_kernel",
                              fix_command="apt update && apt upgrade",
                              fix_description="Update kernel",
                              fix_risk="high")
    except Exception:
        pass

    return ctx.passed(current=kernel,
                      expected=">= 4.0",
                      message=f"Kernel {kernel}")
