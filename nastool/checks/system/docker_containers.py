"""
checks/system/docker_containers.py - Docker container status check
检查 Docker 容器运行状态
"""

import subprocess
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class DockerContainersCheck(Check):
    """Check Docker container status"""

    check_id = "docker_containers"
    title = "Docker 容器状态"
    description = "检测 Docker 容器运行状态，识别已停止或异常退出的容器"
    category = CheckCategory.SYSTEM

    def run(self) -> CheckResult:
        """Run Docker container status check"""
        if not self._command_exists("docker"):
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="Docker 未安装",
                current="未安装",
                expected="Docker 已安装",
            )

        try:
            running = self._get_running_containers()
            stopped = self._get_stopped_containers()
            exited = self._get_exited_containers()

            total = len(running) + len(stopped) + len(exited)
            running_count = len(running)

            # 检查是否有异常退出的容器
            problem_containers = [c for c in stopped if c.get("restart_count", 0) > 3]

            if problem_containers:
                names = [c["name"] for c in problem_containers]
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=False,
                    severity=CheckSeverity.WARNING,
                    message=f"发现 {len(problem_containers)} 个频繁重启的容器: {', '.join(names)}",
                    current=f"{running_count} 个运行, {len(stopped)} 个停止",
                    expected="容器运行稳定",
                    details={
                        "running": running,
                        "stopped": stopped,
                        "exited": exited,
                        "problem_containers": problem_containers,
                    },
                )

            if running_count == 0 and total > 0:
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=True,
                    severity=CheckSeverity.WARNING,
                    message=f"所有 {total} 个容器均已停止",
                    current=f"0 个运行, {total} 个停止",
                    expected="有容器在运行",
                    details={"stopped": stopped},
                )

            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.PASSED,
                message=f"Docker 容器运行正常（{running_count}/{total} 运行中）",
                current=f"{running_count} 个运行",
                expected="容器运行正常",
                details={
                    "running": running,
                    "stopped": stopped,
                    "exited": exited,
                },
            )

        except Exception as e:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"Docker 检查失败: {str(e)}",
                current="检查失败",
                expected="正常",
            )

    def _get_running_containers(self) -> list:
        """Get list of running containers"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                capture_output=True, text=True, timeout=10,
            )
            containers = []
            for line in result.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    containers.append({
                        "name": parts[0],
                        "status": parts[1],
                        "state": "running",
                    })
            return containers
        except Exception:
            return []

    def _get_stopped_containers(self) -> list:
        """Get list of stopped containers"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "status=exited", "--filter", "status=stopped",
                 "--format", "{{.Names}}\t{{.Status}}\t{{.Restarts}}"],
                capture_output=True, text=True, timeout=10,
            )
            containers = []
            for line in result.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) >= 1:
                    restart_count = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
                    containers.append({
                        "name": parts[0],
                        "status": parts[1] if len(parts) >= 2 else "exited",
                        "restart_count": restart_count,
                        "state": "stopped",
                    })
            return containers
        except Exception:
            return []

    def _get_exited_containers(self) -> list:
        """Get list of exited containers (subset of stopped)"""
        # docker ps -a --format already covers exited, merged into stopped
        return []
