"""
checks/network.py — 网络

判定口径按 NAS 常识，而不是按"能不能上网"：

  · 有网卡拿到有效 IP         → 基本可用（链路本地 169.254 不算）
  · 网关不可达                → 视情况（隔离内网完全正常）
  · 外网不可达                → 只在内网已通时才算问题
  · 无线作为主链路            → 对 NAS 是真实隐患
  · 网卡错误计数              → 线缆/网口/驱动问题的直接证据
"""
from __future__ import annotations

from ..collect.util import read_file
from ..model import Status
from ..registry import check
from ._base import R, ev


def _usable(ctx):
    return [i for i in ctx.network.interfaces if i.up and i.has_usable_ip()]


def _wired_up(ctx):
    return [i for i in ctx.network.interfaces if i.up and not i.is_wireless]


@check("network.interface_present", "网络接口", "network", weight=3,
       platforms=["any"], tags=["nas", "verify"])
def interface_present(ctx):
    n = ctx.network
    if not n.interfaces:
        return R(Status.FAIL, "未发现任何网络接口",
                 detail="网卡驱动缺失、容器无网络命名空间，或采集工具（ip/ifconfig）不可用",
                 suggestion="确认系统能识别网卡：ip link / lspci | grep -i ethernet")
    up = [i for i in n.interfaces if i.up]
    evidence = [ev("ip addr", i.name, i.ip or "(无 IP)",
                   note="UP" if i.up else "DOWN")
                for i in n.interfaces[:10]]
    if not up:
        return R(Status.FAIL, f"{len(n.interfaces)} 个网卡全部处于 DOWN 状态",
                 suggestion="检查网线与交换机端口；确认网卡未被禁用",
                 evidence=evidence)
    return R(Status.PASS, f"{len(up)}/{len(n.interfaces)} 个网卡已启用",
             evidence=evidence, confidence=0.9)


@check("network.ip_assigned", "IP 地址", "network", weight=5,
       platforms=["any"], tags=["nas", "verify"])
def ip_assigned(ctx):
    n = ctx.network
    usable = _usable(ctx)
    evidence = [ev("ip addr", i.name, i.ip or "(无)",
                   note="链路本地" if i.ip.startswith("169.254.") else "")
                for i in n.interfaces if i.ip or i.up]

    if usable:
        return R(Status.PASS, f"有效 IP：{usable[0].ip}"
                 + (f" 等 {len(usable)} 个" if len(usable) > 1 else ""),
                 evidence=evidence, confidence=0.95)

    link_local = [i for i in n.interfaces if i.ip.startswith("169.254.")]
    if link_local:
        return R(Status.WARN,
                 f"{link_local[0].name} 只拿到链路本地地址（169.254.x.x）",
                 detail="链路本地地址说明 DHCP 没成功，实际无法与局域网其他设备通信",
                 suggestion="检查网线、交换机端口、DHCP 服务；或改为固定 IP",
                 evidence=evidence)
    return R(Status.FAIL, "没有任何网卡获取到 IP",
             suggestion="配置 DHCP 或静态 IP", evidence=evidence)


@check("network.link_speed", "链路速率", "network", weight=3,
       platforms=["linux"], tags=["nas", "verify"])
def link_speed(ctx):
    wired = _wired_up(ctx)
    if not wired:
        return R(Status.SKIP, "没有已启用的有线网卡",
                 detail="只有无线或虚拟网卡时不适用")

    known = [i for i in wired if i.speed_mbps > 0]
    if not known:
        return R(Status.UNKNOWN, "无法读取链路速率",
                 detail="/sys/class/net/*/speed 不可读（虚拟网卡常见）")

    worst = min(known, key=lambda i: i.speed_mbps)
    evidence = [ev(f"/sys/class/net/{i.name}/speed", "speed_mbps",
                   i.speed_mbps, num=i.speed_mbps) for i in known]

    if worst.speed_mbps < 100:
        return R(Status.WARN, f"{worst.name} 链路仅 {worst.speed_mbps} Mbps",
                 detail="百兆以下常见于网线只通了 4 芯、水晶头氧化、或走了 USB 网卡",
                 suggestion="更换超五类以上网线，检查交换机端口协商速率",
                 evidence=evidence)
    if worst.speed_mbps < 1000:
        return R(Status.WARN, f"{worst.name} 链路 {worst.speed_mbps} Mbps（非千兆）",
                 detail="NAS 的主要瓶颈通常就在链路上，千兆是基本盘",
                 suggestion="确认网线规格（Cat5e+）与交换机端口", evidence=evidence)
    return R(Status.PASS, f"链路速率 {worst.speed_mbps} Mbps"
             + ("（2.5G+）" if worst.speed_mbps >= 2500 else "（千兆）"),
             evidence=evidence, confidence=0.95)


