# -*- coding: utf-8 -*-
"""cuDNN 版本检测"""

import subprocess
import re
from pathlib import Path

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class CUDNNVersionCheck(Check):
    """检测 NVIDIA cuDNN 库版本"""

    check_id = "cudnn_version"
    category = CheckCategory.AI
    title = "cuDNN Version"
    description = "检查 NVIDIA cuDNN 深度神经网络库版本"

    def run(self) -> CheckResult:
        # 通过 nvidia-smi 检查是否有 NVIDIA GPU
        try:
            result = subprocess.run(
                ["nvidia-smi"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.INFO, passed=True,
                    title=self.title, current="no GPU",
                    expected="cuDNN available",
                    message="无 NVIDIA GPU，跳过 cuDNN 检测",
                    fix_available=False,
                )
        except FileNotFoundError:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.INFO, passed=True,
                title=self.title, current="nvidia-smi not found",
                expected="cuDNN available",
                message="nvidia-smi 不可用，跳过 cuDNN 检测",
                fix_available=False,
            )

        # 通过 PyTorch 检测
        try:
            import torch
            if hasattr(torch.backends, "cudnn"):
                cudnn_enabled = torch.backends.cudnn.is_available()
                cudnn_version = torch.backends.cudnn.version()
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current=str(cudnn_version),
                    expected="installed",
                    message=f"cuDNN {cudnn_version} (enabled: {cudnn_enabled})",
                    fix_available=False,
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
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.PASSED, passed=True,
                title=self.title, current=vers,
                expected="installed",
                message=f"cuDNN 已安装 (major versions: {vers})",
                fix_available=False,
            )

        return CheckResult(
            check_id=self.check_id, category=self.category,
            severity=CheckSeverity.WARNING, passed=False,
            title=self.title, current="not found",
            expected="cuDNN installed",
            message="cuDNN 库未找到",
            fix_available=True,
            fix_id="install_cudnn",
            fix_command="conda install -c nvidia cudnn",
            fix_description="安装 NVIDIA cuDNN",
            fix_risk="medium",
        )
