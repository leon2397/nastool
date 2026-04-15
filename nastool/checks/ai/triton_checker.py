# -*- coding: utf-8 -*-
"""Triton Inference Server 检测"""

import subprocess
import requests
import shutil

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class TritonServerCheck(Check):
    """检测 NVIDIA Triton Inference Server 状态"""

    check_id = "triton_server"
    category = CheckCategory.AI
    title = "Triton Server"
    description = "检查 Triton Inference Server 是否运行"

    def __init__(self, host: str = "localhost", port: int = 8000):
        super().__init__()
        self.host = host
        self.port = port

    def run(self) -> CheckResult:
        # 通过 HTTP API 检测
        try:
            resp = requests.get(f"http://{self.host}:{self.port}/v2/health", timeout=5)
            if resp.status_code == 200:
                try:
                    meta_resp = requests.get(f"http://{self.host}:{self.port}/v2/models", timeout=5)
                    if meta_resp.status_code == 200:
                        models = meta_resp.json().get("models", [])
                        return CheckResult(
                            check_id=self.check_id, category=self.category,
                            severity=CheckSeverity.PASSED, passed=True,
                            title=self.title, current="running",
                            expected="running",
                            message=f"Triton Server 运行中 (models: {len(models)})",
                            fix_available=False,
                            details={"model_count": len(models)},
                        )
                except Exception:
                    pass
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="running",
                    expected="running",
                    message="Triton Server 运行中",
                    fix_available=False,
                )
        except requests.exceptions.RequestException:
            pass

        # 通过进程检测
        try:
            result = subprocess.run(["pgrep", "-f", "tritonserver"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="running",
                    expected="running",
                    message="Triton Server 进程运行中",
                    fix_available=False,
                )
        except Exception:
            pass

        # 检查命令
        tritonserver = shutil.which("tritonserver")
        if tritonserver:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.WARNING, passed=False,
                title=self.title, current="installed",
                expected="running",
                message="Triton Server 已安装但未运行",
                fix_available=True,
                fix_id="start_triton",
                fix_command="tritonserver --model-repository=/models",
                fix_description="启动 Triton Server",
                fix_risk="low",
            )

        return CheckResult(
            check_id=self.check_id, category=self.category,
            severity=CheckSeverity.WARNING, passed=False,
            title=self.title, current="not installed",
            expected="running",
            message="Triton Server 未安装",
            fix_available=True,
            fix_id="install_triton",
            fix_command="docker pull nvcr.io/nvidia/tritonserver:xx.x-py3",
            fix_description="安装 Triton Inference Server",
            fix_risk="medium",
        )
