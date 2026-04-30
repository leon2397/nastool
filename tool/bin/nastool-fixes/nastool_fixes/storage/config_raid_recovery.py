# -*- coding: utf-8 -*-
"""
fixes/storage/config_raid_recovery.py - RAID degraded recovery assistant
对应检测: checks/storage/raid_status.py
风险: high | requires_root: True
"""

from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class RAIDRecoveryFix(Fix):
    """RAID降级恢复指引（提供操作指引，不自动执行高危操作）"""

    fix_id = "config_raid_recovery"
    title = "RAID降级恢复指引"
    description = "检测RAID降级状态，提供数据备份和恢复操作的安全指引"
    risk = "high"
    requires_root = True

    def is_applicable(self) -> bool:
        """检查RAID是否处于降级状态"""
        ok, out = self._run_command("cat /proc/mdstat 2>/dev/null")
        if ok and out:
            if "_" in out or "degraded" in out.lower():
                return True
        return False

    def run(self) -> FixResult:
        commands_run = []
        mdstat_out, _ = self._run_command("cat /proc/mdstat")
        commands_run.append("cat /proc/mdstat")

        # 获取详细信息
        ok_detail, detail = self._run_command(
            "sudo mdadm --detail /dev/md* 2>/dev/null | head -60"
        )
        if ok_detail:
            commands_run.append("mdadm --detail ...")

        # 分析状态
        degraded = []
        for line in mdstat_out.splitlines():
            if "_" in line and "[" in line:
                degraded.append(line.strip())

        msg = "检测到RAID降级状态！\n\n"
        msg += "当前状态:\n" + mdstat_out + "\n\n"

        if degraded:
            msg += "降级阵列:\n" + "\n".join(degraded) + "\n\n"

        msg += "安全建议:\n"
        msg += "1. 立即备份重要数据！\n"
        msg += "2. 检查物理硬盘SMART状态: smartctl -a /dev/sdX\n"
        msg += "3. 更换故障硬盘后，执行: sudo mdadm --add /dev/md0 /dev/sdX\n"
        msg += "4. 重建完成后，验证数据完整性\n"
        msg += "\n此工具不自动执行RAID恢复，以防数据丢失。"

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message=msg,
            commands_run=commands_run,
            details={"mdstat": mdstat_out, "degraded_arrays": degraded},
        )
