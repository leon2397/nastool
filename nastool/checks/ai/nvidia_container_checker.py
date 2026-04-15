# -*- coding: utf-8 -*-
"""NVIDIA Container Toolkit 检测"""

import subprocess
import shutil

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class NVIDIAContainerToolkitCheck(Check):
    """检测 NVIDIA Container Toolkit 状态"""

    check_id = "nvidia_container_toolkit"
    category = CheckCategory.AI
    title = "NVIDIA Container Toolkit"
    description = "检查 NVIDIA Container Toolkit (nvidia-docker) 状态"

    def run(self) -> CheckResult:
        # 方法1: 检查包管理器
        try:
            result = subprocess.run(
                ["dpkg", "-l", "nvidia-container-toolkit"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("ii"):
                        parts = line.split()
                        if len(parts) >= 3:
                            version = parts[2]
                            return CheckResult(
                                check_id=self.check_id, category=self.category,
                                severity=CheckSeverity.PASSED, passed=True,
                                title=self.title, current=f"v{version}",
                                expected="installed",
                                message=f"nvidia-container-toolkit {version} 已安装",
                                fix_available=False,
                            )
        except Exception:
            pass

        # 方法2: 检查容器内 nvidia-smi
        try:
            result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="container GPU available",
                    expected="installed",
                    message="NVIDIA GPU 在容器内可用",
                    fix_available=False,
                )
        except Exception:
            pass

        # 方法3: 检查 Docker NVIDIA runtime
        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.Runtimes}}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and "nvidia" in result.stdout.lower():
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="nvidia runtime configured",
                    expected="installed",
                    message="Docker NVIDIA runtime 已配置",
                    fix_available=False,
                )
        except Exception:
            pass

        # 方法4: 检查 nvidia-container-cli
        cli = shutil.which("nvidia-container-cli")
        if cli:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.PASSED, passed=True,
                title=self.title, current="cli installed",
                expected="installed",
                message=f"nvidia-container-cli: {cli}",
                fix_available=False,
            )

        return CheckResult(
            check_id=self.check_id, category=self.category,
            severity=CheckSeverity.WARNING, passed=False,
            title=self.title, current="not installed",
            expected="installed",
            message="NVIDIA Container Toolkit 未安装",
            fix_available=True,
            fix_id="install_nvidia_container",
            fix_command="distribution=$(. /etc/os-release;echo $ID$VERSION_ID)",
            fix_description="安装 NVIDIA Container Toolkit",
            fix_risk="medium",
        )
