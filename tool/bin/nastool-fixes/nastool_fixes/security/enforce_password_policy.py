"""
fixes/security/enforce_password_policy.py - Enforce strong password policy
对应检测: checks/nas/user_stats.py
风险: medium | requires_root: True
"""

import re
import os
from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class EnforcePasswordPolicyFix(Fix):
    """强制密码复杂度策略，禁用弱密码用户"""

    fix_id = "enforce_password_policy"
    title = "强制密码策略"
    description = "检查系统用户密码强度，禁用使用弱密码的账号"
    risk = "medium"
    requires_root = True

    WEAK_USERS = {
        "admin", "root", "test", "user", "guest",
        "administrator", "nas", "nasadmin",
    }

    def is_applicable(self) -> bool:
        """检查是否存在弱密码用户"""
        if not os.path.exists("/etc/passwd"):
            return False
        ok, out = self._run_command("cat /etc/passwd")
        if not ok:
            return False
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3:
                uid = int(parts[2])
                if uid >= 1000 and parts[0] in self.WEAK_USERS:
                    return True
        return False

    def run(self) -> FixResult:
        commands_run = []
        weak_found = []

        # 收集弱密码用户名
        ok, out = self._run_command("cat /etc/passwd")
        if ok:
            for line in out.splitlines():
                parts = line.split(":")
                if len(parts) >= 3:
                    uid = int(parts[2])
                    if uid >= 1000 and parts[0] in self.WEAK_USERS:
                        weak_found.append(parts[0])

        if not weak_found:
            return FixResult(
                fix_id=self.fix_id,
                success=True,
                message="未发现弱密码用户，密码策略已合规",
                commands_run=commands_run,
            )

        # 建议锁定这些用户
        locked = []
        failed = []

        for user in weak_found:
            ok_lock, out_lock = self._run_command(f"passwd -l {user}")
            commands_run.append(f"passwd -l {user}")
            if ok_lock:
                locked.append(user)
            else:
                failed.append(f"{user}: {out_lock[:50]}")

        msg = f"已锁定 {len(locked)} 个弱密码账号: {', '.join(locked)}"
        if failed:
            msg += f"\n锁定失败: {', '.join(failed)}"

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message=msg,
            commands_run=commands_run,
            rollback_command="; ".join(f"passwd -u {u}" for u in locked),
        )
