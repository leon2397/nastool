"""
reporters/terminal.py — 彩色终端报告

输出顺序按运维排查习惯排：先结论，再平台/系统/存储/网络/服务，最后问题清单。
支持 NO_COLOR 环境变量与 --no-color，便于重定向到文件或接入 CI 日志。
"""
import os
import sys


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    PASS = "\033[92m"
    FAIL = "\033[91m"
    WARN = "\033[93m"
    INFO = "\033[96m"
    SKIP = "\033[90m"
    HIGHLIGHT = "\033[95m"
    HEADER = "\033[95m\033[1m"


def disable_colors() -> None:
    """把所有颜色置空（重定向/CI 场景）。"""
    for attr in dir(C):
        if attr.isupper():
            setattr(C, attr, "")


def _ok(v: str = "PASS") -> str:
    return f"{C.PASS}{C.BOLD}{v}{C.RESET}"


def _fail(v: str = "FAIL") -> str:
    return f"{C.FAIL}{C.BOLD}{v}{C.RESET}"


def _warn(v: str = "WARN") -> str:
    return f"{C.WARN}{v}{C.RESET}"


def _skip(v: str) -> str:
    return f"{C.SKIP}{v}{C.RESET}"


def _title(v: str) -> str:
    return f"\n{C.HEADER}{'═' * 64}\n  {v}\n{'═' * 64}{C.RESET}"


def _section(v: str) -> str:
    return f"\n{C.BOLD}{C.INFO}▶ {v}{C.RESET}"


def _kv(key: str, val: str, ok=None) -> str:
    color = "" if ok is None else (C.PASS if ok else C.FAIL)
    return f"  {C.DIM}{key}:{C.RESET} {color}{val}{C.RESET}"


def _row(label: str, value: str, status=None) -> str:
    mark = {"pass": f"  {_ok('✓')}", "fail": f"  {_fail('✗')}",
            "warn": f"  {_warn('⚠')}", "skip": f"  {_skip('○')}"}.get(status, "")
    return f"  {C.BOLD}{label:<22}{C.RESET} {value}{mark}"


def _bar(pct: float, width: int = 20) -> str:
    filled = max(0, min(width, int(pct / 100 * width)))
    color = C.PASS if pct < 70 else (C.WARN if pct < 88 else C.FAIL)
    return f"{color}{'█' * filled}{'░' * (width - filled)}{C.RESET} {pct}%"


