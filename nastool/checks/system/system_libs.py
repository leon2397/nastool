# -*- coding: utf-8 -*-
"""系统库检测"""
from __future__ import annotations

import subprocess
from checks.decorators import check

COMMON_LIBS = ["libgcc_s.so", "libssl.so", "libc.so", "libm.so", "libpthread.so"]


@check(id="system_libs", category="SYSTEM", title="System Libraries",
       description="检查基础系统库是否完整")
def system_libs(ctx):
    missing = []
    for lib in COMMON_LIBS:
        r = subprocess.run(f"ldconfig -p | grep {lib}", shell=True,
                           capture_output=True, text=True, timeout=3)
        if r.returncode != 0 and "ldconfig" not in r.stderr:
            # Try find
            r2 = subprocess.run(f"find /lib -name '{lib}*' 2>/dev/null | head -1",
                                shell=True, capture_output=True, text=True, timeout=5)
            if not r2.stdout.strip():
                missing.append(lib)

    if missing:
        return ctx.result(passed=False, current="some missing",
                          expected="all present",
                          message=f"Missing libs: {', '.join(missing)}",
                          severity="WARNING")
    return ctx.result(passed=True, current="all present",
                      expected="all present",
                      message="All required system libraries present")
