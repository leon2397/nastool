"""
checks/system.py — 系统与硬件

判定逻辑从「读不到就报错」改成「分三档」：
  读到了且正常 → PASS
  读到了但异常 → WARN / FAIL
  读不到       → UNKNOWN（不扣分，只降低覆盖度）
"""
from __future__ import annotations

import os
import time

from ..collect.util import IS_LINUX, IS_WINDOWS, have, read_file, run, safe_listdir
from ..model import Status
from ..registry import check
from ._base import R, ev


@check("system.cpu_visible", "CPU 信息可读", "system", weight=1,
       platforms=["any"], tags=["verify"])
def cpu_visible(ctx):
    d = ctx.device
    if d.cpu.cores <= 0:
        return R(Status.UNKNOWN, "无法读取 CPU 核心数",
                 detail="; ".join(d.collect_errors) or "lscpu 与 /proc/cpuinfo 均未返回数据",
                 suggestion="确认当前环境允许读取 /proc，或在受支持的系统上运行")
    return R(Status.PASS, f"{d.cpu.model}（{d.cpu.cores} 线程）",
             evidence=[
                 ev("/proc/cpuinfo", "model", d.cpu.model),
                 ev("/proc/cpuinfo", "threads", d.cpu.cores, num=d.cpu.cores),
                 ev("/proc/cpuinfo", "freq_mhz", d.cpu.freq_mhz, num=d.cpu.freq_mhz),
             ],
             confidence=0.95)


@check("system.memory_readable", "内存信息可读", "system", weight=1,
       platforms=["any"], tags=["verify"])
def memory_readable(ctx):
    mem = ctx.device.memory
    if mem.total_gb <= 0:
        return R(Status.UNKNOWN, "无法读取内存容量",
                 suggestion="确认权限或该平台的采集实现")
    return R(Status.PASS, f"{mem.total_gb} GB（可用 {mem.available_gb} GB）",
             evidence=[ev("/proc/meminfo", "total_gb", mem.total_gb, num=mem.total_gb)],
             confidence=0.95)


@check("system.memory_pressure", "内存压力", "system", weight=3,
       platforms=["any"], tags=["nas", "verify"])
def memory_pressure(ctx):
    mem = ctx.device.memory
    if mem.total_gb <= 0:
        return R(Status.UNKNOWN, "无法读取内存使用率")

    warn = ctx.threshold("mem_use_warn", 85.0)
    crit = ctx.threshold("mem_use_crit", 95.0)
    used = mem.used_percent

    evidence = [ev("/proc/meminfo", "used_percent", used, num=used)]

    if used >= crit:
        return R(Status.FAIL, f"内存占用 {used}%，已接近耗尽",
                 suggestion="检查是否有内存泄漏进程，必要时扩容内存",
                 evidence=evidence)
    if used >= warn:
        return R(Status.WARN, f"内存占用 {used}%",
                 suggestion="观察是否有异常进程常驻；ZFS ARC 占用高时可调 arc_max",
                 evidence=evidence)
    return R(Status.PASS, f"内存占用 {used}%", evidence=evidence, confidence=0.9)


@check("system.swap_pressure", "交换分区压力", "system", weight=1,
       platforms=["linux"], tags=["nas"])
def swap_pressure(ctx):
    mem = ctx.device.memory
    if mem.swap_total_gb <= 0:
        return R(Status.SKIP, "未启用交换分区",
                 detail="NAS 上不启用 swap 是常见做法，不影响使用")
    used_gb = max(0.0, mem.swap_total_gb - mem.swap_free_gb)
    pct = round(used_gb / mem.swap_total_gb * 100, 1)
    warn = ctx.threshold("swap_use_warn", 50.0)
    evidence = [ev("/proc/meminfo", "swap_used_percent", pct, num=pct)]
    if pct >= warn:
        return R(Status.WARN, f"交换分区使用 {pct}%",
                 suggestion="swap 大量占用通常意味着内存不足，检查进程内存占用",
                 evidence=evidence)
    return R(Status.PASS, f"交换分区使用 {pct}%", evidence=evidence)


@check("system.thermal", "温度", "system", weight=3,
       platforms=["linux"], tags=["nas", "verify", "ai"])
