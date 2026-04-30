"""
fixes/security/disable_root_login.py - Disable SSH root login
对应检测: checks/security/ssh_root.py
风险: medium | requires_root: True
"""

import re
from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class DisableRootLoginFix(Fix):
    """禁用 SSH root 直接登录，改为普通用户 + sudo"""

    fix_id = "disable_root_login"
    title = "禁用 SSH Root 登录"
    description = "将 SSH 配置从 PermitRootLogin yes 改为 no，提升安全性"
    risk = "medium"
    requires_root = True

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

        # 备份
        backup = self.SSH_CONFIG + self.BACKUP_SUFFIX
        ok, _ = self._run_command(f"cp {self.SSH_CONFIG} {backup}")
        commands_run.append(f"cp {self.SSH_CONFIG} {backup}")
        if ok:
            changed_files.append(backup)

        # 替换 PermitRootLogin
        ok, out = self._run_command(
            f"sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' {self.SSH_CONFIG}"
        )
        commands_run.append(f"sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' {self.SSH_CONFIG}")

        if not ok:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"修改 sshd_config 失败: {out[:200]}",
                commands_run=commands_run,
                changed_files=changed_files,
            )

        # 验证
        ok_verify, out_verify = self._run_command(
            f"grep '^PermitRootLogin' {self.SSH_CONFIG}"
        )

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message="SSH root 登录已禁用。需重启 sshd 服务：systemctl restart sshd",
            commands_run=commands_run,
            changed_files=[self.SSH_CONFIG, backup],
            rollback_command=f"mv {backup} {self.SSH_CONFIG}",
        )

    def _file_exists(self, path: str) -> bool:
        import os
        return os.path.exists(path)
