# -*- coding: utf-8 -*-
"""Docker 服务检测"""
from __future__ import annotations

import subprocess
from nastool_core.checks.decorators import check


@check(id="docker_info", category="SYSTEM", title="Docker Service",
       description="检查 Docker 服务是否运行")
def docker_info(ctx):
    r = subprocess.run("docker info", shell=True,
                       capture_output=True, text=True, errors="replace", timeout=10)
    if r.returncode == 0:
        version = ""
        for line in r.stdout.split("\n"):
            if "Server Version" in line or "Server:" in line:
                version = line.split(":")[-1].strip()
                break
        return ctx.passed(current="running",
                          expected="running",
                          message=f"Docker running{': ' + version if version else ''}",
                          details={"version": version})
    else:
        return ctx.failed(current="not running",
                          expected="running",
                          message="Docker service not running",
                          fix_available=True,
                          fix_id="install_docker",
                          fix_command="curl -fsSL https://get.docker.com | sh",
                          fix_description="Install Docker",
                          fix_risk="medium")
