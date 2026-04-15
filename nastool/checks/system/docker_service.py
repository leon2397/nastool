# -*- coding: utf-8 -*-
"""Docker 服务检测"""

import subprocess

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class DockerServiceCheck(Check):
    """检测 Docker 服务状态"""

    check_id = "docker_service"
    title = "Docker 服务"
    description = "检测 Docker daemon 是否运行"
    category = CheckCategory.SYSTEM

    def run(self) -> CheckResult:
        # 检查 dockerd 进程
        try:
            result = subprocess.run(
                ["pgrep", "-f", "dockerd"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message="Docker daemon 运行中",
                    current="running",
                    expected="running",
                )
        except Exception:
            pass

        # Windows: 检查 Docker Desktop 服务
        try:
            result = subprocess.run(
                ["sc", "query", "com.docker.service"],
                capture_output=True, text=True, timeout=10
            )
            if "RUNNING" in result.stdout:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message="Docker Desktop 服务运行中",
                    current="running",
                    expected="running",
                )
        except Exception:
            pass

        # 尝试 docker info
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message="Docker 可用",
                    current="available",
                    expected="running",
                )
        except Exception:
            pass

        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="Docker 服务未运行",
            current="not running",
            expected="running",
            fix_available=True,
            fix_id="start_docker",
            fix_command="systemctl start docker",
            fix_description="启动 Docker 服务",
            fix_risk="low",
        )
