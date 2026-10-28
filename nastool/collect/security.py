"""
nastool/collect/security.py — 安全面事实采集

NAS 最容易被忽略、也最容易被"验机"发现的一类问题。全部只读：
  - SSH 配置（是否允许 root 登录、是否允许密码登录）
  - 防火墙状态（ufw / firewalld / nftables / iptables / Windows 防火墙）
  - TLS 证书（有效期、是否自签名、签发者）
  - 匿名 / 免密访问（SMB guest、NFS no_root_squash、FTP anonymous）
  - 基础加固项（fail2ban、IP 转发）

不做任何判定，也不修改任何配置。判定交给 checks/security.py。
"""
from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .util import IS_LINUX, IS_WINDOWS, have, read_file, run, run_ps

# 常见 NAS / Linux 的服务端证书位置（不含系统 CA 库，避免扫出几千条）
_CERT_DIRS = [
    "/etc/letsencrypt/live",
    "/usr/syno/etc/certificate",
    "/etc/nginx/ssl",
    "/etc/nginx/certs",
    "/etc/ssl/private",
    "/etc/casaos/certs",
    "/etc/pve",
    "/etc/stunnel",
    "/etc/apache2/ssl",
    "/etc/httpd/ssl",
    "/etc/openmediavault",
    "/volume1/@appstore",
]

_CERT_EXTS = (".pem", ".crt", ".cer")


@dataclass
class SshFacts:
    found: bool = False
    config_paths: List[str] = field(default_factory=list)
    permit_root_login: str = ""      # yes / no / prohibit-password / forced-commands-only
    password_auth: str = ""          # yes / no
    pubkey_auth: str = ""            # yes / no
    port: int = 22
    running: bool = False


@dataclass
class FirewallFacts:
    detected: List[str] = field(default_factory=list)   # ufw / firewalld / nftables / iptables ...
    active: Optional[bool] = None                        # None = 无法判定
    rule_count: int = 0
    detail: str = ""


@dataclass
class CertFacts:
    path: str = ""
    subject: str = ""
    issuer: str = ""
    not_after: str = ""
    days_left: Optional[int] = None
    self_signed: bool = False
    error: str = ""


@dataclass
class SecurityFacts:
    ssh: SshFacts = field(default_factory=SshFacts)
    firewall: FirewallFacts = field(default_factory=FirewallFacts)
    certs: List[CertFacts] = field(default_factory=list)
    smb_guest: Optional[bool] = None        # SMB 是否允许 guest
    smb_signing: str = ""                   # auto / mandatory / disabled / ""
    nfs_no_root_squash: Optional[bool] = None
    ftp_anonymous: Optional[bool] = None
    fail2ban: Optional[bool] = None
    ip_forward: Optional[bool] = None
    collect_errors: List[str] = field(default_factory=list)


# ── SSH ─────────────────────────────────────────────────────
_SSH_KEYS = {
    "permitrootlogin": "permit_root_login",
    "passwordauthentication": "password_auth",
    "pubkeyauthentication": "pubkey_auth",
    "port": "port",
}


def _parse_sshd(files: List[str]) -> dict:
    """
    按 sshd 语义解析：后出现的同名字段覆盖前面的（sshd 是"最后匹配生效"）。
    只取全局段，遇到 Match 块就停止（Match 内的值只对特定用户生效）。
    """
    values: Dict[str, str] = {}
    for path in files:
        for line in read_file(path).splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if re.match(r"(?i)^match\b", s):
                break
            parts = s.split(None, 1)
            if len(parts) != 2:
                continue
            key = parts[0].lower()
            if key in _SSH_KEYS:
                values[_SSH_KEYS[key]] = parts[1].strip().strip('"')
    return values


