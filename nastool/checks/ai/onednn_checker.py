# -*- coding: utf-8 -*-
"""MKL-DNN / OneDNN 版本检测"""

import subprocess
import shutil
import re
from pathlib import Path

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class OneDNNVersionCheck(Check):
    """检测 Intel OneDNN (原 MKL-DNN) 库版本"""

    check_id = "onednn_version"
    category = CheckCategory.AI
    title = "OneDNN / MKL-DNN"
    description = "检查 Intel OneDNN 深度神经网络库版本"

    def run(self) -> CheckResult:
        # 方法1: 通过 PyTorch 检测
        try:
            import torch
            if hasattr(torch.backends, "mkl") and torch.backends.mkl.is_available():
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="available via PyTorch",
                    expected="installed",
                    message="OneDNN (MKL) 通过 PyTorch 可用",
                    fix_available=False,
                )
        except (ImportError, AttributeError):
            pass

        # 方法2: 通过 oneDNN Python 包
        try:
            import onednn as dnnl
            version = getattr(dnnl, "__version__", "unknown")
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.PASSED, passed=True,
                title=self.title, current=f"v{version}",
                expected="installed",
                message=f"OneDNN {version}",
                fix_available=False,
            )
        except ImportError:
            pass

        # 方法3: 查找库文件
        import glob
        found = set()
        for pattern in ["/usr/lib/x86_64-linux-gnu", "/usr/local/lib"]:
            for lib in glob.glob(f"{pattern}/lib*mkldnn*") + glob.glob(f"{pattern}/lib*dnnl*"):
                m = re.search(r"lib(?:mkldnn|dnnl)\.so\.(\d+)", Path(lib).name)
                if m:
                    found.add(m.group(1))
        if found:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.PASSED, passed=True,
                title=self.title, current=f"lib versions: {', '.join(sorted(found))}",
                expected="installed",
                message=f"找到 OneDNN 库 (major versions: {', '.join(sorted(found))})",
                fix_available=False,
            )

        # 方法4: Intel Python
        if shutil.which("ipython"):
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.PASSED, passed=True,
                title=self.title, current="Intel Python",
                expected="installed",
                message="Intel Python 环境已安装 (含 OneDNN)",
                fix_available=False,
            )

        return CheckResult(
            check_id=self.check_id, category=self.category,
            severity=CheckSeverity.WARNING, passed=False,
            title=self.title, current="not detected",
            expected="installed",
            message="OneDNN / MKL-DNN 未检测到",
            fix_available=True,
            fix_id="install_onednn",
            fix_command="pip install torch (自动包含 OneDNN)",
            fix_description="安装 PyTorch (自动包含 OneDNN)",
            fix_risk="low",
        )
