# -*- coding: utf-8 -*-
"""OpenVINO 版本检测"""

import shutil
import subprocess

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class OpenVINOVersionCheck(Check):
    """检测 Intel OpenVINO 推理引擎版本"""

    check_id = "openvino_version"
    category = CheckCategory.AI
    title = "OpenVINO Version"
    description = "检查 Intel OpenVINO 推理引擎版本"

    def run(self) -> CheckResult:
        # 方法1: 通过 Python 检测
        try:
            import openvino as ov
            version = ov.__version__
            try:
                core = ov.Core()
                devices = core.available_devices
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current=version,
                    expected="installed",
                    message=f"OpenVINO {version} (devices: {', '.join(devices)})",
                    fix_available=False,
                    details={"version": version, "devices": list(devices)},
                )
            except Exception:
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current=version,
                    expected="installed",
                    message=f"OpenVINO {version}",
                    fix_available=False,
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
                        return CheckResult(
                            check_id=self.check_id, category=self.category,
                            severity=CheckSeverity.PASSED, passed=True,
                            title=self.title, current=result.stdout.strip(),
                            expected="installed",
                            message=f"OpenVINO CLI: {result.stdout.strip()}",
                            fix_available=False,
                        )
                except Exception:
                    pass

        # 方法3: 查找安装路径
        for path in ["/opt/intel/openvino"]:
            import os
            if os.path.exists(path):
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="installed",
                    expected="installed",
                    message=f"OpenVINO 已安装: {path}",
                    fix_available=False,
                )

        return CheckResult(
            check_id=self.check_id, category=self.category,
            severity=CheckSeverity.WARNING, passed=False,
            title=self.title, current="not installed",
            expected="installed",
            message="OpenVINO 未安装",
            fix_available=True,
            fix_id="install_openvino",
            fix_command="pip install openvino",
            fix_description="安装 Intel OpenVINO",
            fix_risk="low",
        )
