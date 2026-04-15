# -*- coding: utf-8 -*-
"""TorchServe 检测"""

import subprocess
import requests
import shutil
import os

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class TorchServeCheck(Check):
    """检测 PyTorch TorchServe 推理服务状态"""

    check_id = "torchserve"
    category = CheckCategory.AI
    title = "TorchServe"
    description = "检查 PyTorch TorchServe 推理服务状态"

    def __init__(self, host: str = "localhost", port: int = 8080):
        super().__init__()
        self.host = host
        self.port = port

    def run(self) -> CheckResult:
        # 通过 HTTP API 检测
        try:
            resp = requests.get(f"http://{self.host}:{self.port}/v1/models", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="running",
                    expected="running",
                    message=f"TorchServe 运行中 (models: {len(models)})",
                    fix_available=False,
                    details={"model_count": len(models)},
                )
        except requests.exceptions.RequestException:
            pass

        # 通过进程检测
        try:
            result = subprocess.run(["pgrep", "-f", "torchserve"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="running",
                    expected="running",
                    message="TorchServe 进程运行中",
                    fix_available=False,
                )
        except Exception:
            pass

        # 检查命令
        ts = shutil.which("torchserve")
        if ts:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.WARNING, passed=False,
                title=self.title, current="installed",
                expected="running",
                message="TorchServe 已安装但未运行",
                fix_available=True,
                fix_id="start_torchserve",
                fix_command="torchserve --start --model-store /model_store",
                fix_description="启动 TorchServe",
                fix_risk="low",
            )

        # 检查 .mar 文件
        for store in ["/model_store", "/opt/model_store"]:
            if os.path.exists(store):
                mar_files = [f for f in os.listdir(store) if f.endswith(".mar")]
                if mar_files:
                    return CheckResult(
                        check_id=self.check_id, category=self.category,
                        severity=CheckSeverity.WARNING, passed=False,
                        title=self.title, current=f"{len(mar_files)} .mar files",
                        expected="running",
                        message=f"找到 {len(mar_files)} 个 TorchServe 模型存档",
                        fix_available=True,
                        fix_id="start_torchserve",
                        fix_command="torchserve --start --model-store /model_store",
                        fix_description="启动 TorchServe",
                        fix_risk="low",
                    )

        return CheckResult(
            check_id=self.check_id, category=self.category,
            severity=CheckSeverity.WARNING, passed=False,
            title=self.title, current="not installed",
            expected="running",
            message="TorchServe 未安装",
            fix_available=True,
            fix_id="install_torchserve",
            fix_command="pip install torchserve",
            fix_description="安装 TorchServe",
            fix_risk="medium",
        )
