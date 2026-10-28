"""
checks/services.py — 服务与端口

原则：**服务缺失不算故障。**
一台只跑 SMB 的裸 NAS 完全正常，不能因为没装 Plex 就扣分。
所以只有两类情况会真正扣分：
  · 高风险服务对外暴露（Telnet、未加密 Docker API）
  · 敏感端口绑定在所有地址上
其余都是信息项。
"""
from __future__ import annotations

from ..model import Status
from ..registry import check
from ._base import R, ev

# 一旦对外暴露就等于高风险的服务
_HIGH_RISK = {
    23: ("Telnet", "明文传输，凭据可被直接抓包"),
    2375: ("Docker API (未加密)", "可直接创建特权容器，等同于交出 root"),
    21: ("FTP", "明文传输；建议改用 SFTP"),
}

# 敏感端口：绑定 0.0.0.0 就需要注意
_SENSITIVE_BIND = {445: "SMB", 2049: "NFS", 3306: "MySQL", 6379: "Redis",
                   5432: "PostgreSQL", 27017: "MongoDB"}


def _items(ctx):
    return ctx.services.items


@check("services.port_inventory", "端口清单", "services", weight=1,
       platforms=["any"], tags=["nas", "verify"])
def port_inventory(ctx):
    s = ctx.services
    if not s.total_listening:
        return R(Status.UNKNOWN, "未读取到监听端口",
                 detail="ss / netstat 均不可用，或需要更高权限",
                 suggestion="确认 iproute2 已安装")
    return R(Status.PASS,
             f"{s.total_listening} 个监听端口，识别出 {len(s.items)} 个已知服务",
             detail=(f"另有 {s.ephemeral_ports} 个临时端口（49152+），多为客户端出站连接"
                     if s.ephemeral_ports else ""),
             evidence=[ev("ss -tlnp", "total_listening", s.total_listening,
                          num=s.total_listening)],
             confidence=0.9)


@check("services.file_sharing", "文件共享服务", "services", weight=3,
       platforms=["any"], tags=["nas"])
def file_sharing(ctx):
    items = [i for i in _items(ctx) if i.category == "文件共享"]
    if items:
        names = sorted({i.name for i in items})
        return R(Status.PASS, "、".join(names),
                 evidence=[ev("监听端口", f"{i.name}", f"{i.port}") for i in items[:6]],
                 confidence=0.95)

    # 没有端口不代表没开：可能只监听了内网地址，或本轮没权限读端口
    if not ctx.services.total_listening:
        return R(Status.UNKNOWN, "无法确认文件共享服务（端口列表不可用）")
    return R(Status.WARN, "未检测到 SMB / NFS 等文件共享服务",
             detail="NAS 的核心职能是文件共享，没有共享服务通常意味着尚未配置",
             suggestion="如需共享请在系统里开启 SMB/NFS；仅作本地存储可忽略",
             confidence=0.85)


@check("services.risky_ports", "高风险服务", "services", weight=4,
       platforms=["any"], tags=["nas", "verify"])
def risky_ports(ctx):
    found = [(i, _HIGH_RISK[i.port]) for i in _items(ctx) if i.port in _HIGH_RISK]
    if not found:
        return R(Status.PASS, "未发现明文/高危服务在监听", confidence=0.9)

    evidence = [ev("监听端口", f"{name}({i.port})", i.bind_address or "unknown",
                   note=reason) for i, (name, reason) in found]

    docker_api = [x for x in found if x[0].port == 2375]
    if docker_api:
        i, (name, reason) = docker_api[0]
        return R(Status.FAIL, f"{name} 正在监听（{i.port}）",
                 detail=reason,
                 suggestion="立即关闭 2375，改用 2376（TLS）或只走本地 socket",
                 evidence=evidence, confidence=1.0)

    names = "、".join(f"{name}({i.port})" for i, (name, _) in found)
    return R(Status.WARN, f"存在明文服务：{names}",
             detail="; ".join(reason for _, (_, reason) in found),
             suggestion="关闭不用的明文服务；必须使用时限制来源 IP",
             evidence=evidence)


@check("services.exposed_bind", "端口暴露范围", "services", weight=3,
       platforms=["any"], tags=["nas", "verify"])
def exposed_bind(ctx):
    exposed = [i for i in _items(ctx)
               if i.port in _SENSITIVE_BIND
               and i.bind_address in ("0.0.0.0", "*", "::", "[::]", "")]
    if not exposed:
        return R(Status.PASS, "敏感端口未监听在所有地址上", confidence=0.85)

    evidence = [ev("绑定地址", f"{_SENSITIVE_BIND[i.port]}({i.port})",
                   i.bind_address or "(未知)") for i in exposed]
    return R(Status.WARN,
             "、".join(f"{_SENSITIVE_BIND[i.port]}({i.port})" for i in exposed)
             + " 监听所有地址",
             detail="这些服务本身有认证，但对外暴露会放大暴力破解与漏洞利用面",
             suggestion="在防火墙限制来源网段，或改为只绑定内网地址",
             evidence=evidence)


@check("services.docker", "容器运行时", "services", weight=2,
       platforms=["any"], tags=["nas"])
def docker(ctx):
    s = ctx.services
    if not s.docker_available:
        return R(Status.SKIP, "未检测到 Docker",
                 detail="没有安装、未启动，或当前用户无权限访问 docker")
    running = len([c for c in s.containers if "Up" in c.status or "running" in c.status.lower()])
    stopped = len(s.containers) - running
    evidence = [ev("docker ps", c.name, c.status, note=c.image)
                for c in s.containers[:12]]
    summary = f"{running} 个容器运行中"
    if stopped:
        summary += f"，{stopped} 个已停止"
    return R(Status.PASS, summary, evidence=evidence, confidence=0.9)


@check("services.web_ui", "管理界面", "services", weight=1,
       platforms=["any"], tags=["nas"])
def web_ui(ctx):
    items = [i for i in _items(ctx) if i.category == "管理界面"]
    if not items:
        return R(Status.SKIP, "未检测到 Web 管理界面")
    return R(Status.PASS, "、".join(sorted({f"{i.name}({i.port})" for i in items})[:4]),
             evidence=[ev("监听端口", i.name, i.port) for i in items[:6]])


@check("services.media_stack", "媒体服务", "services", weight=1,
       platforms=["any"], tags=["nas"])
def media_stack(ctx):
    items = [i for i in _items(ctx) if i.category in ("媒体服务", "下载")]
    if not items:
        return R(Status.SKIP, "未检测到媒体/下载服务",
                 detail="纯文件存储用途无需此项")
    names = sorted({i.name for i in items})
    return R(Status.PASS, "、".join(names),
             evidence=[ev("监听端口", i.name, i.port) for i in items[:8]])


@check("services.unknown_services", "未识别端口", "services", weight=1,
       platforms=["any"], tags=["verify"])
def unknown_services(ctx):
    unknown = [i for i in _items(ctx) if i.category == "其他"]
    if not unknown:
        return R(Status.PASS, "所有监听端口均已识别", confidence=0.9)
    evidence = [ev("监听端口", str(i.port), i.process or "(未知进程)")
                for i in unknown[:12]]
    if len(unknown) >= 10:
        return R(Status.WARN, f"{len(unknown)} 个端口无法识别对应服务",
                 detail="端口数量偏多，可能是自建服务、恶意程序，或端口映射残留",
                 suggestion="用 ss -tlnp 逐个确认进程来源",
                 evidence=evidence)
    return R(Status.PASS, f"{len(unknown)} 个端口未识别（多为自建服务）",
             evidence=evidence, confidence=0.8)
