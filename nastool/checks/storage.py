"""
checks/storage.py — 存储

NAS 最核心的一类。这里把「容量 / 权限 / 阵列 / 硬盘健康 / 性能」拆成独立检查项，
每一类都有独立的置信度和证据，方便历史对比时精确到某一项。

特别处理「读不到」：
  没有 smartctl、不是 root、盘在硬件 RAID 卡后面、USB 桥接盘……
  这些情况一律 UNKNOWN，绝不写成「健康」。
"""
from __future__ import annotations

from ..collect.util import IS_LINUX
from ..model import Status
from ..registry import check
from ._base import R, ev


def _target_disk(storage):
    """找出目标路径所在的挂载点（取最长匹配）。"""
    best = None
    best_len = -1
    for d in storage.disks:
        mp = d.mountpoint.rstrip("/") or "/"
        if storage.target_path.startswith(mp) and len(mp) > best_len:
            best, best_len = d, len(mp)
    return best


@check("storage.path_exists", "数据路径存在", "storage", weight=5,
       platforms=["any"], tags=["nas", "verify"])
def path_exists(ctx):
    s = ctx.storage
    evidence = [ev("os.path.exists", "target_path", s.target_path)]
    if not s.target_exists:
        return R(Status.FAIL, f"数据路径不存在：{s.target_path}",
                 detail="挂载点掉了 / 网盘未挂载 / 路径写错，都会导致这项失败",
                 suggestion="确认挂载状态（df -h）与路径拼写；NAS 重启后阵列未自动挂载常见",
                 evidence=evidence, confidence=1.0)
    if not s.is_dir:
        return R(Status.FAIL, f"数据路径不是目录：{s.target_path}",
                 suggestion="--storage-path 应指向目录而不是文件",
                 evidence=evidence, confidence=1.0)
    return R(Status.PASS, f"路径可用：{s.target_path}", evidence=evidence, confidence=1.0)


@check("storage.writable", "数据路径可写", "storage", weight=5,
       platforms=["any"], tags=["nas", "verify"])
def writable(ctx):
    s = ctx.storage
    if not s.target_exists or not s.is_dir:
        return R(Status.SKIP, "路径不可用，跳过可写性检测")

    evidence = [ev("写入探针", "can_write", s.can_write)]
    if not s.can_write:
        return R(Status.FAIL, "数据路径不可写",
                 detail="权限不足、只读挂载，或文件系统已转为只读（常见于磁盘错误后自动保护）",
                 suggestion="检查目录权限；若为只读挂载，先看 dmesg 是否有文件系统错误",
                 evidence=evidence)
    return R(Status.PASS, "写入正常", evidence=evidence, confidence=0.95)


@check("storage.capacity", "数据盘容量", "storage", weight=4,
       platforms=["any"], tags=["nas", "verify"])
def capacity(ctx):
    s = ctx.storage
    if s.target_total_gb <= 0:
        return R(Status.UNKNOWN, "无法读取容量")

    warn = ctx.threshold("disk_use_warn", 80.0)
    crit = ctx.threshold("disk_use_crit", 90.0)
    pct = s.target_use_percent

    evidence = [
        ev("shutil.disk_usage", "use_percent", pct, num=pct, trend="up_bad"),
        ev("shutil.disk_usage", "free_gb", s.target_free_gb,
           num=s.target_free_gb, trend="up_good"),
        ev("shutil.disk_usage", "total_gb", s.target_total_gb, num=s.target_total_gb),
    ]

    if pct >= crit:
        return R(Status.FAIL, f"已用 {pct}%，剩余 {s.target_free_gb} GB，即将写满",
                 suggestion="立即清理或扩容；写满会导致应用异常、快照失效",
                 evidence=evidence)
    if pct >= warn:
        return R(Status.WARN, f"已用 {pct}%，剩余 {s.target_free_gb} GB",
                 suggestion="规划清理或扩容", evidence=evidence)
    return R(Status.PASS, f"已用 {pct}%，剩余 {s.target_free_gb} GB",
             evidence=evidence, confidence=1.0)


@check("storage.inode", "inode 使用率", "storage", weight=2,
       platforms=["linux"], tags=["nas"])
