# -*- coding: utf-8 -*-
"""cuDNN 版本检测 (declarative style)"""

from __future__ import annotations

import re
import subprocess

from checks.decorators import check, CheckContext
from checks.base import CheckCategory, CheckSeverity, CheckResult


@check(
    id="cudnn_version",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="cuDNN Version",
    description="检查 NVIDIA cuDNN 深度神经网络库版本",
    timeout=10,
)
def cudnn_version(ctx: CheckContext) -> CheckResult:
    """检测 NVIDIA cuDNN 库版本"""
    # 通过 nvidia-smi 检查是否有 NVIDIA GPU
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return ctx.info(current="no GPU", message="无 NVIDIA GPU，跳过 cuDNN 检测")
    except FileNotFoundError:
        return ctx.info(current="nvidia-smi not found", message="nvidia-smi 不可用，跳过 cuDNN 检测")

    # 通过 PyTorch 检测
    try:
        import torch
        if hasattr(torch.backends, "cudnn"):
            cudnn_enabled = torch.backends.cudnn.is_available()
            cudnn_version = torch.backends.cudnn.version()
            return ctx.passed(
                current=str(cudnn_version),
                expected="installed",
                message=f"cuDNN {cudnn_version} (enabled: {cudnn_enabled})",
                details={"version": cudnn_version, "enabled": cudnn_enabled},
            )
    except ImportError:
        pass

    # 通过库文件检测
    import glob
    found_versions = set()
    for pattern in ["/usr/local/cuda/lib64", "/usr/lib/x86_64-linux-gnu"]:
        for lib_path in glob.glob(f"{pattern}/libcudnn.so.*"):
            m = re.search(r"libcudnn\.so\.(\d+)", lib_path)
            if m:
                found_versions.add(m.group(1))
    if found_versions:
        vers = ", ".join(sorted(found_versions))
        return ctx.passed(
            current=vers,
            expected="installed",
            message=f"cuDNN 已安装 (major versions: {vers})",
        )

    return ctx.failed(
        current="not found",
        expected="cuDNN installed",
        message="cuDNN 库未找到",
        fix_available=True,
        fix_id="install_cudnn",
        fix_command="conda install -c nvidia cudnn",
        fix_description="安装 NVIDIA cuDNN",
        fix_risk="medium",
    )


# Backward-compatible class alias
CUDNNVersionCheck = cudnn_version