class TerminalReporter:
    def __init__(self, verbose: bool = False, color: bool = True):
        self.verbose = verbose
        if not color or os.environ.get("NO_COLOR"):
            disable_colors()
        self.lines = []

    # ── 概览 ────────────────────────────────────────────────
    def header(self, result) -> "TerminalReporter":
        m = result.meta
        p = result.platform
        self.lines.append(f"{C.HEADER}{C.BOLD}")
        self.lines.append("   _   _   ___ _____ ___   ___  _    ")
        self.lines.append("  | \\ | | / _ \\_   _/ _ \\ / _ \\| |   ")
        self.lines.append("  |  \\| || |_| || || | | | | | | |   ")
        self.lines.append("  | |\\  ||  _  || || |_| | |_| | |___")
        self.lines.append("  |_| \\_||_| |_||_| \\___/ \\___/|_____|")
        self.lines.append(f"{C.RESET}")
        self.lines.append(f"  {C.BOLD}nastool v{m.version}{C.RESET}"
                          f" {C.DIM}· NAS 设备检测{C.RESET}")
        self.lines.append(_kv("主机", m.hostname or p.hostname))
        self.lines.append(_kv("系统", p.pretty_name or m.platform_summary))
        if p.vendor:
            self.lines.append(_kv("平台", f"{p.vendor} {p.product} {p.version}".strip()))
        self.lines.append(_kv("时间", f"{m.generated_at}（耗时 {m.duration_s}s）"))

        s = result.score
        color = C.PASS if s.total >= 80 else (C.WARN if s.total >= 60 else C.FAIL)
        self.lines.append("")
        self.lines.append(f"  {C.BOLD}健康评分{C.RESET}  {color}{C.BOLD}{s.total}/100"
                          f"  {s.grade} 级{C.RESET}")
        self.lines.append(f"  {C.DIM}{s.verdict}{C.RESET}")
        return self

    # ── 平台 ────────────────────────────────────────────────
    def platform(self, result) -> "TerminalReporter":
        p = result.platform
        self.lines.append(_section("平台"))
        kind_label = {
            "nas_appliance": "成品 NAS",
            "nas_software": "NAS 系统",
            "linux": "通用 Linux",
            "windows": "Windows",
            "macos": "macOS",
        }.get(p.kind, p.kind)
        self.lines.append(_row("类型", kind_label))
        self.lines.append(_row("厂商/产品", f"{p.vendor or '—'} / {p.product or '—'}"))
        if p.version:
            self.lines.append(_row("系统版本", p.version))
        self.lines.append(_row("架构", f"{p.arch}  kernel {p.kernel}"))
        self.lines.append(_row("运行环境",
                               "容器 (" + p.container_type + ")" if p.in_container else "物理机",
                               "warn" if p.in_container else "pass"))
        perm_status = "pass" if p.is_root else (
            "warn" if p.kind in ("linux", "nas_appliance", "nas_software") else "skip")
        self.lines.append(_row("权限", "管理员 / root" if p.is_root else "普通用户", perm_status))
        if p.data_roots:
            self.lines.append(_row("数据盘", ", ".join(p.data_roots[:4])))
        return self

    # ── 系统 ────────────────────────────────────────────────
    def system(self, result) -> "TerminalReporter":
        d = result.device
        self.lines.append(_section("系统"))
        self.lines.append(_row("CPU", d.cpu.model))
        cores = f"{d.cpu.cores} 线程"
        if d.cpu.physical_cores:
            cores += f" / {d.cpu.physical_cores} 核"
        self.lines.append(_row("核心", cores + (f"  @ {d.cpu.freq_mhz} MHz" if d.cpu.freq_mhz else "")))
        if d.cpu.flags:
            key_flags = [f for f in d.cpu.flags if f in
                         ("neon", "asimd", "fp16", "dotprod", "sve", "avx", "avx2", "avx512f")]
            if key_flags:
                self.lines.append(_row("指令集", " / ".join(key_flags)))
        m = d.memory
        self.lines.append(_row("内存", f"{m.total_gb} GB（可用 {m.available_gb} GB）"))
        self.lines.append(f"  {C.DIM}内存占用{' ' * 14}{C.RESET} {_bar(m.used_percent)}")
        b = d.board
        self.lines.append(_row("设备型号", f"{b.manufacturer} {b.model}"))
        if b.serial:
            self.lines.append(_row("序列号", b.serial))
        self.lines.append(_row("运行时长", f"{b.uptime_hours} 小时"))
        if d.virtualization:
            self.lines.append(_row("虚拟化", d.virtualization))
        if d.thermals:
            shown = d.thermals[:6]
            parts = []
            for t in shown:
                color = C.PASS if t.temp_c < 65 else (C.WARN if t.temp_c < 80 else C.FAIL)
                parts.append(f"{t.zone_type or t.zone} {color}{t.temp_c}°C{C.RESET}")
            self.lines.append(_row("温度", "  ".join(parts)))
        return self

    # ── 存储 ────────────────────────────────────────────────
    def storage(self, result) -> "TerminalReporter":
        s = result.storage
        self.lines.append(_section("存储"))

        self.lines.append(_row("目标路径", s.target_path, "pass" if s.target_exists else "fail"))
        self.lines.append(_row("可写", "是" if s.can_write else "否", "pass" if s.can_write else "fail"))
        if s.target_total_gb:
            self.lines.append(
                _row("可用空间", f"{s.target_free_gb} GB / {s.target_total_gb} GB")
            )
            self.lines.append(f"  {C.DIM}空间占用{' ' * 14}{C.RESET} {_bar(s.target_use_percent)}")

        if s.speed_test_done:
            def _spd(v):
                return "pass" if v >= 100 else ("warn" if v >= 30 else "fail")
            self.lines.append(_row("顺序写", f"{s.seq_write_mbps} MB/s", _spd(s.seq_write_mbps)))
            self.lines.append(_row("顺序读", f"{s.seq_read_mbps} MB/s", _spd(s.seq_read_mbps)))

        if s.physical_disks:
            self.lines.append(f"\n  {C.DIM}── 物理磁盘（{len(s.physical_disks)} 块）──{C.RESET}")
            for disk in s.physical_disks:
                kind = "HDD" if disk.rotational else ("SSD" if disk.rotational is False else "磁盘")
                self.lines.append(f"    {C.BOLD}{disk.name:<14}{C.RESET} "
                                  f"{disk.size_gb:>7} GB  {kind:<4} {disk.model}")

        if s.raids:
            self.lines.append(f"\n  {C.DIM}── 阵列 ──{C.RESET}")
            for r in s.raids:
                status = "pass" if r.healthy else "fail"
                extra = ""
                if r.state == "rebuilding":
                    extra = f"  重建 {r.rebuild_percent}%"
                self.lines.append(_row(
                    f"{r.name}",
                    f"{r.kind}/{r.level}  {r.state}  {r.members_active}/{r.members_total} 盘在线{extra}",
                    status))

        if s.smart_checked:
            self.lines.append(f"\n  {C.DIM}── SMART ──{C.RESET}")
            for sm in s.smart:
                if sm.healthy is True:
                    state, status = "正常", "pass"
                elif sm.healthy is False:
                    state, status = sm.message or "异常", "fail"
                else:
                    state, status = sm.message or "不可判定", "skip"
                t = f"  {sm.temperature_c}°C" if sm.temperature_c else ""
                h = f"  {sm.power_on_hours}h" if sm.power_on_hours else ""
                self.lines.append(_row(sm.device, f"{state}{t}{h}", status))
        elif s.physical_disks:
            self.lines.append(f"  {C.DIM}SMART: 未检查（需 smartctl 与 root 权限）{C.RESET}")

        if s.disks:
            self.lines.append(f"\n  {C.DIM}── 挂载点 ──{C.RESET}")
            for d in s.disks[:8]:
                self.lines.append(f"    {d.mountpoint:<22} {d.fstype:<8} "
                                  f"{d.total_gb:>8} GB  余 {d.free_gb} GB  {_bar(d.use_percent, 12)}")
        return self

    # ── 网络 ────────────────────────────────────────────────
    def network(self, result) -> "TerminalReporter":
        n = result.network
        self.lines.append(_section("网络"))

        if n.interfaces:
            for i in n.interfaces:
                if i.up and i.has_usable_ip():
                    status = "pass"
                elif i.ip.startswith("169.254."):
                    status = "warn"
                elif i.up:
                    status = "warn"
                else:
                    status = "skip"
                extra = f"  {i.speed_mbps} Mbps" if i.speed_mbps else ""
                if i.is_wireless:
                    extra += "  WiFi"
                self.lines.append(_row(f"{i.name}", f"{i.ip or '(无 IP)'}{extra}", status))
        else:
            self.lines.append(_row("接口", "未探测到可用接口", "fail"))

        self.lines.append(f"\n  {C.DIM}── 连通性 ──{C.RESET}")
        self.lines.append(_row("网关", n.gateway or "—",
                               "pass" if n.gateway_reachable else "warn"))
        self.lines.append(_row("DNS", n.dns_server or "—", "pass" if n.dns_ok else "warn"))
        self.lines.append(_row("外网", "可达" if n.internet_reachable else "不可达",
                               "pass" if n.internet_reachable else "skip"))
        for peer in n.peers:
            self.lines.append(_row(f"对端 {peer.label}",
                                   f"{peer.rtt_ms} ms" if peer.reachable else peer.error,
                                   "pass" if peer.reachable else "fail"))
        return self

    # ── 服务 ────────────────────────────────────────────────
    def services(self, result) -> "TerminalReporter":
        sv = result.services
        self.lines.append(_section(f"服务（{sv.total_listening} 个端口监听）"))

        if sv.items:
            by_cat = {}
            for item in sv.items:
                by_cat.setdefault(item.category, []).append(item)
            for cat, items in by_cat.items():
                names = []
                for i in items:
                    label = f"{i.name}({i.port})"
                    if i.category == "其他":
                        label = f"{i.port}"
                    names.append(label)
                self.lines.append(f"  {C.BOLD}{cat:<8}{C.RESET} {', '.join(names)}")
        else:
            self.lines.append(_row("监听端口", "未探测到（可能权限受限）", "skip"))

        if sv.docker_available:
            self.lines.append(f"\n  {C.DIM}── Docker 容器（{len(sv.containers)} 个运行中）──{C.RESET}")
            for c in sv.containers[:12]:
                self.lines.append(f"    {C.BOLD}{c.name:<22}{C.RESET} {c.status}  {C.DIM}{c.image}{C.RESET}")
        return self

    # ── AI ──────────────────────────────────────────────────
    def ai(self, result) -> "TerminalReporter":
        a = result.ai
        self.lines.append(_section("AI 算力（可选能力）"))

        for dev in a.devices:
            tag = "加速" if dev.chip_type != "cpu" else "CPU"
            self.lines.append(_row(f"{dev.name}", f"[{tag}] {dev.chip_type}", "pass" if dev.available else "skip"))
            detail = []
            if dev.memory_total_mb:
                detail.append(f"显存 {dev.memory_total_mb} MB")
            if dev.driver_version:
                detail.append(f"驱动 {dev.driver_version}")
            if dev.runtime_version:
                detail.append(f"Runtime {dev.runtime_version}")
            if dev.tflops_fp16:
                detail.append(f"~{dev.tflops_fp16} TFLOPS FP16")
            if detail:
                self.lines.append(f"    {C.DIM}{'  ·  '.join(detail)}{C.RESET}")
            self.lines.append(f"    {C.DIM}检测路径: {dev.detected_by}{C.RESET}")

        self.lines.append(_row("推理引擎",
                               a.inference_engine or "无",
                               "pass" if a.inference_available else "skip"))
        if a.inference_test_ms:
            self.lines.append(_row("推理耗时", f"{a.inference_test_ms} ms"))
        if a.config_npu_type:
            match = a.config_npu_type.lower() in (a.best_chip_type or "").lower()
            self.lines.append(_row("配置声明", f"{a.config_npu_type}（{a.config_path}）",
                                   "pass" if match else "warn"))
        for note in a.notes:
            self.lines.append(f"    {C.SKIP}{note}{C.RESET}")
        return self

    # ── 适配器 ──────────────────────────────────────────────
    def adapter(self, result) -> "TerminalReporter":
        rep = result.adapter
        if not rep or not getattr(rep, "name", ""):
            return self
        self.lines.append(_section(f"平台适配检查 · {rep.name}"))
        for key, val in (rep.specific_checks or {}).items():
            self.lines.append(_kv(key, str(val)))
        for w in rep.warnings or []:
            self.lines.append(f"  {_warn('⚠ ' + w)}")
        return self

    # ── 结论 ────────────────────────────────────────────────
    def summary(self, result) -> "TerminalReporter":
        s = result.score
        self.lines.append(_title("检测结论"))

        color = C.PASS if s.total >= 80 else (C.WARN if s.total >= 60 else C.FAIL)
        self.lines.append(f"\n  {color}{C.BOLD}{s.grade} 级 · {s.total}/100{C.RESET}  {s.verdict}")

        self.lines.append(f"\n  {C.DIM}── 分项得分 ──{C.RESET}")
        for cat in s.categories:
            full = int(cat.weight)
            self.lines.append(f"    {cat.name:<6} {_bar(cat.score / full * 100 if full else 0, 16)}"
                              f"  {cat.score}/{full}")

        if s.ai_score:
            self.lines.append(f"    {'AI 能力':<6} {_bar(s.ai_score, 16)}  {s.ai_note}")
        elif s.ai_note:
            self.lines.append(f"    {C.SKIP}AI 能力  {s.ai_note}{C.RESET}")

        if s.findings:
            self.lines.append(f"\n  {C.DIM}── 问题清单 ──{C.RESET}")
            icons = {"critical": _fail("✗ 严重"), "warning": _warn("⚠ 告警"), "info": _skip("· 提示")}
            for f in s.findings[:20]:
                self.lines.append(f"  {icons.get(f.level, '·')} [{f.category}] {f.message}")
                if f.suggestion:
                    self.lines.append(f"       {C.DIM}→ {f.suggestion}{C.RESET}")
        else:
            self.lines.append(f"\n  {_ok('✅ 未发现问题')}")

        self.lines.append("")
        if result.overall_ok:
            self.lines.append(f"  {_ok('结论：设备状态正常')}")
        else:
            self.lines.append(f"  {_fail('结论：存在需要处理的问题')}")
        return self

    def full(self, result) -> "TerminalReporter":
        (self.header(result).platform(result).system(result)
         .storage(result).network(result).services(result)
         .ai(result).adapter(result).summary(result))
        return self

    def print(self) -> None:
        for line in self.lines:
            print(line)

    def __str__(self) -> str:
        return "\n".join(self.lines)