def inode(ctx):
    s = ctx.storage
    if not s.disks:
        return R(Status.UNKNOWN, "无法读取挂载信息")
    worst = max(s.disks, key=lambda d: d.inodes_use_percent)
    if worst.inodes_use_percent <= 0:
        return R(Status.SKIP, "该文件系统不提供 inode 统计",
                 detail="btrfs / ZFS 等动态 inode 文件系统通常不报 inode 使用率")

    warn = ctx.threshold("inode_use_warn", 90.0)
    evidence = [ev("df -iP", worst.mountpoint,
                   f"{worst.inodes_use_percent}%", num=worst.inodes_use_percent)]

    if worst.inodes_use_percent >= warn:
        return R(Status.WARN,
                 f"{worst.mountpoint} inode 已用 {worst.inodes_use_percent}%（空间可能还很充足）",
                 detail="inode 耗尽后同样无法创建新文件，但 df 显示空间足够，很容易误判",
                 suggestion="排查小文件过多的目录（日志、缓存、缩略图、邮件队列）",
                 evidence=evidence)
    return R(Status.PASS, f"inode 最高使用 {worst.inodes_use_percent}%",
             evidence=evidence)


@check("storage.readonly_mount", "挂载只读", "storage", weight=4,
       platforms=["linux"], tags=["nas", "verify"])
def readonly_mount(ctx):
    s = ctx.storage
    target = _target_disk(s)
    if not s.disks:
        return R(Status.UNKNOWN, "无法读取挂载状态")

    interesting = [d for d in s.disks
                   if d.readonly and d.fstype not in ("squashfs", "iso9660", "erofs")]
    evidence = [ev("/proc/mounts", d.mountpoint, "ro", num=1) for d in interesting]

    if target is not None and target.readonly:
        return R(Status.FAIL, f"数据盘 {target.mountpoint} 为只读挂载",
                 detail="文件系统检出错误后内核会自动转为只读，这是数据受损的强信号",
                 suggestion="立即备份数据，检查 dmesg 与文件系统一致性（btrfs scrub / fsck）",
                 evidence=evidence)
    if interesting:
        return R(Status.WARN,
                 f"{len(interesting)} 个文件系统为只读挂载（{', '.join(d.mountpoint for d in interesting[:3])}）",
                 suggestion="确认其中是否有本该可写的数据盘", evidence=evidence)
    return R(Status.PASS, "数据盘为可写挂载", confidence=0.9)


@check("storage.physical_disks", "物理磁盘识别", "storage", weight=2,
       platforms=["linux"], tags=["nas", "verify"])
def physical_disks(ctx):
    s = ctx.storage
    if not s.physical_disks:
        if ctx.platform.in_container:
            return R(Status.UNKNOWN, "未识别到物理磁盘（运行在容器内）",
                     detail="容器看不到宿主机块设备，SMART / 阵列检测均无法进行",
                     suggestion="如需完整检测，请在宿主机上直接运行")
        return R(Status.UNKNOWN, "未识别到物理磁盘",
                 detail="可能运行在虚拟机中，或 lsblk 不可用",
                 suggestion="确认是否为虚拟化环境")
    total = round(sum(d.size_gb for d in s.physical_disks), 1)
    kinds = []
    if any(d.rotational is True for d in s.physical_disks):
        kinds.append("HDD")
    if any(d.rotational is False for d in s.physical_disks):
        kinds.append("SSD")
    return R(Status.PASS,
             f"识别到 {len(s.physical_disks)} 块物理盘，合计 {total} GB"
             + (f"（{'/'.join(kinds)}）" if kinds else ""),
             evidence=[ev("lsblk", d.name, f"{d.size_gb} GB {d.model or ''}".strip(),
                          num=d.size_gb) for d in s.physical_disks[:12]],
             confidence=0.9)


@check("storage.raid_state", "阵列健康", "storage", weight=5,
       platforms=["linux"], tags=["nas", "verify"])
