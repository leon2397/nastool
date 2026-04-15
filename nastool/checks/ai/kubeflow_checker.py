# -*- coding: utf-8 -*-
"""Kubeflow 检测"""

import subprocess
import shutil

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class KubeflowCheck(Check):
    """检测 Kubernetes Kubeflow ML 工具链状态"""

    check_id = "kubeflow"
    category = CheckCategory.AI
    title = "Kubeflow"
    description = "检查 Kubernetes Kubeflow ML 工具链状态"

    def __init__(self, namespace: str = "kubeflow"):
        super().__init__()
        self.namespace = namespace

    def run(self) -> CheckResult:
        # 检查 kubectl
        kubectl = shutil.which("kubectl")
        if not kubectl:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.CRITICAL, passed=False,
                title=self.title, current="kubectl not found",
                expected="kubectl available",
                message="kubectl 未安装",
                fix_available=True,
                fix_id="install_kubectl",
                fix_command="curl -LO https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe",
                fix_description="安装 kubectl",
                fix_risk="low",
            )

        # 检查 Kubernetes 连接
        try:
            result = subprocess.run(["kubectl", "cluster-info"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.CRITICAL, passed=False,
                    title=self.title, current="no cluster access",
                    expected="cluster connected",
                    message="无法连接到 Kubernetes 集群",
                    fix_available=True,
                    fix_id="configure_kubeconfig",
                    fix_description="配置 kubeconfig",
                    fix_risk="medium",
                )
        except Exception:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.CRITICAL, passed=False,
                title=self.title, current="kubectl failed",
                expected="kubectl available",
                message="kubectl 连接失败",
                fix_available=True,
                fix_id="check_kubectl",
                fix_description="检查 kubectl 配置",
                fix_risk="low",
            )

        # 检查 kubeflow 命名空间
        try:
            result = subprocess.run(
                ["kubectl", "get", "namespace", self.namespace],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                pods_result = subprocess.run(
                    ["kubectl", "get", "pods", "-n", self.namespace],
                    capture_output=True, text=True, timeout=10
                )
                if pods_result.returncode == 0:
                    lines = pods_result.stdout.strip().split("\n")
                    running = sum(1 for line in lines[1:] if "Running" in line)
                    total = len(lines) - 1
                    return CheckResult(
                        check_id=self.check_id, category=self.category,
                        severity=CheckSeverity.PASSED, passed=True,
                        title=self.title, current=f"{running}/{total} pods running",
                        expected="deployed",
                        message=f"Kubeflow 运行中 (pods: {running}/{total})",
                        fix_available=False,
                        details={"running_pods": running, "total_pods": total},
                    )
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="namespace exists",
                    expected="deployed",
                    message=f"Kubeflow 命名空间存在: {self.namespace}",
                    fix_available=False,
                )
            else:
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.WARNING, passed=False,
                    title=self.title, current="not deployed",
                    expected="deployed",
                    message=f"Kubeflow 命名空间不存在: {self.namespace}",
                    fix_available=True,
                    fix_id="deploy_kubeflow",
                    fix_description="部署 Kubeflow",
                    fix_risk="high",
                )
        except Exception as e:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.WARNING, passed=False,
                title=self.title, current="error",
                expected="deployed",
                message=f"Kubeflow 检测失败: {str(e)}",
                fix_available=False,
            )
