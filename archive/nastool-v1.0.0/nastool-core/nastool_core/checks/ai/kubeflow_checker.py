# -*- coding: utf-8 -*-
"""Kubeflow 检测 (declarative style)"""

from __future__ import annotations

import subprocess
import shutil

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult

_KUBEFLOW_NS = "kubeflow"


@check(
    id="kubeflow",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="Kubeflow",
    description="检查 Kubernetes Kubeflow ML 工具链状态",
    timeout=20,
)
def kubeflow(ctx: CheckContext) -> CheckResult:
    """检测 Kubernetes Kubeflow ML 工具链状态"""
    kubectl = shutil.which("kubectl")
    if not kubectl:
        return ctx.failed(
            current="kubectl not found", expected="kubectl available",
            message="kubectl 未安装",
            severity=CheckSeverity.CRITICAL,
            fix_available=True, fix_id="install_kubectl",
            fix_command="curl -LO https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe",
            fix_description="安装 kubectl", fix_risk="low",
        )

    # 检查 Kubernetes 连接
    try:
        result = subprocess.run(["kubectl", "cluster-info"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return ctx.failed(
                current="no cluster access", expected="cluster connected",
                message="无法连接到 Kubernetes 集群",
                severity=CheckSeverity.CRITICAL,
                fix_available=True, fix_id="configure_kubeconfig",
                fix_description="配置 kubeconfig", fix_risk="medium",
            )
    except Exception:
        return ctx.failed(
            current="kubectl failed", expected="kubectl available",
            message="kubectl 连接失败",
            severity=CheckSeverity.CRITICAL,
            fix_available=True, fix_id="check_kubectl",
            fix_description="检查 kubectl 配置", fix_risk="low",
        )

    # 检查 kubeflow 命名空间
    try:
        result = subprocess.run(
            ["kubectl", "get", "namespace", _KUBEFLOW_NS],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            pods_result = subprocess.run(
                ["kubectl", "get", "pods", "-n", _KUBEFLOW_NS],
                capture_output=True, text=True, timeout=10,
            )
            if pods_result.returncode == 0:
                lines = pods_result.stdout.strip().split("\n")
                running = sum(1 for line in lines[1:] if "Running" in line)
                total = len(lines) - 1
                return ctx.passed(
                    current=f"{running}/{total} pods running",
                    expected="deployed",
                    message=f"Kubeflow 运行中 (pods: {running}/{total})",
                    details={"running_pods": running, "total_pods": total},
                )
            return ctx.passed(
                current="namespace exists", expected="deployed",
                message=f"Kubeflow 命名空间存在: {_KUBEFLOW_NS}",
            )
        return ctx.failed(
            current="not deployed", expected="deployed",
            message=f"Kubeflow 命名空间不存在: {_KUBEFLOW_NS}",
            fix_available=True, fix_id="deploy_kubeflow",
            fix_description="部署 Kubeflow", fix_risk="high",
        )
    except Exception as e:
        return ctx.failed(
            current="error", expected="deployed",
            message=f"Kubeflow 检测失败: {str(e)}",
        )


# Backward-compatible class alias
KubeflowCheck = kubeflow
