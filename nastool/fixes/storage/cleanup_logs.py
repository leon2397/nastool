"""
fixes/storage/cleanup_logs.py - Clean up old log files
对应检测: checks/nas/log_disk.py
风险: low | requires_root: True
"""

import os
from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class CleanupLogsFix(Fix):
    """清理 /var/log 目录中的旧日志和压缩归档"""

    fix_id = "cleanup_logs"
    title = "清理旧日志文件"
    description = "删除 /var/log 下超过 30 天的 .gz 日志文件，释放磁盘空间"
    risk = "low"
    requires_root = True

    def is_applicable(self) -> bool:
        """检查是否存在可清理的旧日志"""
        # 检查 .gz 日志
        ok, out = self._run_command("find /var/log -name '*.gz' -type f 2>/dev/null | head -5")
        return ok and out.strip()

    def run(self) -> FixResult:
        commands_run = []
        freed_bytes = 0

        # 统计并删除 .gz 日志
        ok_size, out_size = self._run_command(
            "find /var/log -name '*.gz' -type f 2>/dev/null -exec du -b {} + | awk '{sum+=$1} END {print sum}'"
        )
        if ok_size and out_size.strip().isdigit():
            freed_bytes = int(out_size.strip())

        ok_rm, out_rm = self._run_command(
            "find /var/log -name '*.gz' -type f 2>/dev/null -mtime +30 -delete"
        )
        commands_run.append("find /var/log -name '*.gz' -mtime +30 -delete")

        if not ok_rm:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"清理日志失败: {out_rm[:200]}",
                commands_run=commands_run,
            )

        # 同时清理超过 500MB 的单个日志文件
        ok_truncate, _ = self._run_command(
            "find /var/log -name '*.log' -type f -size +500M -exec truncate -s 0 {} +"
        )
        commands_run.append("find /var/log -name '*.log' -size +500M -truncate")

        freed_mb = freed_bytes // (1024 * 1024) if freed_bytes else 0
        msg = f"已清理 /var/log 中 30 天以上的 .gz 日志"
        if freed_mb > 0:
            msg += f"，释放约 {freed_mb} MB"
        msg += "。同时截断了超过 500MB 的单一日志文件。"

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message=msg,
            commands_run=commands_run,
        )