def raid_state(ctx):
    s = ctx.storage
    if not s.raids:
        return R(Status.SKIP, "未检测到软阵列",
                 detail="单盘使用、或使用硬件 RAID 卡（需厂商工具才能读取）")

    bad = [r for r in s.raids if not r.healthy]
    evidence = []
    for r in s.raids:
        evidence.append(ev(f"raid:{r.kind}", r.name,
                           f"{r.state} {r.members_active}/{r.members_total}",
                           note="; ".join(r.errors) if r.errors else "",
                           num=r.members_active))

    if bad:
        detail = "; ".join(
            f"{r.name}（{r.level}）: {r.state} " + ("、".join(r.errors) or "健康标记为失败")
            for r in bad
        )
        return R(Status.FAIL, f"{len(bad)} 个阵列异常：" + "、".join(r.name for r in bad),
                 detail=detail,
                 suggestion="立即备份数据并更换故障盘；降级阵列在重建期间风险最高，避免再断电",
                 evidence=evidence, confidence=1.0)

    summary = "、".join(f"{r.name}({r.level},{r.members_active}/{r.members_total})"
                       for r in s.raids[:4])
    return R(Status.PASS, f"阵列正常：{summary}", evidence=evidence, confidence=0.95)


@check("storage.raid_rebuild", "阵列重建", "storage", weight=3,
       platforms=["linux"], tags=["nas", "verify"])
def raid_rebuild(ctx):
    s = ctx.storage
    if not s.raids:
        return R(Status.SKIP, "未检测到软阵列")
    rebuilding = [r for r in s.raids if r.state == "rebuilding" or r.rebuild_percent > 0]
    if not rebuilding:
        return R(Status.PASS, "没有阵列处于重建状态", confidence=0.9)

    r = rebuilding[0]
    pct = r.rebuild_percent
    return R(Status.WARN, f"{r.name} 正在重建（{pct}%）",
             detail="重建期间阵列处于降级状态，性能下降且再坏一块盘就会丢数据",
             suggestion="重建完成前避免大量读写与开关机；确认剩余盘健康",
             evidence=[ev(f"raid:{r.kind}", f"{r.name}.rebuild", pct, num=pct)])


@check("storage.smart_health", "硬盘 SMART 健康", "storage", weight=6,
       platforms=["linux"], requires=["smart_data"], tags=["nas", "verify"])
def smart_health(ctx):
    s = ctx.storage
    bad = [x for x in s.smart if x.healthy is False]
    evidence = [ev(f"smartctl {x.device}", "healthy",
                   "PASSED" if x.healthy else ("FAILED" if x.healthy is False else "无法判定"),
                   note=x.message)
                for x in s.smart[:12]]

    if bad:
        return R(Status.FAIL, f"{len(bad)} 块硬盘 SMART 未通过：" +
                 "、".join(x.device for x in bad),
                 detail="; ".join(f"{x.device}: {x.message or 'SMART FAILED'}" for x in bad),
                 suggestion="立即备份数据并准备更换硬盘",
                 evidence=evidence, confidence=1.0)

    return R(Status.PASS, f"{len(s.smart)} 块硬盘 SMART 全部通过",
             evidence=evidence, confidence=0.95)


@check("storage.smart_bad_sectors", "坏道计数", "storage", weight=5,
       platforms=["linux"], requires=["smart_data"], tags=["nas", "verify"])
def smart_bad_sectors(ctx):
    s = ctx.storage
    pending = [x for x in s.smart if x.pending_sectors > 0]
    realloc = [x for x in s.smart if x.reallocated_sectors > 0]

    evidence = [
        ev(f"smartctl {x.device}", "reallocated_sector_ct", x.reallocated_sectors,
           num=x.reallocated_sectors, trend="up_bad")
        for x in s.smart[:12]
    ] + [
        ev(f"smartctl {x.device}", "current_pending_sector", x.pending_sectors,
           num=x.pending_sectors, trend="up_bad")
        for x in s.smart if x.pending_sectors > 0
    ]

    if pending:
        return R(Status.FAIL,
                 f"{len(pending)} 块硬盘存在待定扇区（"
                 + "、".join(f"{x.device}:{x.pending_sectors}" for x in pending) + "）",
                 detail="待定扇区意味着已经出现读不出来的扇区，是最直接的硬盘失效前兆",
                 suggestion="立即备份并更换硬盘",
                 evidence=evidence, confidence=0.95)
    if realloc:
        return R(Status.WARN,
                 f"{len(realloc)} 块硬盘存在重映射扇区（"
                 + "、".join(f"{x.device}:{x.reallocated_sectors}" for x in realloc) + "）",
                 detail="已有坏道被备用扇区替换，短期内可用，但数量持续增长说明盘在老化",
                 suggestion="加强备份频率，记录数值以便下次对比是否增长",
                 evidence=evidence, confidence=0.95)
    return R(Status.PASS, "未发现坏道计数", evidence=evidence, confidence=0.95)


