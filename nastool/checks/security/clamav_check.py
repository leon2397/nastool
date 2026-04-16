# -*- coding: utf-8 -*-
"""ClamAV 杀毒软件检测"""
from __future__ import annotations

import subprocess
from checks.decorators import check


@check(id="clamav", category="SECURITY", title="ClamAV Antivirus",
       description="检测 ClamAV 杀毒软件是否安装")
def clamav_check(ctx):
    try:
        r = subprocess.run(["clamscan", "--version"],
                          capture_output=True, timeout=10)
        if r.returncode == 0:
            ver = r.stdout.splitlines()[0][:60]
            return ctx.result(passed=True, current="installed",
                            expected="installed",
                            message=f"ClamAV: {ver}")
    except Exception:
        pass
    return ctx.result(passed=True, current="not installed",
                    expected="installed",
                    message="ClamAV not installed",
                    severity="INFO",
                    fix_available=True, fix_id="install_clamav",
                    fix_command="apt install clamav && systemctl start clamav-daemon",
                    fix_description="Install ClamAV antivirus",
                    fix_risk="low")
