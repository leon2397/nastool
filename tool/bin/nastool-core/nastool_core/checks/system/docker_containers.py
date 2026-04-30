# -*- coding: utf-8 -*-
"""Docker 容器状态检测"""
from __future__ import annotations

import subprocess
from nastool_core.checks.decorators import check


@check(id="docker_containers", category="SYSTEM", title="Docker Containers",
       description="检查 Docker 容器运行状态")
def docker_containers(ctx):
    r = subprocess.run("docker ps --format '{{.Names}}|{{.Status}}'", shell=True,
                       capture_output=True, text=True, errors="replace", timeout=15)
    if r.returncode != 0:
        return ctx.passed(current="no docker",
                          expected="n/a",
                          message="Docker not available",
                          severity="INFO")

    lines = [l for l in r.stdout.strip().split("\n") if l]
    if not lines:
        return ctx.passed(current="0 running",
                          expected="any",
                          message="No running containers",
                          details={"count": 0})

    running = 0
    for line in lines:
        if "Up" in line or "running" in line.lower():
            running += 1

    if running == 0:
        return ctx.passed(current="0 running",
                          expected="any",
                          message="All containers stopped",
                          severity="WARNING",
                          details={"total": len(lines)})
    return ctx.passed(current=f"{running} running",
                      expected="running",
                      message=f"{running}/{len(lines)} containers running",
                      details={"running": running, "total": len(lines),
                               "containers": [l.replace("|", " ") for l in lines[:5]]})
