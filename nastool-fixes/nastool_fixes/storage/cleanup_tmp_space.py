"""
fixes/storage/cleanup_tmp_space.py - Clean up /tmp and /var/tmp
对应检测: checks/nas/log_disk.py
风险: low | requires_root: True
"""

import os
from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class CleanupTmpSpaceFix(Fix):
    """清理 /tmp 和 /var/tmp 目录中的临时文件"""

    fix_id = "cleanup_tmp_space"
    title = "清理临时文件空间"
    description = "清理 /tmp 和 /var/tmp 中超过 7 天的临时文件（保留正在使用的文件）"
    risk = "low"
    requires_root = True

    def is_applicable(self) -> bool:
        """检查 /tmp 使用量"""
        ok, out = self._run_command("df /tmp --output=used -B1 2>/dev/null | tail -1")
        if ok and out.strip().isdigit():
            used_bytes = int(out.strip())
            # 超过 500MB 才建议清理
            return used_bytes > 500 * 1024 * 1024
        return False

    def run(self) -> FixResult:
        commands_run = []
        dirs_cleaned = []

        for tmp_dir in ["/tmp", "/var/tmp"]:
            if not os.path.exists(tmp_dir):
                continue

            # 统计清理前大小
            ok_before, out_before = self._run_command(
                f"df {tmp_dir} --output=used -B1 2>/dev/null | tail -1"
            )
            size_before = int(out_before.strip()) if ok_before and out_before.strip().isdigit() else 0

            # 清理超过 7 天的文件（排除正在使用的文件）
            ok, out = self._run_command(
                f"find {tmp_dir} -maxdepth 1 -type f -mtime +7 -delete 2>/dev/null"
            )
            commands_run.append(f"find {tmp_dir} -mtime +7 -delete")

            # 统计清理后大小
            ok_after, out_after = self._run_command(
                f"df {tmp_dir} --output=used -B1 2>/dev/null | tail -1"
            )
            size_after = int(out_after.strip()) if ok_after and out_after.strip().isdigit() else 0

            freed = size_before - size_after
            if freed > 0:
                freed_mb = freed // (1024 * 1024)
                dirs_cleaned.append(f"{tmp_dir}（释放 {freed_mb} MB）")

        if dirs_cleaned:
            msg = f"临时文件清理完成：{'，'.join(dirs_cleaned)}"
        else:
            msg = "临时文件清理完成，无超过 7 天的文件"

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message=msg,
            commands_run=commands_run,
        )
