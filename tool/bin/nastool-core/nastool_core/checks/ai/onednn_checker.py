# -*- coding: utf-8 -*-
"""MKL-DNN / OneDNN 版本检测 (declarative style)"""

from __future__ import annotations

import glob
import re
import shutil
from pathlib import Path

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult


@check(
    id="onednn_version",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="OneDNN / MKL-DNN",
    description="检查 Intel OneDNN 深度神经网络库版本",
    timeout=10,
)
def onednn_version(ctx: CheckContext) -> CheckResult:
    """检测 Intel OneDNN (原 MKL-DNN) 库版本"""
    # 方法1: 通过 PyTorch 检测
    try:
        import torch
        if hasattr(torch.backends, "mkl") and torch.backends.mkl.is_available():
            return ctx.passed(
                current="available via PyTorch",
                expected="installed",
                message="OneDNN (MKL) 通过 PyTorch 可用",
            )
    except (ImportError, AttributeError):
        pass

    # 方法2: 通过 oneDNN Python 包
    try:
        import onednn as dnnl
        version = getattr(dnnl, "__version__", "unknown")
        return ctx.passed(
            current=f"v{version}",
            expected="installed",
            message=f"OneDNN {version}",
        )
    except ImportError:
        pass

    # 方法3: 查找库文件
    found = set()
    for pattern in ["/usr/lib/x86_64-linux-gnu", "/usr/local/lib"]:
        for lib in glob.glob(f"{pattern}/lib*mkldnn*") + glob.glob(f"{pattern}/lib*dnnl*"):
            m = re.search(r"lib(?:mkldnn|dnnl)\.so\.(\d+)", Path(lib).name)
            if m:
                found.add(m.group(1))
    if found:
        return ctx.passed(
            current=f"lib versions: {', '.join(sorted(found))}",
            expected="installed",
            message=f"找到 OneDNN 库 (major versions: {', '.join(sorted(found))})",
        )

    # 方法4: Intel Python
    if shutil.which("ipython"):
        return ctx.passed(
            current="Intel Python",
            expected="installed",
            message="Intel Python 环境已安装 (含 OneDNN)",
        )

    return ctx.failed(
        current="not detected",
        expected="installed",
        message="OneDNN / MKL-DNN 未检测到",
        fix_available=True,
        fix_id="install_onednn",
        fix_command="pip install torch (自动包含 OneDNN)",
        fix_description="安装 PyTorch (自动包含 OneDNN)",
        fix_risk="low",
    )


# Backward-compatible class alias
OneDNNVersionCheck = onednn_version