@check("storage.smart_age", "硬盘通电时长", "storage", weight=2,
       platforms=["linux"], requires=["smart_data"], tags=["verify"])
def smart_age(ctx):
    s = ctx.storage
    known = [x for x in s.smart if x.power_on_hours > 0]
    if not known:
        return R(Status.UNKNOWN, "未读取到通电时长")

    oldest = max(known, key=lambda x: x.power_on_hours)
    years = oldest.power_on_hours / 8760
    evidence = [ev(f"smartctl {x.device}", "power_on_hours", x.power_on_hours,
                   num=x.power_on_hours) for x in known[:12]]

    if years >= 8:
        return R(Status.WARN, f"最老的盘已通电 {years:.1f} 年（{oldest.device}）",
                 detail="机械盘的设计寿命通常在 5-8 年区间，二手验机时这是重要议价点",
                 suggestion="规划更换；确保 RAID 冗余与备份可用",
                 evidence=evidence)
    if years >= 5:
        return R(Status.WARN, f"最老的盘已通电 {years:.1f} 年（{oldest.device}）",
                 suggestion="进入老化期，建议提高备份频率并关注坏道计数",
                 evidence=evidence)
    return R(Status.PASS, f"最老的盘通电 {years:.1f} 年", evidence=evidence)


@check("storage.smart_temperature", "硬盘温度", "storage", weight=2,
       platforms=["linux"], requires=["smart_data"], tags=["nas"])
def smart_temperature(ctx):
    s = ctx.storage
    temps = [x for x in s.smart if x.temperature_c > 0]
    if not temps:
        return R(Status.UNKNOWN, "未读取到硬盘温度")

    hott = max(temps, key=lambda x: x.temperature_c)
    evidence = [ev(f"smartctl {x.device}", "temperature_c", x.temperature_c,
                   num=x.temperature_c) for x in temps[:12]]

    if hott.temperature_c >= 60:
        return R(Status.WARN, f"硬盘温度 {hott.temperature_c}°C（{hott.device}），过高",
                 detail="机械盘长期高于 55°C 会显著缩短寿命",
                 suggestion="改善机箱风道，检查风扇转速", evidence=evidence)
    if hott.temperature_c >= 50:
        return R(Status.WARN, f"硬盘温度 {hott.temperature_c}°C（{hott.device}）",
                 suggestion="关注散热，避免夏季高温时叠加热点", evidence=evidence)
    return R(Status.PASS, f"硬盘温度 {hott.temperature_c}°C", evidence=evidence)


@check("storage.speed", "读写速度", "storage", weight=2,
       platforms=["any"], tags=["nas", "slow"])
def speed(ctx):
    s = ctx.storage
    if not s.speed_test_done:
        return R(Status.SKIP, "未执行读写测速",
                 detail="使用了 --no-speed-test，或目标路径不可写")

    write, read = s.seq_write_mbps, s.seq_read_mbps
    best = max(write, read)
    evidence = [ev("顺序写", "write_mbps", write, num=write),
                ev("顺序读", "read_mbps", read, num=read)]

    if best <= 0:
        return R(Status.UNKNOWN, "测速未取得有效数据",
                 detail="读写均为 0，可能是 I/O 异常或路径只读")
    if best < 10:
        return R(Status.WARN, f"读写异常低（写 {write} / 读 {read} MB/s）",
                 detail="正常机械盘顺序读写应在 100 MB/s 以上，SSD 更高",
                 suggestion="检查磁盘健康、SATA 线缆、是否被其他任务占满 I/O",
                 evidence=evidence)
    if best < 50:
        return R(Status.WARN, f"读写偏慢（写 {write} / 读 {read} MB/s）",
                 suggestion="排除网络盘误判；检查是否走了 USB 2.0 或链路降速",
                 evidence=evidence)
    return R(Status.PASS, f"写 {write} / 读 {read} MB/s", evidence=evidence)
