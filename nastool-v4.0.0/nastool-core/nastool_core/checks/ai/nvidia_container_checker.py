# -*- coding: utf-8 -*-
"""NVIDIA Container Toolkit 检测 (declarative style)"""

from __future__ import annotations

import subprocess
import shutil

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult


@check(
    id="nvidia_container_toolkit",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="NVIDIA Container Toolkit",
    description="检查 NVIDIA Container Toolkit (nvidia-docker) 状态",
    timeout=15,
    depends_on=["gpu_detected"],
)
def nvidia_container_toolkit(ctx: CheckContext) -> CheckResult:
    """检测 NVIDIA Container Toolkit 状态"""
    # 方法1: 检查包管理器
    try:
        result = subprocess.run(
            ["dpkg", "-l", "nvidia-container-toolkit"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if line.startswith("ii"):
                    parts = line.split()
                    if len(parts) >= 3:
                        version = parts[2]
                        return ctx.passed(
                            current=f"v{version}",
                            expected="installed",
                            message=f"nvidia-container-toolkit {version} 已安装",
                        )
    except Exception:
        pass

    # 方法2: 检查容器内 nvidia-smi
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return ctx.passed(
                current="container GPU available",
                expected="installed",
                message="NVIDIA GPU 在容器内可用",
            )
    except Exception:
        pass

    # 方法3: 检查 Docker NVIDIA runtime
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.Runtimes}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "nvidia" in result.stdout.lower():
            return ctx.passed(
                current="nvidia runtime configured",
                expected="installed",
                message="Docker NVIDIA runtime 已配置",
            )
    except Exception:
        pass

    # 方法4: 检查 nvidia-container-cli
    cli = shutil.which("nvidia-container-cli")
    if cli:
        return ctx.passed(
            current="cli installed",
            expected="installed",
            message=f"nvidia-container-cli: {cli}",
        )

    return ctx.failed(
        current="not installed",
        expected="installed",
        message="NVIDIA Container Toolkit 未安装",
        fix_available=True,
        fix_id="install_nvidia_container",
        fix_command="distribution=$(. /etc/os-release;echo $ID$VERSION_ID)",
        fix_description="安装 NVIDIA Container Toolkit",
        fix_risk="medium",
    )


# Backward-compatible class alias
NVIDIAContainerToolkitCheck = nvidia_container_toolkit
