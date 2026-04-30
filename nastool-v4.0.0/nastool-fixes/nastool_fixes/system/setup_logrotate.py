# -*- coding: utf-8 -*-
"""
fixes/system/setup_logrotate.py - Configure logrotate
对应检测: checks/nas/log_disk.py
风险: low | requires_root: True

支持回滚机制。
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from ..base import Fix, FixResult, RollbackInfo, RollbackStatus
from ..registry import register_fix


@register_fix
class SetupLogrotateFix(Fix):
    """配置 logrotate，防止日志无限增长"""

    fix_id = "setup_logrotate"
    title = "配置日志轮转"
    description = "配置 logrotate 规则，防止 /var/log 无限增长"
    risk = "low"
    requires_root = True
    supports_rollback = True

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
        changed_files: List[str] = []
        backup_files: List[str] = []

        original_state = self._capture_logrotate_state()

        if os.path.exists(self.LOGROTATE_CONF):
            backup = self.LOGROTATE_CONF + ".bak.nastool"
            ok, _ = self._run_command(f"cp {self.LOGROTATE_CONF} {backup}")
            if ok:
                backup_files.append(backup)
                changed_files.append(backup)
                commands_run.append(f"cp {self.LOGROTATE_CONF} {backup}")

        try:
            with open(self.LOGROTATE_CONF, "w") as f:
                f.write(self.CONFIG)
            commands_run.append(f"write {self.LOGROTATE_CONF}")
            changed_files.append(self.LOGROTATE_CONF)

            ok, out = self._run_command(f"chmod 644 {self.LOGROTATE_CONF}")
            commands_run.append(f"chmod 644 {self.LOGROTATE_CONF}")

            rollback_info = RollbackInfo(
                fix_id=self.fix_id,
                timestamp=datetime.now().isoformat(),
                original_state={'logrotate_config': original_state},
                backup_files=backup_files,
                rollback_commands=[f"rm {self.LOGROTATE_CONF}"] + [f"mv {f} {self.LOGROTATE_CONF}" for f in backup_files if f != self.LOGROTATE_CONF + ".bak.nastool"],
                status=RollbackStatus.NOT_NEEDED,
            )
            self._save_rollback_info(rollback_info)

            return FixResult(
                fix_id=self.fix_id,
                success=True,
                message=f"logrotate 配置已写入 {self.LOGROTATE_CONF}。"
                        "日志将每日轮转，保留 7 天，启用压缩。",
                commands_run=commands_run,
                changed_files=changed_files,
            )
        except Exception as e:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"写入 logrotate 配置失败: {e}",
                commands_run=commands_run,
                changed_files=changed_files,
            )

    def _capture_logrotate_state(self) -> Dict[str, Any]:
        """捕获 logrotate 配置的当前状态"""
        try:
            if os.path.exists(self.LOGROTATE_CONF):
                with open(self.LOGROTATE_CONF, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                return {
                    'path': self.LOGROTATE_CONF,
                    'exists': True,
                    'content': content,
                }
            else:
                return {
                    'path': self.LOGROTATE_CONF,
                    'exists': False,
                }
        except Exception as e:
            print(f"[WARN] 捕获 logrotate 配置状态失败: {e}")
            return {'path': self.LOGROTATE_CONF, 'exists': False}

    def _execute_rollback(self) -> FixResult:
        """执行回滚操作"""
        rollback_info = self._rollback_info

        if rollback_info is None:
            rollback_info = self._load_rollback_info(self.fix_id)
            if rollback_info is None:
                return FixResult(
                    fix_id=self.fix_id,
                    success=False,
                    message="没有找到可用的回滚信息",
                    rollback_status=RollbackStatus.FAILED,
                )

        try:
            original_state = rollback_info.original_state
            config_state = original_state.get('logrotate_config', {})

            if config_state.get('exists', False):
                content = config_state.get('content', '')
                with open(self.LOGROTATE_CONF, 'w') as f:
                    f.write(content)

                rollback_info.status = RollbackStatus.SUCCESSFUL
                rollback_info.message = "logrotate 配置已回滚到原始状态"

                return FixResult(
                    fix_id=self.fix_id,
                    success=True,
                    message="logrotate 配置已回滚到原始状态",
                    rollback_status=RollbackStatus.SUCCESSFUL,
                    rollback_message="logrotate 配置已恢复",
                )
            else:
                if os.path.exists(self.LOGROTATE_CONF):
                    os.remove(self.LOGROTATE_CONF)

                rollback_info.status = RollbackStatus.SUCCESSFUL
                rollback_info.message = "logrotate 配置文件已删除（回滚到不存在状态）"

                return FixResult(
                    fix_id=self.fix_id,
                    success=True,
                    message="logrotate 配置文件已删除",
                    rollback_status=RollbackStatus.SUCCESSFUL,
                    rollback_message="logrotate 配置已删除（恢复到修复前状态）",
                )

        except Exception as e:
            rollback_info.status = RollbackStatus.FAILED
            rollback_info.message = f"回滚异常: {str(e)}"

            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"回滚失败: {e}",
                rollback_status=RollbackStatus.FAILED,
            )

    def rollback(self) -> FixResult:
        """回滚修复操作"""
        print(f"[ROLLBACK] 正在回滚 {self.fix_id}...")

        result = super().rollback()

        if result.rollback_status == RollbackStatus.SUCCESSFUL:
            print(f"[OK] 回滚成功: {result.message}")
        elif result.rollback_status == RollbackStatus.NOT_SUPPORTED:
            print(f"[X] 此修复不支持回滚")
        elif result.rollback_status == RollbackStatus.FAILED:
            print(f"[X] 回滚失败: {result.message}")

        return result

    def _command_exists(self, cmd: str) -> bool:
        import shutil
        return shutil.which(cmd) is not None
