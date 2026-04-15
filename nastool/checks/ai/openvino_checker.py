# -*- coding: utf-8 -*-
"""OpenVINO 版本检测 (declarative style)"""

from __future__ import annotations

import os
import shutil
import subprocess

from checks.decorators import check, CheckContext
from checks.base import CheckCategory, CheckSeverity, CheckResult


@check(
    id="openvino_version",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="OpenVINO Version",
    description="检查 Intel OpenVINO 推理引擎版本",
    timeout=10,
)
def openvino_version(ctx: CheckContext) -> CheckResult:
    """检测 Intel OpenVINO 推理引擎版本"""
    # 方法1: 通过 Python 检测
    try:
        import openvino as ov
        version = ov.__version__
        try:
            core = ov.Core()
            devices = core.available_devices
            return ctx.passed(
                current=version,
                expected="installed",
                message=f"OpenVINO {version} (devices: {', '.join(devices)})",
                details={"version": version, "devices": list(devices)},
            )
        except Exception:
            return ctx.passed(
                current=version,
                expected="installed",
                message=f"OpenVINO {version}",
            )
    except ImportError:
        pass

    # 方法2: 通过命令行工具
    for tool in ["ov_info", "openvino_info"]:
        ov_path = shutil.which(tool)
        if ov_path:
            try:
                result = subprocess.run([ov_path, "--version"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return ctx.passed(
                        current=result.stdout.strip(),
                        expected="installed",
                        message=f"OpenVINO CLI: {result.stdout.strip()}",
                    )
            except Exception:
                pass

    # 方法3: 查找安装路径
    if os.path.exists("/opt/intel/openvino"):
        return ctx.passed(
            current="installed",
            expected="installed",
            message="OpenVINO 已安装: /opt/intel/openvino",
        )

    return ctx.failed(
        current="not installed",
        expected="installed",
        message="OpenVINO 未安装",
        fix_available=True,
        fix_id="install_openvino",
        fix_command="pip install openvino",
        fix_description="安装 Intel OpenVINO",
        fix_risk="low",
    )


# Backward-compatible class alias
OpenVINOVersionCheck = openvino_version
