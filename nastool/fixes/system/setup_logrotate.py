"""
fixes/system/setup_logrotate.py - Configure logrotate
对应检测: checks/nas/log_disk.py
风险: low | requires_root: True
"""

from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class SetupLogrotateFix(Fix):
    """配置 logrotate，防止日志无限增长"""

    fix_id = "setup_logrotate"
    title = "配置日志轮转"
    description = "配置 logrotate 规则，防止 /var/log 无限增长"
    risk = "low"
    requires_root = True

    LOGROTATE_CONF = "/etc/logrotate.d/nastool"

    CONFIG = """\
/var/log/nastool/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}

/var/log/syslog {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 syslog adm
}
"""

    def is_applicable(self) -> bool:
        """检查 logrotate 是否已配置 nastool 日志"""
        if not self._command_exists("logrotate"):
            return False
        import os
        return not os.path.exists(self.LOGROTATE_CONF)

    def run(self) -> FixResult:
        commands_run = []

        try:
            with open(self.LOGROTATE_CONF, "w") as f:
                f.write(self.CONFIG)
            commands_run.append(f"write {self.LOGROTATE_CONF}")

            # 设置权限
            ok, out = self._run_command(f"chmod 644 {self.LOGROTATE_CONF}")
            commands_run.append(f"chmod 644 {self.LOGROTATE_CONF}")

            return FixResult(
                fix_id=self.fix_id,
                success=True,
                message=f"logrotate 配置已写入 {self.LOGROTATE_CONF}。"
                        "日志将每日轮转，保留 7 天，启用压缩。",
                commands_run=commands_run,
                changed_files=[self.LOGROTATE_CONF],
            )
        except Exception as e:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"写入 logrotate 配置失败: {e}",
                commands_run=commands_run,
            )

    def _command_exists(self, cmd: str) -> bool:
        import shutil
        return shutil.which(cmd) is not None
