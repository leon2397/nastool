# -*- coding: utf-8 -*-
"""
fixes/security/enable_fail2ban.py - Install and configure fail2ban
对应检测: checks/security/login_failures.py
风险: medium | requires_root: True
"""

from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class EnableFail2banFix(Fix):
    """安装并配置fail2ban，防护SSH暴力破解"""

    fix_id = "enable_fail2ban"
    title = "启用 Fail2ban 防护"
    description = "安装fail2ban并配置SSH暴力破解自动封禁"
    risk = "medium"
    requires_root = True

    JAIL_LOCAL = "/etc/fail2ban/jail.local"
    SSHD_JAIL = """
[sshd]
enabled   = true
port      = ssh
filter    = sshd
logpath   = /var/log/auth.log
maxretry  = 5
bantime   = 3600
findtime  = 600
"""

    def is_applicable(self) -> bool:
        """检查fail2ban是否已安装或未启动"""
        ok, _ = self._run_command("fail2ban-client status")
        if ok:
            ok2, out2 = self._run_command("fail2ban-client get sshd enabled")
            if ok2 and "true" in out2.lower():
                return False
        return True

    def run(self) -> FixResult:
        commands_run = []

        # 安装 fail2ban
        os_release_out, _ = self._run_command("cat /etc/os-release")
        system = "unknown"

        if "ubuntu" in os_release_out.lower() or "debian" in os_release_out.lower():
            system = "debian"
        elif "centos" in os_release_out.lower() or "rhel" in os_release_out.lower():
            system = "centos"
        elif "fedora" in os_release_out.lower():
            system = "fedora"

        if system == "debian":
            steps = [
                ("apt update", 120),
                ("apt install -y fail2ban", 180),
            ]
        elif system in ("centos", "fedora"):
            steps = [
                ("yum install -y fail2ban", 180),
            ]
        else:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message="不支持的操作系统，请手动安装fail2ban",
                commands_run=commands_run,
            )

        for cmd, timeout in steps:
            ok, out = self._run_command(cmd, timeout=timeout)
            commands_run.append(cmd)
            if not ok:
                return FixResult(
                    fix_id=self.fix_id,
                    success=False,
                    message=f"安装fail2ban失败: {out[:200]}",
                    commands_run=commands_run,
                )

        # 写入 jail.local
        try:
            with open(self.JAIL_LOCAL, "w") as f:
                f.write(self.SSHD_JAIL)
            commands_run.append(f"write {self.JAIL_LOCAL}")
        except Exception as e:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"写入jail.local失败: {e}",
                commands_run=commands_run,
            )

        # 启动服务
        ok_start, _ = self._run_command("systemctl enable fail2ban")
        commands_run.append("systemctl enable fail2ban")
        if ok_start:
            ok_restart, _ = self._run_command("systemctl restart fail2ban")
            commands_run.append("systemctl restart fail2ban")

        # 验证
        ok_verify, out_verify = self._run_command("fail2ban-client status sshd")
        status_msg = out_verify[:200] if ok_verify else "服务已启动"

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message=f"fail2ban已安装并启用SSH防护: {status_msg}",
            commands_run=commands_run,
            changed_files=[self.JAIL_LOCAL],
        )