def _collect_ssh() -> SshFacts:
    facts = SshFacts()
    if IS_WINDOWS:
        # Windows 的 OpenSSH 服务端同一套配置格式
        candidates = [r"C:\ProgramData\ssh\sshd_config"]
    else:
        candidates = ["/etc/ssh/sshd_config"]

    existing = [p for p in candidates if os.path.isfile(p)]
    if not existing:
        return facts

    facts.found = True
    facts.config_paths = list(existing)

    files = list(existing)
    if not IS_WINDOWS:
        files.extend(sorted(glob.glob("/etc/ssh/sshd_config.d/*.conf")))
        files = [p for p in files if os.path.isfile(p)]

    values = _parse_sshd(files)
    facts.permit_root_login = values.get("permit_root_login", "")
    facts.password_auth = values.get("password_auth", "")
    facts.pubkey_auth = values.get("pubkey_auth", "")
    try:
        facts.port = int(values.get("port", "22"))
    except ValueError:
        facts.port = 22

    if IS_LINUX:
        out = run("systemctl is-active ssh sshd 2>/dev/null | sort -u", timeout=8)
        facts.running = "active" in out
    else:
        facts.running = True   # Windows 上不做服务查询，交给端口检测兜底
    return facts


# ── 防火墙 ──────────────────────────────────────────────────
def _collect_firewall() -> FirewallFacts:
    facts = FirewallFacts()

    if IS_WINDOWS:
        out = run_ps("Get-NetFirewallProfile | Select-Object Name,Enabled | "
                     "ConvertTo-Csv -NoTypeInformation", timeout=25)
        # CSV 形如 "Domain","True"（带引号），不能直接匹配 ",True"
        enabled = [ln for ln in out.splitlines()[1:]
                   if '"True"' in ln or ",True" in ln]
        facts.detected = ["Windows 防火墙"]
        facts.active = bool(enabled)
        facts.detail = f"{len(enabled)} 个配置档已启用" if enabled else "所有配置档均未启用"
        return facts

    if have("ufw"):
        out = run("ufw status 2>/dev/null | head -1", timeout=8).lower()
        if out:
            facts.detected.append("ufw")
            if "active" in out:
                facts.active = True
                rules = run("ufw status numbered 2>/dev/null | grep -c '\\['", timeout=8)
                try:
                    facts.rule_count = int(rules.strip() or 0)
                except ValueError:
                    pass
            elif "inactive" in out:
                facts.active = False
            facts.detail = out.strip()

    if have("firewall-cmd"):
        state = run("firewall-cmd --state 2>/dev/null", timeout=8).strip().lower()
        if state:
            facts.detected.append("firewalld")
            if state == "running":
                facts.active = True
                facts.detail = "firewalld 运行中"
            elif facts.active is None:
                facts.active = False
                facts.detail = "firewalld 未运行"

    if have("nft"):
        out = run("nft list ruleset 2>/dev/null | head -40", timeout=8)
        if out.strip():
            facts.detected.append("nftables")
            rules = len([ln for ln in out.splitlines() if ln.strip()])
            facts.rule_count = max(facts.rule_count, rules)
            if facts.active is None:
                facts.active = rules > 0

    if have("iptables"):
        out = run("iptables -S 2>/dev/null | head -40", timeout=8)
        if out.strip():
            rules = [ln for ln in out.splitlines() if ln.startswith("-A")]
            # 只有默认策略（无 -A 规则）时视为"未配置"
            if rules:
                facts.detected.append("iptables")
                facts.rule_count = max(facts.rule_count, len(rules))
                if facts.active is None:
                    facts.active = True

    if not facts.detected:
        facts.detected = []
        facts.active = None
        facts.detail = "未发现已安装的防火墙工具"
    return facts


# ── 证书 ────────────────────────────────────────────────────
def _openssl_cert(path: str) -> CertFacts:
    cert = CertFacts(path=path)
    if not have("openssl"):
        cert.error = "未安装 openssl，无法解析证书"
        return cert
    out = run(f'openssl x509 -in "{path}" -noout -subject -issuer -enddate 2>/dev/null',
              timeout=10)
    if not out:
        cert.error = "无法解析（可能不是 PEM 证书或需要密码）"
        return cert
    for line in out.splitlines():
        low = line.lower()
        if low.startswith("subject"):
            cert.subject = line.split("=", 1)[-1].strip()
        elif low.startswith("issuer"):
            cert.issuer = line.split("=", 1)[-1].strip()
        elif low.startswith("notafter"):
            cert.not_after = line.split("=", 1)[-1].strip()

    cert.self_signed = bool(cert.subject) and cert.subject == cert.issuer

    if cert.not_after:
        try:
            import datetime
            # 形如 Mar  1 12:00:00 2027 GMT
            dt = datetime.datetime.strptime(cert.not_after.replace(" GMT", ""),
                                            "%b %d %H:%M:%S %Y")
            cert.days_left = (dt - datetime.datetime.utcnow()).days
        except ValueError:
            cert.days_left = None
    return cert


