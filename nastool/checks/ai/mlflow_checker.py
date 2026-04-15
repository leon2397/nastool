# -*- coding: utf-8 -*-
"""MLflow 检测"""

import subprocess
import requests
import shutil

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class MLflowCheck(Check):
    """检测 MLflow 是否安装及运行状态"""

    check_id = "mlflow"
    category = CheckCategory.AI
    title = "MLflow"
    description = "检查 MLflow ML 实验跟踪平台状态"

    def __init__(self, host: str = "localhost", port: int = 5000):
        super().__init__()
        self.host = host
        self.port = port

    def run(self) -> CheckResult:
        # 方法1: 尝试导入 mlflow
        try:
            import mlflow
            version = mlflow.__version__
            # 检测服务器
            try:
                resp = requests.get(f"http://{self.host}:{self.port}/api/2.0/mlflow/", timeout=5)
                if resp.status_code == 200:
                    exp_resp = requests.get(
                        f"http://{self.host}:{self.port}/api/2.0/mlflow/experiments/list", timeout=5
                    )
                    if exp_resp.status_code == 200:
                        experiments = exp_resp.json().get("experiments", [])
                        return CheckResult(
                            check_id=self.check_id, category=self.category,
                            severity=CheckSeverity.PASSED, passed=True,
                            title=self.title, current=f"v{version}",
                            expected="installed",
                            message=f"MLflow {version} 运行中 (experiments: {len(experiments)})",
                            fix_available=False,
                            details={"version": version, "experiments": len(experiments)},
                        )
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current=f"v{version}",
                    expected="installed",
                    message=f"MLflow {version} (本地，仅 CLI 可用)",
                    fix_available=False,
                    details={"version": version},
                )
            except requests.exceptions.RequestException:
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current=f"v{version}",
                    expected="installed",
                    message=f"MLflow {version} (服务器未运行)",
                    fix_available=False,
                    details={"version": version},
                )
        except ImportError:
            pass

        # 方法2: 检查 CLI
        mlflow_cli = shutil.which("mlflow")
        if mlflow_cli:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.WARNING, passed=False,
                title=self.title, current="CLI installed",
                expected="installed",
                message="MLflow CLI 已安装但 Python 包未安装",
                fix_available=True,
                fix_id="install_mlflow",
                fix_command="pip install mlflow",
                fix_description="安装 MLflow",
                fix_risk="low",
            )

        return CheckResult(
            check_id=self.check_id, category=self.category,
            severity=CheckSeverity.WARNING, passed=False,
            title=self.title, current="not installed",
            expected="installed",
            message="MLflow 未安装",
            fix_available=True,
            fix_id="install_mlflow",
            fix_command="pip install mlflow",
            fix_description="安装 MLflow",
            fix_risk="low",
        )