def thermal(ctx):
    zones = [t for t in ctx.device.thermals if t.temp_c > 0]
    if not zones:
        return R(Status.UNKNOWN, "未读取到温度传感器",
                 detail="容器 / 虚拟机 / 部分 ARM 设备不暴露温度接口",
                 suggestion="在宿主机上运行，或确认 /sys/class/thermal 可读")

    hottest = max(zones, key=lambda t: t.temp_c)
    warn, crit = ctx.thermal_limits()
    chip = ctx.chip_hint()

    evidence = [
        ev("thermal_zone", z.zone_type or z.zone, f"{z.temp_c}°C", num=z.temp_c)
        for z in sorted(zones, key=lambda t: -t.temp_c)[:6]
    ]

    note = f"（阈值按 {chip} 校准：{warn:.0f}/{crit:.0f}°C）" if chip != "generic" else ""
    if hottest.temp_c >= crit:
        return R(Status.FAIL, f"最高温度 {hottest.temp_c}°C，已超过安全线{note}",
                 suggestion="立即检查风扇与散热，避免降频或硬件损伤",
                 evidence=evidence)
    if hottest.temp_c >= warn:
        return R(Status.WARN, f"最高温度 {hottest.temp_c}°C，偏高{note}",
                 suggestion="清理灰尘、检查风扇转速与风道",
                 evidence=evidence)
    return R(Status.PASS, f"最高温度 {hottest.temp_c}°C{note}", evidence=evidence)


@check("system.load_average", "负载", "system", weight=2,
       platforms=["linux", "macos"], tags=["nas"])
def load_average(ctx):
    try:
        load1 = os.getloadavg()[0]
    except (OSError, AttributeError):
        return R(Status.SKIP, "当前系统不提供负载数据")

    cores = max(1, ctx.device.cpu.cores)
    per_core = round(load1 / cores, 2)
    warn = ctx.threshold("load_per_core_warn", 1.5)
    evidence = [ev("getloadavg", "load1", round(load1, 2), num=load1),
                ev("getloadavg", "per_core", per_core, num=per_core)]

    if per_core >= warn * 2:
        return R(Status.WARN, f"1 分钟负载 {load1:.2f}（每核 {per_core}），明显偏高",
                 suggestion="检查是否有备份/刮削/转码任务在满负荷运行",
                 evidence=evidence)
    if per_core >= warn:
        return R(Status.WARN, f"1 分钟负载 {load1:.2f}（每核 {per_core}）",
                 suggestion="持续偏高需排查常驻任务", evidence=evidence)
    return R(Status.PASS, f"1 分钟负载 {load1:.2f}（每核 {per_core}）",
             evidence=evidence)


@check("system.uptime", "运行时长", "system", weight=1,
       platforms=["any"], tags=["verify"])
def uptime(ctx):
    hours = ctx.device.board.uptime_hours
    if hours <= 0:
        return R(Status.UNKNOWN, "无法读取运行时长",
                 suggestion="部分平台需要管理员权限")

    days = hours / 24
    evidence = [ev("board.uptime_hours", "uptime_hours", round(hours, 1), num=hours)]

    if hours < 0.5:
        return R(Status.WARN, "系统启动不足 30 分钟",
                 detail="如果这台机器不是刚刚部署的，可能发生了意外重启或断电恢复",
                 suggestion="查看系统日志确认重启原因；二手验机时特别注意",
                 evidence=evidence)
    return R(Status.PASS, f"已连续运行 {days:.1f} 天", evidence=evidence)


@check("system.clock_sync", "时间同步", "system", weight=2,
       platforms=["linux", "windows"], tags=["nas", "verify"])
