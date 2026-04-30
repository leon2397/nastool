"""
checks/storage/docker_images.py - Docker dangling images check
检测可清理的 dangling Docker 镜像
"""

import subprocess
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class DockerImagesCheck(Check):
    """Check Docker image hygiene"""

    check_id = "docker_images"
    title = "Docker 镜像清理"
    description = "检测 dangling（悬空）Docker 镜像，提示可清理的空间"
    category = CheckCategory.STORAGE

    # 警告阈值：dangling 镜像超过此数量
    WARNING_COUNT = 5
    # 严重阈值：dangling 镜像超过此数量
    CRITICAL_COUNT = 20

    def run(self) -> CheckResult:
        """Run Docker images check"""
        if not self._command_exists("docker"):
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="Docker 未安装",
                current="Docker 未安装",
                expected="Docker 已安装",
            )

        try:
            # 获取 dangling 镜像列表
            result = subprocess.run(
                ["docker", "images", "-f", "dangling=true", "-q"],
                capture_output=True, text=True, errors="replace", timeout=15,
            )

            dangling_ids = [
                line.strip() for line in result.stdout.strip().splitlines() if line.strip()
            ]
            count = len(dangling_ids)

            # 获取总镜像数和 size
            size_result = subprocess.run(
                ["docker", "images", "--format", "{{.Size}}"],
                capture_output=True, text=True, errors="replace", timeout=15,
            )
            total_images = len([
                l for l in size_result.stdout.strip().splitlines() if l
            ])

            # 估算 dangling 镜像占用的空间（需要获取 Size 信息）
            sizes = self._get_dangling_sizes()
            total_wasted_gb = sizes["total_gb"]

            if count == 0:
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=True,
                    severity=CheckSeverity.PASSED,
                    message="无 dangling 镜像，镜像管理正常",
                    current=f"共 {total_images} 个镜像，无悬空",
                    expected="无 dangling 镜像",
                )

            if count >= self.CRITICAL_COUNT or total_wasted_gb >= 5:
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=False,
                    severity=CheckSeverity.WARNING,
                    message=f"发现 {count} 个 dangling 镜像（约 {total_wasted_gb:.1f} GB 可清理）",
                    current=f"{count} 个悬空镜像",
                    expected="无或少量 dangling 镜像",
                    fix_available=True,
                    fix_description=f"可执行 docker image prune 清理约 {total_wasted_gb:.1f} GB 空间",
                    fix_command="docker image prune -f",
                    details={
                        "dangling_count": count,
                        "total_images": total_images,
                        "wasted_gb": total_wasted_gb,
                    },
                )

            if count >= self.WARNING_COUNT:
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=True,
                    severity=CheckSeverity.WARNING,
                    message=f"发现 {count} 个 dangling 镜像（约 {total_wasted_gb:.1f} GB 可清理）",
                    current=f"{count} 个悬空镜像",
                    expected="< 5 个 dangling 镜像",
                    fix_available=True,
                    fix_description=f"可执行 docker image prune 清理约 {total_wasted_gb:.1f} GB",
                    fix_command="docker image prune -f",
                )

            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.PASSED,
                message=f"有 {count} 个 dangling 镜像，但数量在可接受范围",
                current=f"{count} 个悬空镜像",
                expected="< 5 个 dangling 镜像",
            )

        except subprocess.TimeoutExpired:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="Docker 检查超时（可能镜像较多）",
                current="超时",
                expected="正常",
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

    def _get_dangling_sizes(self) -> dict:
        """Get sizes of dangling images"""
        total_bytes = 0
        count = 0
        try:
            result = subprocess.run(
                ["docker", "images", "-f", "dangling=true", "--format", "{{.Size}}"],
                capture_output=True, text=True, errors="replace", timeout=15,
            )
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                count += 1
                size_str = line.upper()
                if "G" in size_str:
                    total_bytes += float(size_str.replace("G", "").replace("GB", "").strip()) * 1024 * 1024 * 1024
                elif "M" in size_str:
                    total_bytes += float(size_str.replace("M", "").replace("MB", "").strip()) * 1024 * 1024
                elif "K" in size_str:
                    total_bytes += float(size_str.replace("K", "").replace("KB", "").strip()) * 1024
        except Exception:
            pass
        return {"total_gb": total_bytes / (1024**3), "count": count}