@check("network.duplex", "双工模式", "network", weight=2,
       platforms=["linux"], tags=["nas"])
def duplex(ctx):
    wired = _wired_up(ctx)
    if not wired:
        return R(Status.SKIP, "没有已启用的有线网卡")

    half = [i for i in wired if i.duplex == "half"]
    unknown = all(not i.duplex for i in wired)
    evidence = [ev(f"/sys/class/net/{i.name}/duplex", "duplex", i.duplex or "未知")
                for i in wired]

    if half:
        return R(Status.WARN, f"{half[0].name} 处于半双工模式",
                 detail="半双工通常是协商失败的结果，会出现大量冲突与丢包",
                 suggestion="固定速率与双工为 1000full，或更换网线/交换机端口",
                 evidence=evidence)
    if unknown:
        return R(Status.UNKNOWN, "无法读取双工模式")
    return R(Status.PASS, "全双工", evidence=evidence, confidence=0.9)


@check("network.gateway", "默认网关", "network", weight=2,
       platforms=["any"], tags=["nas"])
def gateway(ctx):
    n = ctx.network
    if not n.gateway:
        return R(Status.SKIP, "未配置默认网关",
                 detail="隔离内网 / 纯二层存储网络属于正常配置")
    evidence = [ev("路由表", "gateway", n.gateway),
                ev("ping", "gateway_reachable", n.gateway_reachable)]
    if not n.gateway_reachable:
        return R(Status.WARN, f"网关 {n.gateway} 不可达",
                 detail="内网直连场景可忽略；但如果需要跨网段访问就会不通",
                 suggestion="检查网关设备、VLAN 配置与本机路由", evidence=evidence,
                 confidence=0.85)
    return R(Status.PASS, f"网关 {n.gateway} 可达", evidence=evidence, confidence=0.9)


@check("network.dns", "DNS 解析", "network", weight=2,
       platforms=["any"], tags=["nas"])
def dns(ctx):
    n = ctx.network
    if not n.gateway and not n.dns_server:
        return R(Status.SKIP, "无网关也无 DNS 配置",
                 detail="隔离内网属于正常情况")

    evidence = [ev("resolv.conf", "dns_server", n.dns_server or "(未配置)"),
                ev("解析测试", "dns_ok", n.dns_ok)]

    if n.dns_ok:
        return R(Status.PASS, f"DNS 正常{f'（{n.dns_server}）' if n.dns_server else ''}",
                 evidence=evidence, confidence=0.9)
    if not n.gateway_reachable:
        return R(Status.UNKNOWN, "DNS 解析失败，但网关本身不可达",
                 detail="先解决网关问题才能判断 DNS，因此本次不算 DNS 故障",
                 evidence=evidence)
    return R(Status.WARN, "DNS 解析失败",
             detail="会影响套件更新、证书校验、Docker 拉镜像、时间同步",
             suggestion="检查 /etc/resolv.conf 与上游 DNS 是否可达",
             evidence=evidence)


@check("network.internet", "外网连通", "network", weight=1,
       platforms=["any"], tags=["nas"])
