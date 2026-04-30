"""
fixes/storage/cleanup_docker_images.py - Clean up Docker dangling images
对应检测: checks/storage/docker_images.py
风险: medium | requires_root: True
"""

from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class CleanupDockerImagesFix(Fix):
    """清理 Docker dangling（悬空）镜像"""

    fix_id = "cleanup_docker_images"
    title = "清理 Docker 悬空镜像"
    description = "删除 Docker dangling 镜像（tag 为 <none> 的镜像），释放磁盘空间"
    risk = "medium"
    requires_root = True

    def is_applicable(self) -> bool:
        """检查是否存在 dangling 镜像"""
        if not self._command_exists("docker"):
            return False
        ok, out = self._run_command("docker images -f 'dangling=true' -q")
        return ok and out.strip()

    def run(self) -> FixResult:
        commands_run = []

        # 统计 dangling 镜像数量和大小
        ok_count, out_count = self._run_command("docker images -f 'dangling=true' --format '{{.Repository}}:{{.Tag}}'")
        dangling_list = [l for l in out_count.strip().splitlines() if l.strip()] if out_count.strip() else []

        # 统计总大小
        ok_size, out_size = self._run_command("docker system df -f 'type=images' 2>/dev/null | awk 'NR>1 {sum+=$4} END {print sum}'")
        freed_mb = int(out_size.strip()) if ok_size and out_size.strip().isdigit() else 0

        # 执行清理
        ok_prune, out_prune = self._run_command("docker image prune -f")
        commands_run.append("docker image prune -f")

        if not ok_prune:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"Docker 镜像清理失败: {out_prune[:200]}",
                commands_run=commands_run,
            )

        freed_mb_after = freed_mb
        ok_size_after, out_size_after = self._run_command(
            "docker images -f 'dangling=true' --format '{{.Size}}' 2>/dev/null | head -1"
        )
        if freed_mb > 0:
            msg = f"已清理 {len(dangling_list)} 个悬空 Docker 镜像，释放约 {freed_mb} MB"
        else:
            msg = "Docker 镜像清理完成，无悬空镜像"

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message=msg,
            commands_run=commands_run,
        )

    def _command_exists(self, cmd: str) -> bool:
        import shutil
        return shutil.which(cmd) is not None