def clock_sync(ctx):
    if IS_WINDOWS:
        source = run("w32tm /query /source", timeout=8).strip()
        if not source:
            return R(Status.UNKNOWN, "无法查询 Windows 时间来源",
                     detail="Windows 时间服务（w32time）可能未运行",
                     suggestion="以管理员身份执行 w32tm /resync 验证")
        local = ("local cmos" in source.lower() or "本地 CMOS" in source
                 or "Free-running" in source or "自由运行" in source)
        evidence = [ev("w32tm /query /source", "source", source)]
        if local:
            return R(Status.WARN, "系统时间取自本地时钟，未与外部 NTP 同步",
                     detail="长期不同步会累积偏差，影响 TLS 证书校验与域认证",
                     suggestion="启动 w32time 服务并配置 NTP："
                                "w32tm /config /manualpeerlist:\"time.windows.com\" /update",
                     evidence=evidence, confidence=0.85)
        return R(Status.PASS, f"时间来源：{source}", evidence=evidence, confidence=0.9)

    synced = None
    server = ""

    if have("timedatectl"):
        out = run("timedatectl show -p NTPSynchronized --value 2>/dev/null", timeout=8)
        if out.strip() in ("yes", "no"):
            synced = out.strip() == "yes"

    if synced is None:
        # 退回配置文件判断：有配置就算"已配置"，但是否生效无法确认
        for conf in ("/etc/ntp.conf", "/etc/chrony.conf", "/etc/chrony/chrony.conf"):
            if os.path.isfile(conf):
                for line in read_file(conf).splitlines():
                    s = line.strip()
                    if s.startswith(("server ", "pool ")):
                        server = s.split()[1]
                        break
                if server:
                    synced = True
                break

    if synced is None:
        return R(Status.UNKNOWN, "无法判定时间同步状态",
                 detail="未找到 timedatectl 或 NTP 配置",
                 suggestion="若用于域认证 / 证书校验 / 备份，务必确认时间准确")

    evidence = [ev("timedatectl", "NTPSynchronized", "yes" if synced else "no")]
    if server:
        evidence.append(ev("ntp.conf", "server", server))

    if not synced:
        return R(Status.WARN, "系统时间未同步",
                 detail="时间偏差会导致 TLS 证书校验失败、Kerberos/域认证失败、备份时间戳错乱",
                 suggestion="启用 systemd-timesyncd / chrony / ntpd 并指向可用 NTP 服务器",
                 evidence=evidence)
    return R(Status.PASS, "系统时间已同步" + (f"（{server}）" if server else ""),
             evidence=evidence, confidence=0.85)


@check("system.io_pressure", "磁盘 I/O 压力", "system", weight=2,
       platforms=["linux"], tags=["nas"])
def io_pressure(ctx):
    raw = read_file("/proc/pressure/io", "")
    if not raw:
        return R(Status.SKIP, "当前内核不支持 I/O 压力指标（PSI）",
                 detail="Linux 4.20+ 才提供 /proc/pressure，老内核可忽略")

    def _avg10(line: str) -> float:
        for tok in line.split():
            if tok.startswith("avg10="):
                try:
                    return float(tok.split("=", 1)[1])
                except ValueError:
                    return 0.0
        return 0.0

    some = next((ln for ln in raw.splitlines() if ln.startswith("some")), "")
    full = next((ln for ln in raw.splitlines() if ln.startswith("full")), "")
    avg10, full10 = _avg10(some), _avg10(full)

    evidence = [ev("/proc/pressure/io", "some_avg10", avg10, num=avg10),
                ev("/proc/pressure/io", "full_avg10", full10, num=full10)]

    if full10 >= 30:
        return R(Status.WARN, f"磁盘 I/O 已饱和（full avg10={full10}%）",
                 suggestion="排查是否有重建/刮削/转码在跑；持续饱和会拖慢全部服务",
                 evidence=evidence)
    if avg10 >= 50:
        return R(Status.WARN, f"磁盘 I/O 压力偏高（some avg10={avg10}%）",
                 suggestion="观察一段时间，确认不是长期满载", evidence=evidence)
    return R(Status.PASS, f"I/O 压力正常（some avg10={avg10}%）", evidence=evidence)


@check("system.process_count", "进程数量", "system", weight=1,
       platforms=["linux"], tags=["verify"])
def process_count(ctx):
    pids = [p for p in safe_listdir("/proc") if p.isdigit()]
    if not pids:
        return R(Status.UNKNOWN, "无法读取进程列表")
    n = len(pids)
    evidence = [ev("/proc", "process_count", n, num=n)]
    if n >= 2000:
        return R(Status.WARN, f"进程数 {n}，异常偏多",
                 suggestion="检查是否有进程反复重启或 fork 炸弹",
                 evidence=evidence)
    return R(Status.PASS, f"当前 {n} 个进程", evidence=evidence, confidence=0.9)