def internet(ctx):
    n = ctx.network
    if not getattr(ctx.options, "do_internet_check", True):
        return R(Status.SKIP, "已跳过外网检查（--no-internet）")
    if not n.gateway_reachable:
        return R(Status.UNKNOWN, "网关不可达，无法判断外网",
                 detail="内网 NAS 不联外网是常见且合理的配置")
    if n.internet_reachable:
        return R(Status.PASS, "外网可达", confidence=0.9)
    return R(Status.WARN, "外网不可达",
             detail="内网 NAS 常见，若无需远程访问/更新套件可忽略",
             suggestion="确认是否需要远程访问或套件更新；否则可忽略此项",
             confidence=0.85)


@check("network.peer_reach", "对端可达性", "network", weight=2,
       platforms=["any"], tags=["nas"])
def peer_reach(ctx):
    n = ctx.network
    if not n.peers:
        return R(Status.SKIP, "未指定对端目标",
                 detail="用 --peer host:port 可以顺手验证备份服务器、客户端、管理后台是否可达")

    ok = [p for p in n.peers if p.reachable]
    bad = [p for p in n.peers if not p.reachable]
    evidence = [ev("TCP 连接", p.label, f"{p.rtt_ms} ms" if p.reachable else p.error,
                   num=p.rtt_ms if p.reachable else None)
                for p in n.peers]

    if bad:
        return R(Status.WARN, f"{len(bad)}/{len(n.peers)} 个对端不可达",
                 detail="; ".join(f"{p.label}: {p.error}" for p in bad),
                 suggestion="确认目标服务是否开启、防火墙是否放行",
                 evidence=evidence)
    return R(Status.PASS, f"{len(ok)} 个对端全部可达", evidence=evidence, confidence=0.95)


@check("network.wireless_primary", "主链路类型", "network", weight=3,
       platforms=["any"], tags=["nas", "verify"])
def wireless_primary(ctx):
    usable = _usable(ctx)
    if not usable:
        return R(Status.SKIP, "没有可用链路")
    wired = [i for i in usable if not i.is_wireless]
    wireless = [i for i in usable if i.is_wireless]
    evidence = [ev("ip addr", i.name, i.ip,
                   note="无线" if i.is_wireless else "有线") for i in usable]

    if wired:
        return R(Status.PASS, f"主链路为有线（{wired[0].name}）",
                 evidence=evidence, confidence=0.9)
    return R(Status.WARN, f"只有无线链路可用（{wireless[0].name}）",
             detail="NAS 走 WiFi 会出现带宽不稳、延迟抖动、断流，尤其在多客户端并发时",
             suggestion="条件允许时改用有线连接",
             evidence=evidence)


@check("network.interface_errors", "网卡错误计数", "network", weight=2,
       platforms=["linux"], tags=["nas"])
def interface_errors(ctx):
    names = [i.name for i in ctx.network.interfaces]
    if not names:
        return R(Status.UNKNOWN, "无网卡可检查")

    rows = []
    for name in names[:8]:
        base = f"/sys/class/net/{name}/statistics"
        try:
            rx = int(read_file(f"{base}/rx_errors", "0") or 0)
            tx = int(read_file(f"{base}/tx_errors", "0") or 0)
            drop = int(read_file(f"{base}/rx_dropped", "0") or 0)
        except ValueError:
            continue
        rows.append((name, rx, tx, drop))

    if not rows:
        return R(Status.UNKNOWN, "无法读取网卡统计")

    bad = [(n, rx + tx, drop) for n, rx, tx, drop in rows if rx + tx > 0]
    evidence = [ev(f"/sys/class/net/{n}/statistics", "errors", err,
                   num=err, trend="up_bad")
                for n, err, _ in rows]

    if bad:
        return R(Status.WARN,
                 "、".join(f"{n} 累计错误 {err}" for n, err, _ in bad[:3]),
                 detail="累计错误计数持续增长说明物理层有问题（网线、水晶头、网口氧化）",
                 suggestion="更换网线；观察该计数是否继续增长",
                 evidence=evidence)
    return R(Status.PASS, "网卡无累计错误", evidence=evidence, confidence=0.9)
