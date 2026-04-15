from typing import Dict
# -*- coding: utf-8 -*-
"""SSH 安全配置检测"""
import os
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class SSHConfigCheck(Check):
    check_id = "ssh_config"
    title = "SSH 安全配置"
    description = "检测 SSH 配置安全性（密码登录/密钥/端口）"
    category = CheckCategory.SECURITY

    def run(self) -> CheckResult:
        warnings_found = []

        for cfg in ["/etc/ssh/sshd_config", "/etc/sshd_config"]:
            if not os.path.exists(cfg):
                continue
            try:
                with open(cfg) as f:
                    lines = [l.strip() for l in f.readlines()
                             if l.strip() and not l.strip().startswith("#")]
                cfg_dict = {}
                for line in lines:
                    parts = line.split(None, 1)
                    if len(parts) >= 2:
                        cfg_Dict[parts[0].lower()] = parts[1].lower()

                if cfg_dict.get("passwordauthentication", "yes") == "yes":
                    warnings_found.append("允许密码登录（建议改为密钥）")
                root = cfg_dict.get("permitrootlogin", "prohibit-password")
                if root not in ("no", "without-password"):
                    warnings_found.append("允许 root 直接登录")
                if cfg_dict.get("port", "22") == "22":
                    warnings_found.append("使用默认端口 22")
                break
            except Exception:
                pass

        if warnings_found:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.WARNING,
                message="; ".join(warnings_found),
                current="insecure", expected="secure",
                fix_available=True, fix_id="harden_ssh",
                fix_description="禁用密码登录，使用密钥认证",
                fix_risk="medium",
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.PASSED,
            message="SSH 配置安全",
            current="secure", expected="secure",
        )
