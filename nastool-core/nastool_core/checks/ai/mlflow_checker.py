# -*- coding: utf-8 -*-
"""MLflow 检测 (declarative style)"""

from __future__ import annotations

import shutil

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult

_MLFLOW_HOST = "localhost"
_MLFLOW_PORT = 5000


@check(
    id="mlflow",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="MLflow",
    description="检查 MLflow ML 实验跟踪平台状态",
    timeout=15,
    enable_accuracy=True)
def mlflow(ctx: CheckContext) -> CheckResult:
    """检测 MLflow 是否安装及运行状态"""
    try:
        import mlflow as _mlflow
        version = _mlflow.__version__

        try:
            import requests
        except ImportError:
            return ctx.passed(
                current=f"v{version}", expected="installed",
                message=f"MLflow {version} (requests 库不可用，无法检查服务)",
                details={"version": version},
            )

        # 检测服务器
        try:
            resp = requests.get(f"http://{_MLFLOW_HOST}:{_MLFLOW_PORT}/api/2.0/mlflow/", timeout=5)
            if resp.status_code == 200:
                try:
                    exp_resp = requests.get(
                        f"http://{_MLFLOW_HOST}:{_MLFLOW_PORT}/api/2.0/mlflow/experiments/list", timeout=5,
                    )
                    if exp_resp.status_code == 200:
                        experiments = exp_resp.json().get("experiments", [])
                        return ctx.passed(
                            current=f"v{version}", expected="installed",
                            message=f"MLflow {version} 运行中 (experiments: {len(experiments)})",
                            details={"version": version, "experiments": len(experiments)},
                        )
                except Exception:
                    pass
                return ctx.passed(
                    current=f"v{version}", expected="installed",
                    message=f"MLflow {version} (服务器响应正常)",
                    details={"version": version},
                )
        except Exception:
            return ctx.passed(
                current=f"v{version}", expected="installed",
                message=f"MLflow {version} (服务器未运行)",
                details={"version": version},
            )
    except ImportError:
        pass

    # 检查 CLI
    if shutil.which("mlflow"):
        return ctx.failed(
            current="CLI installed", expected="installed",
            message="MLflow CLI 已安装但 Python 包未安装",
            fix_available=True, fix_id="install_mlflow",
            fix_command="pip install mlflow",
            fix_description="安装 MLflow", fix_risk="low",
        )

    return ctx.failed(
        current="not installed", expected="installed",
        message="MLflow 未安装",
        fix_available=True, fix_id="install_mlflow",
        fix_command="pip install mlflow",
        fix_description="安装 MLflow", fix_risk="low",
    )


# Backward-compatible class alias
MLflowCheck = mlflow
