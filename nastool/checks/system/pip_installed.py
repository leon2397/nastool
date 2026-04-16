# -*- coding: utf-8 -*-
"""pip 工具检测"""
from __future__ import annotations

import subprocess
from checks.decorators import check


@check(id="pip_installed", category="SYSTEM", title="pip Installed",
       description="检查 pip 包管理器是否可用")
def pip_installed(ctx):
    pip3_ok = subprocess.run("pip3 --version", shell=True,
                              capture_output=True, timeout=5).returncode == 0
    pip_ok = (not pip3_ok and
              subprocess.run("pip --version", shell=True,
                             capture_output=True, timeout=5).returncode == 0)
    installed = pip3_ok or pip_ok

    if installed:
        ver_cmd = "pip3 --version" if pip3_ok else "pip --version"
        ver = subprocess.run(ver_cmd, shell=True,
                             capture_output=True, text=True, timeout=5).stdout
        ver_str = ver.split()[1] if ver and len(ver.split()) > 1 else "unknown"
        return ctx.passed(current="installed",
                          expected="installed",
                          message=f"pip available: {ver_str}")
    else:
        apt_ok = subprocess.run("apt --version", shell=True,
                                capture_output=True, timeout=5).returncode == 0
        fix_cmd = "apt install python3-pip" if apt_ok else "Install pip"
        return ctx.failed(current="not installed",
                          expected="installed",
                          message="pip is not installed, cannot install Python packages",
                          fix_available=True, fix_id="install_pip",
                          fix_command=fix_cmd,
                          fix_description="Install pip package manager",
                          fix_risk="low")
