"""
fixes/security/renew_ssl_cert.py - Renew SSL certificate
对应检测: checks/security/ssl_cert.py
风险: medium | requires_root: True
"""

import os
from datetime import datetime
from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class RenewSSLCertFix(Fix):
    """生成 Let's Encrypt SSL 自签名证书（临时方案）"""

    fix_id = "renew_ssl_cert"
    title = "续期 SSL 证书"
    description = "为即将过期或已过期的 SSL 证书生成临时续期"
    risk = "medium"
    requires_root = True

    CERT_DIR = "/etc/ssl/private"
    CERT_FILE = "/etc/ssl/certs/server.crt"
    KEY_FILE = "/etc/ssl/private/server.key"

    def is_applicable(self) -> bool:
        """检查证书是否即将过期或已过期"""
        import subprocess
        for cert_path in [self.CERT_FILE, "/etc/nginx/ssl/server.crt"]:
            if not os.path.exists(cert_path):
                continue
            try:
                result = subprocess.run(
                    ["openssl", "x509", "-in", cert_path, "-noout", "-enddate"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    # 检查是否在 30 天内过期
                    date_str = result.stdout.strip().replace("notAfter=", "")
                    expire = datetime.strptime(date_str.strip(), "%b %d %H:%M:%S %Y %Z")
                    days_left = (expire - datetime.now()).days
                    if days_left < 30:
                        return True
            except Exception:
                pass
        return False

    def run(self) -> FixResult:
        commands_run = []
        cert_path = None

        # 找到证书文件
        for path in [self.CERT_FILE, "/etc/nginx/ssl/server.crt"]:
            if os.path.exists(path):
                cert_path = path
                break

        if not cert_path:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message="未找到 SSL 证书文件",
                commands_run=commands_run,
            )

        # 备份
        backup = cert_path + ".bak.nastool"
        ok_backup, _ = self._run_command(f"cp {cert_path} {backup}")
        commands_run.append(f"cp {cert_path} {backup}")

        # 生成新证书（365 天有效期）
        ok_gen, out_gen = self._run_command(
            f"openssl req -x509 -nodes -days 365 -newkey rsa:2048 "
            f"-keyout {self.KEY_FILE} -out {cert_path} "
            f"-subj '/CN=localhost/O=AI-NAS/C=CN'",
            timeout=30,
        )
        commands_run.append("openssl req -x509 -nodes -days 365 ...")

        if not ok_gen:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"证书生成失败: {out_gen[:200]}",
                commands_run=commands_run,
                rollback_command=f"mv {backup} {cert_path}",
            )

        # 设置权限
        self._run_command(f"chmod 600 {self.KEY_FILE}")
        self._run_command(f"chmod 644 {cert_path}")
        commands_run.append("chmod ...")

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message="SSL 证书已续期（365 天有效期）。重启相关服务以应用新证书。",
            commands_run=commands_run,
            changed_files=[cert_path, self.KEY_FILE, backup],
            rollback_command=f"mv {backup} {cert_path}",
        )
