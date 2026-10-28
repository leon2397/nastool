"""
checks/security.py — 安全

这是原来完全缺失的一类，却是二手验机和真实运维里最容易被忽略的部分。
全部只读判断，不修改任何配置。

判定不搞"一刀切"：
  · PermitRootLogin prohibit-password 是现代发行版默认值，不算问题
  · 只有明确 yes 才算严重
  · 证书自签名在纯内网属于合理选择，因此只告警不建议强制更换
"""
from __future__ import annotations

from ..model import Status
from ..registry import check
from ._base import R, ev


@check("security.ssh_root_login", "SSH 允许 root 登录", "security", weight=4,
       platforms=["any"], requires=["ssh_config"], tags=["nas", "verify"])
def ssh_root_login(ctx):
    ssh = ctx.security.ssh
    value = (ssh.permit_root_login or "").strip().lower()
    evidence = [ev(ssh.config_paths[0] if ssh.config_paths else "sshd_config",
                   "PermitRootLogin", value or "(默认)")]

    if value in ("yes", "true"):
        return R(Status.FAIL, "SSH 允许 root 直接登录",
                 detail="root 账户名是公开已知的，允许直接登录等于把暴力破解的目标减半",
                 suggestion="改为 PermitRootLogin prohibit-password，日常用普通账号 + sudo",
                 evidence=evidence, confidence=0.95)
    if value in ("prohibit-password", "without-password", "forced-commands-only"):
        return R(Status.PASS, f"已限制为 {value}（禁止密码登录 root）",
                 evidence=evidence, confidence=0.95)
    if value == "no":
        return R(Status.PASS, "已禁止 root 登录", evidence=evidence, confidence=0.95)

    return R(Status.UNKNOWN, "配置中未显式声明 PermitRootLogin",
             detail="不同发行版默认值不同（多数现代发行版默认 prohibit-password，老版本默认 yes）",
             suggestion="显式写一行 PermitRootLogin prohibit-password 更稳妥",
             confidence=0.0)


@check("security.ssh_password_auth", "SSH 密码登录", "security", weight=3,
       platforms=["any"], requires=["ssh_config"], tags=["nas", "verify"])
def ssh_password_auth(ctx):
    ssh = ctx.security.ssh
    value = (ssh.password_auth or "").strip().lower()
    evidence = [ev(ssh.config_paths[0] if ssh.config_paths else "sshd_config",
                   "PasswordAuthentication", value or "(默认)")]

    if value in ("no", "false"):
        return R(Status.PASS, "已禁用密码登录（仅密钥）", evidence=evidence, confidence=0.95)
    if value in ("yes", "true"):
        # 已禁用 root 登录时风险低一些，但仍然会被持续爆破
        return R(Status.WARN, "SSH 允许密码登录",
                 detail="公网或大内网环境下会被持续暴力破解，日志里大量失败记录",
                 suggestion="改用密钥登录并关闭密码认证；或至少启用 fail2ban",
                 evidence=evidence, confidence=0.9)
    return R(Status.UNKNOWN, "配置中未显式声明 PasswordAuthentication",
             detail="默认值通常是 yes", confidence=0.0)


@check("security.firewall", "防火墙", "security", weight=4,
       platforms=["any"], tags=["nas", "verify"])
def firewall(ctx):
    fw = ctx.security.firewall
    evidence = [ev("防火墙", "detected", "、".join(fw.detected) or "(未检测到)"),
                ev("防火墙", "active", fw.active)]

    if fw.active is True:
        detail = f"{'、'.join(fw.detected)} 已启用"
        if fw.rule_count:
            detail += f"，{fw.rule_count} 条规则"
        return R(Status.PASS, detail, evidence=evidence, confidence=0.9)

    if fw.active is False:
        return R(Status.WARN, "检测到防火墙但未启用",
                 detail=fw.detail or "规则为空或被关闭",
                 suggestion="启用防火墙，只放行必要端口（SMB/NFS/管理界面）",
                 evidence=evidence, confidence=0.85)

    if not fw.detected:
        return R(Status.WARN, "未发现启用的防火墙",
                 detail="系统里没有任何防火墙工具，或全部未配置规则",
                 suggestion="至少启用 ufw / firewalld 并放行必要端口；路由器侧做 NAT 也能缓解",
                 evidence=evidence, confidence=0.8)

    return R(Status.UNKNOWN, "无法判定防火墙状态", evidence=evidence)


@check("security.tls_cert", "证书有效期", "security", weight=4,
       platforms=["any"], requires=["certs"], tags=["nas", "verify"])
