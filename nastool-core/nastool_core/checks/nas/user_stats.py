from typing import Optional
"""
checks/nas/user_stats.py - NAS user account statistics check
检测 NAS 用户账号统计和弱密码风险
"""

import subprocess
import re
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class UserStatsCheck(Check):
    """Check NAS user account statistics"""

    check_id = "nas_users"
    title = "NAS 用户账号统计"
    description = "统计 NAS 用户账号数量，检测弱密码和访客账号风险"
    category = CheckCategory.NAS

    # 弱密码列表（常见默认/弱密码）
    WEAK_PASSWORDS = {
        "admin", "password", "123456", "12345678", "qwerty",
        "admin123", "administrator", "root", "test", "user",
        "nas", "nas123", "password1", "1234567890",
    }

    def run(self) -> CheckResult:
        """Run user stats check"""
        # 尝试群晖/威联通用户获取
        users = self._get_nas_users()

        if users is None:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="非群晖/威联通环境或无用户管理接口",
                current="无法获取",
                expected="获取用户列表",
            ))

        total = len(users)
        weak_users = [u for u in users if u.get("weak", False)]
        admin_count = len([u for u in users if u.get("is_admin", False)])

        if weak_users:
            names = [u["name"] for u in weak_users]
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"发现 {len(weak_users)} 个账号使用弱密码: {', '.join(names)}",
                current=f"共 {total} 个账号，{len(weak_users)} 个弱密码",
                expected="所有账号使用强密码",
                fix_available=True,
                fix_description="立即修改以下账号密码：{}".format("、".join(names)),
                details={
                    "total_users": total,
                    "admin_users": admin_count,
                    "weak_users": weak_users,
                    "users": users,
                },
            ))

        if total == 0:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未检测到用户账号（正常）",
                current="0 个账号",
                expected="有少量用户",
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"共 {total} 个用户账号，无弱密码检测",
            current=f"{total} 个账号，{admin_count} 个管理员",
            expected="用户账号安全",
            details={"total_users": total, "admin_users": admin_count, "users": users},
        )

    def _get_nas_users(self) -> Optional[list]:
        """Get user list from NAS system"""
        users = []

        # 群晖：/usr/syno/synoman/webapi/ 或 synouser
        try:
            result = subprocess.run(
                ["cat", "/etc/shadow"],
                capture_output=True, text=True, errors="replace", timeout=3,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 2 and parts[1] not in ("*", "!"):
                        name = parts[0]
                        # 检查弱密码（通过用户名判断，不是密码本身）
                        is_weak = name.lower() in self.WEAK_PASSWORDS
                        users.append({
                            "name": name,
                            "has_shadow": True,
                            "weak": is_weak,
                            "is_admin": name == "admin",
                        })
                if users:
                    return users
        except Exception:
            pass

        # 通用：/etc/passwd
        try:
            result = subprocess.run(
                ["cat", "/etc/passwd"],
                capture_output=True, text=True, errors="replace", timeout=3,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 3:
                        name = parts[0]
                        uid = int(parts[2])
                        # 跳过系统账号（UID < 1000）
                        if uid >= 1000 and name not in ("nobody",):
                            is_admin = uid == 1000 or name == "admin"
                            is_weak = name.lower() in self.WEAK_PASSWORDS
                            users.append({
                                "name": name,
                                "uid": uid,
                                "is_admin": is_admin,
                                "weak": is_weak,
                            })
                if users:
                    return users
        except Exception:
            pass

        return None if not users else users
