# -*- coding: utf-8 -*-
"""
fixes/security/disable_root_login.py - Disable SSH root login
对应检测: checks/security/ssh_root.py
风险: medium | requires_root: True

支持回滚机制。
"""

import re
import json
from datetime import datetime
from typing import Dict, Any
from ..base import Fix, FixResult, RollbackInfo, RollbackStatus
from ..registry import register_fix


@register_fix
class DisableRootLoginFix(Fix):
    """禁用 SSH root 直接登录，改为普通用户 + sudo"""

    fix_id = "disable_root_login"
    title = "禁用 SSH Root 登录"
    description = "将 SSH 配置从 PermitRootLogin yes 改为 no，提升安全性"
    risk = "medium"
    requires_root = True
    supports_rollback = True

    SSH_CONFIG = "/etc/ssh/sshd_config"
    BACKUP_SUFFIX = ".bak.nastool"

    def is_applicable(self) -> bool:
        """检查是否需要禁用 root 登录"""
        if not self._file_exists(self.SSH_CONFIG):
            return False
        ok, out = self._run_command(f"grep -E '^PermitRootLogin' {self.SSH_CONFIG}")
        if ok and "yes" in out.lower():
            return True
        return False

    def run(self) -> FixResult:
        commands_run = []
        changed_files = []
        backup_files = []

        original_state = self._capture_ssh_config_state()
        if original_state is None:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message="无法捕获 SSH 配置当前状态",
            )

        backup = self.SSH_CONFIG + self.BACKUP_SUFFIX
        ok, _ = self._run_command(f"cp {self.SSH_CONFIG} {backup}")
        commands_run.append(f"cp {self.SSH_CONFIG} {backup}")
        if ok:
            changed_files.append(self.SSH_CONFIG)
            backup_files.append(backup)
        else:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"备份 sshd_config 失败",
                commands_run=commands_run,
            )

        ok, out = self._run_command(
            f"sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' {self.SSH_CONFIG}"
        )
        commands_run.append(f"sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' {self.SSH_CONFIG}")

        if not ok:
            self._restore_backup(backup, self.SSH_CONFIG)
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"修改 sshd_config 失败: {out[:200]}",
                commands_run=commands_run,
                changed_files=changed_files,
            )

        ok_verify, out_verify = self._run_command(
            f"grep '^PermitRootLogin' {self.SSH_CONFIG}"
        )

        rollback_info = RollbackInfo(
            fix_id=self.fix_id,
            timestamp=datetime.now().isoformat(),
            original_state={'ssh_config': original_state},
            backup_files=backup_files,
            rollback_commands=[f"mv {backup} {self.SSH_CONFIG}"],
            status=RollbackStatus.NOT_NEEDED,
        )
        self._save_rollback_info(rollback_info)

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message="SSH root 登录已禁用。需重启 sshd 服务：systemctl restart sshd",
            commands_run=commands_run,
            changed_files=[self.SSH_CONFIG, backup],
            rollback_command=f"mv {backup} {self.SSH_CONFIG}",
        )

    def _capture_ssh_config_state(self) -> Dict[str, Any]:
        """捕获 SSH 配置的当前状态"""
        try:
            if not os.path.exists(self.SSH_CONFIG):
                return None

            with open(self.SSH_CONFIG, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            permit_root = None
            for line in content.split('\n'):
                if line.strip().startswith('PermitRootLogin'):
                    permit_root = line.strip()
                    break

            return {
                'path': self.SSH_CONFIG,
                'permit_root_login': permit_root,
                'content': content,
            }
        except Exception as e:
            print(f"[WARN] 捕获 SSH 配置状态失败: {e}")
            return None

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
            ssh_state = original_state.get('ssh_config', {})

            backup_file = rollback_info.backup_files[0] if rollback_info.backup_files else None
            if not backup_file or not os.path.exists(backup_file):
                return FixResult(
                    fix_id=self.fix_id,
                    success=False,
                    message=f"备份文件不存在: {backup_file}",
                    rollback_status=RollbackStatus.FAILED,
                )

            if self._restore_backup(backup_file, self.SSH_CONFIG):
                rollback_info.status = RollbackStatus.SUCCESSFUL
                rollback_info.message = "SSH 配置已回滚到原始状态"

                return FixResult(
                    fix_id=self.fix_id,
                    success=True,
                    message="SSH 配置已回滚到原始状态",
                    rollback_status=RollbackStatus.SUCCESSFUL,
                    rollback_message="PermitRootLogin 设置已恢复，需要重启 sshd 服务生效",
                )
            else:
                rollback_info.status = RollbackStatus.FAILED
                rollback_info.message = "恢复备份文件失败"

                return FixResult(
                    fix_id=self.fix_id,
                    success=False,
                    message="恢复 SSH 配置失败",
                    rollback_status=RollbackStatus.FAILED,
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

    def _file_exists(self, path: str) -> bool:
        import os
        return os.path.exists(path)

    def _restore_backup(self, backup_path: str, original_path: str) -> bool:
        """从备份恢复文件"""
        try:
            if not os.path.exists(backup_path):
                return False

            import shutil
            shutil.copy2(backup_path, original_path)
            return True
        except Exception as e:
            print(f"[WARN] 恢复文件 {original_path} 失败: {e}")
            return False


import os