def tls_cert(ctx):
    certs = [c for c in ctx.security.certs if c.days_left is not None]
    if not certs:
        return R(Status.UNKNOWN, "无法解析任何证书有效期",
                 detail="找到了证书文件但 openssl 解析失败，或证书受密码保护")

    certs.sort(key=lambda c: c.days_left)
    worst = certs[0]
    evidence = [ev(c.path, "days_left", c.days_left,
                   note=c.subject or "", num=c.days_left) for c in certs[:6]]

    if worst.days_left < 0:
        return R(Status.FAIL, f"证书已过期 {-worst.days_left} 天",
                 detail=f"{worst.path}（{worst.subject}）",
                 suggestion="续签并替换证书；过期会导致浏览器告警、API 调用失败",
                 evidence=evidence, confidence=1.0)
    if worst.days_left <= 7:
        return R(Status.FAIL, f"证书 {worst.days_left} 天后过期",
                 suggestion="立即续签，避免服务中断", evidence=evidence, confidence=1.0)
    if worst.days_left <= 30:
        return R(Status.WARN, f"证书 {worst.days_left} 天后过期",
                 suggestion="提前续签（Let's Encrypt 自动续期请检查定时任务是否正常）",
                 evidence=evidence, confidence=0.95)
    return R(Status.PASS, f"最近一张证书还有 {worst.days_left} 天有效期",
             evidence=evidence, confidence=0.95)


@check("security.self_signed", "证书类型", "security", weight=2,
       platforms=["any"], requires=["certs"], tags=["nas"])
def self_signed(ctx):
    certs = ctx.security.certs
    selfs = [c for c in certs if c.self_signed and not c.error]
    evidence = [ev(c.path, "self_signed", c.self_signed, note=c.subject)
                for c in certs[:6]]

    if not certs:
        return R(Status.SKIP, "未发现服务端证书")
    if selfs:
        return R(Status.WARN, f"{len(selfs)} 张自签名证书",
                 detail="内网使用自签名是常见做法，但会导致客户端告警、部分 API 拒绝连接",
                 suggestion="内网可为客户端导入该证书，或使用内部 CA 签发",
                 evidence=evidence, confidence=0.85)
    return R(Status.PASS, "证书由受信任机构签发", evidence=evidence, confidence=0.9)


@check("security.smb_guest", "SMB 匿名访问", "security", weight=3,
       platforms=["linux"], requires=["smb_config"], tags=["nas", "verify"])
def smb_guest(ctx):
    guest = ctx.security.smb_guest
    evidence = [ev("smb.conf", "guest_ok", guest),
                ev("smb.conf", "server_signing", ctx.security.smb_signing or "(默认)")]

    if guest:
        return R(Status.WARN, "SMB 允许匿名（guest）访问",
                 detail="任何人都能读取共享目录，勒索软件也会优先利用这类共享",
                 suggestion="在 smb.conf 中设置 guest ok = no，并为每个共享配置用户权限",
                 evidence=evidence, confidence=0.9)
    return R(Status.PASS, "SMB 未开启匿名访问", evidence=evidence, confidence=0.9)


@check("security.nfs_root_squash", "NFS 权限映射", "security", weight=3,
       platforms=["linux"], requires=["nfs_config"], tags=["nas", "verify"])
def nfs_root_squash(ctx):
    risky = ctx.security.nfs_no_root_squash
    evidence = [ev("/etc/exports", "no_root_squash", risky)]
    if risky:
        return R(Status.WARN, "NFS 导出使用了 no_root_squash",
                 detail="客户端 root 会保留为服务端 root，等于把整机控制权交给能挂载该目录的主机",
                 suggestion="改用 root_squash（默认），仅在确有需要时对特定主机放开",
                 evidence=evidence, confidence=0.9)
    return R(Status.PASS, "NFS 未放开 root_squash", evidence=evidence, confidence=0.85)


@check("security.fail2ban", "暴力破解防护", "security", weight=1,
       platforms=["linux"], tags=["nas"])
def fail2ban(ctx):
    active = ctx.security.fail2ban
    if active is None:
        return R(Status.SKIP, "未检测到 fail2ban",
                 detail="可用 systemd / 容器方案替代，不算缺陷")
    if active:
        return R(Status.PASS, "fail2ban 运行中", confidence=0.9)
    return R(Status.WARN, "fail2ban 已安装但未运行",
             suggestion="启动并设为开机自启；它会封禁反复尝试登录的来源 IP",
             confidence=0.85)