def _collect_certs() -> List[CertFacts]:
    if IS_WINDOWS:
        return []
    paths: List[str] = []
    for d in _CERT_DIRS:
        if not os.path.isdir(d):
            continue
        for ext in _CERT_EXTS:
            paths.extend(glob.glob(os.path.join(d, "*" + ext)))
            paths.extend(glob.glob(os.path.join(d, "*", "fullchain" + ext)))
            paths.extend(glob.glob(os.path.join(d, "*", "cert" + ext)))
    # 去重 + 限制数量（避免在 appstore 这类大目录里扫出海量文件）
    seen, uniq = set(), []
    for p in paths:
        if p in seen or not os.path.isfile(p):
            continue
        seen.add(p)
        uniq.append(p)
        if len(uniq) >= 8:
            break
    return [_openssl_cert(p) for p in uniq]


# ── 匿名访问 ────────────────────────────────────────────────
def _collect_smb() -> tuple:
    """返回 (smb_guest, smb_signing)"""
    conf = "/etc/samba/smb.conf"
    if not os.path.isfile(conf):
        return None, ""
    guest = None
    signing = ""
    for line in read_file(conf).splitlines():
        s = line.strip().lower()
        if s.startswith("guest ok") or s.startswith("public"):
            if s.endswith("yes") or s.endswith("true"):
                guest = True
        elif s.startswith("map to guest"):
            if "bad user" in s or s.endswith("yes"):
                guest = True
            elif "never" in s:
                guest = guest if guest is not None else False
        elif s.startswith("server signing"):
            signing = s.split("=", 1)[-1].strip()
    return guest, signing


def _collect_nfs() -> Optional[bool]:
    exports = "/etc/exports"
    if not os.path.isfile(exports):
        return None
    for line in read_file(exports).splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "no_root_squash" in s or "insecure" in s:
            return True
    return False


def _collect_fail2ban() -> Optional[bool]:
    """True=运行中 / False=已配置但未运行 / None=未安装（不适用）"""
    if IS_WINDOWS or not IS_LINUX:
        return None
    out = run("systemctl is-active fail2ban 2>/dev/null", timeout=8).strip()
    if out in ("active", "inactive", "failed"):
        return out == "active"
    # 没有 systemd 的环境退回进程检测
    out = run("ps -eo comm= 2>/dev/null | grep -c fail2ban", timeout=8).strip()
    if out.isdigit() and int(out) > 0:
        return True
    return None


def _collect_ip_forward() -> Optional[bool]:
    if not IS_LINUX:
        return None
    val = read_file("/proc/sys/net/ipv4/ip_forward", "")
    if val in ("0", "1"):
        return val == "1"
    return None


def collect_security() -> SecurityFacts:
    """主入口：全部只读，任何子项失败都不影响其他项。"""
    facts = SecurityFacts()

    for name, fn, attr in (
        ("SSH", _collect_ssh, "ssh"),
        ("防火墙", _collect_firewall, "firewall"),
        ("证书", _collect_certs, "certs"),
        ("fail2ban", _collect_fail2ban, "fail2ban"),
        ("IP转发", _collect_ip_forward, "ip_forward"),
    ):
        try:
            setattr(facts, attr, fn())
        except Exception as e:  # noqa: BLE001
            facts.collect_errors.append(f"{name}: {e}")

    try:
        facts.smb_guest, facts.smb_signing = _collect_smb()
    except Exception as e:  # noqa: BLE001
        facts.collect_errors.append(f"SMB: {e}")

    try:
        facts.nfs_no_root_squash = _collect_nfs()
    except Exception as e:  # noqa: BLE001
        facts.collect_errors.append(f"NFS: {e}")

    return facts
