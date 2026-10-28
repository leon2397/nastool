"""
core/scoring.py — 健康评分

把分散的检测结果收敛成一个可比较的分数，方便：
  - 批量验收（一批机器谁不健康）
  - 定期体检（同一台机器分数变化）
  - 给非技术用户一个直观结论

权重按 NAS 实际关注度分配：
  存储 40 / 网络 25 / 系统 20 / 服务 15
AI 算力单独计算，不计入总分——不跑 AI 的纯存储 NAS 不应该因此扣分。
"""
from dataclasses import dataclass, field
from typing import List

from .ai_accel import AIReport
from .device import DeviceReport
from .network import NetworkReport
from .platform_detect import PlatformReport
from .services import ServicesReport
from .storage import StorageReport


LEVEL_CRITICAL = "critical"
LEVEL_WARNING = "warning"
LEVEL_INFO = "info"


@dataclass
class Finding:
    level: str = LEVEL_INFO
    category: str = ""
    message: str = ""
    suggestion: str = ""


@dataclass
class CategoryScore:
    name: str = ""
    score: int = 0
    weight: float = 0.0
    checks: List[str] = field(default_factory=list)


@dataclass
class ScoreReport:
    total: int = 0
    grade: str = ""
    verdict: str = ""
    categories: List[CategoryScore] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    ai_score: int = 0
    ai_note: str = ""


def _grade(total: int) -> tuple:
    if total >= 90:
        return "A", "状态良好，可放心使用"
    if total >= 80:
        return "B", "基本可用，建议按提示优化"
    if total >= 60:
        return "C", "存在明显问题，建议尽快处理"
    return "D", "存在严重问题，需立即处理"


# ── 存储（40）───────────────────────────────────────────────
def _score_storage(rep: StorageReport, findings: List[Finding]) -> int:
    checks = []

    # 目标路径可用（15）
    if rep.target_exists and rep.is_dir and rep.can_write:
        checks.append((15, 15))
    else:
        checks.append((0, 15))
        findings.append(Finding(LEVEL_CRITICAL, "存储",
                                f"数据路径不可用：{rep.target_path}",
                                "检查挂载状态与目录权限"))

    # 剩余空间（10）
    pct = rep.target_use_percent
    if pct < 80:
        checks.append((10, 10))
    elif pct < 90:
        checks.append((6, 10))
        findings.append(Finding(LEVEL_WARNING, "存储", f"数据盘已用 {pct}%", "建议清理或扩容"))
    elif pct < 95:
        checks.append((3, 10))
        findings.append(Finding(LEVEL_WARNING, "存储", f"数据盘已用 {pct}%，空间紧张", "尽快扩容/清理"))
    else:
        checks.append((0, 10))
        findings.append(Finding(LEVEL_CRITICAL, "存储", f"数据盘已用 {pct}%，即将写满", "立即清理或扩容"))

    # RAID 健康（6）
    if not rep.raids:
        checks.append((6, 6))       # 单盘/无阵列不扣分
    else:
        unhealthy = [r for r in rep.raids if not r.healthy]
        if not unhealthy:
            checks.append((6, 6))
        else:
            checks.append((0, 6))
            for r in unhealthy:
                findings.append(Finding(LEVEL_CRITICAL, "存储",
                                        f"阵列 {r.name} 异常：{'；'.join(r.errors) or r.state}",
                                        "立即备份数据并更换故障盘"))

    # SMART（6）
    bad_smart = [s for s in rep.smart if s.healthy is False]
    if not rep.smart:
        checks.append((6, 6))       # 无 SMART 数据不扣分（容器/权限常见）
    elif not bad_smart:
        checks.append((6, 6))
    else:
        checks.append((2, 6))
        for s in bad_smart:
            findings.append(Finding(LEVEL_CRITICAL, "存储",
                                    f"磁盘 {s.device} 健康异常：{s.message or 'SMART FAILED'}",
                                    "立刻备份并准备换盘"))

    # 读写速度（3）
    if not rep.speed_test_done:
        checks.append((3, 3))
    elif rep.seq_write_mbps >= 50 or rep.seq_read_mbps >= 50:
        checks.append((3, 3))
    elif rep.seq_write_mbps >= 10 or rep.seq_read_mbps >= 10:
        checks.append((2, 3))
        findings.append(Finding(LEVEL_WARNING, "存储",
                                f"读写偏慢（写 {rep.seq_write_mbps} MB/s / 读 {rep.seq_read_mbps} MB/s）",
                                "检查磁盘健康、网络瓶颈或负载"))
    else:
        checks.append((0, 3))
        findings.append(Finding(LEVEL_WARNING, "存储", "读写速度异常低", "检查磁盘与 I/O 错误"))

    got = sum(g for g, _ in checks)
    full = sum(f for _, f in checks)
    return round(got / full * 40) if full else 0


# ── 网络（25）───────────────────────────────────────────────
def _score_network(rep: NetworkReport, findings: List[Finding]) -> int:
    checks = []
    active = [i for i in rep.interfaces if i.up and i.has_usable_ip()]

    # 有可用网卡（10）
    if active:
        checks.append((10, 10))
    else:
        checks.append((0, 10))
        findings.append(Finding(LEVEL_CRITICAL, "网络", "没有可用网络接口（无 IP）",
                                "检查网线/网卡配置"))

    # 链路速率（6）
    speed = rep.worst_link_speed()
    if speed == 0:
        checks.append((6, 6))       # 未知不扣分（虚拟机/无线常见）
    elif speed >= 1000:
        checks.append((6, 6))
    elif speed >= 100:
        checks.append((3, 6))
        findings.append(Finding(LEVEL_WARNING, "网络", f"存在百兆链路（{speed} Mbps）",
                                "NAS 建议千兆起步，检查网线与交换机"))
    else:
        checks.append((1, 6))
        findings.append(Finding(LEVEL_WARNING, "网络", f"链路速率过低（{speed} Mbps）",
                                "检查网线/无线连接"))

    # 网关 / DNS（5）
    gw_ok = rep.gateway_reachable or (rep.dns_ok and rep.gateway == "")
    if gw_ok:
        checks.append((5, 5))
    else:
        checks.append((2, 5))
        findings.append(Finding(LEVEL_WARNING, "网络", "默认网关不可达",
                                "内网直连可忽略，否则检查路由"))

    # 对端可达（4）
    if not rep.peers:
        checks.append((4, 4))
    else:
        ok_peers = [p for p in rep.peers if p.reachable]
        ratio = len(ok_peers) / len(rep.peers)
        checks.append((round(4 * ratio), 4))
        for p in rep.peers:
            if not p.reachable:
                findings.append(Finding(LEVEL_WARNING, "网络",
                                        f"对端不可达：{p.label}", "确认目标服务是否开启"))

    got = sum(g for g, _ in checks)
    full = sum(f for _, f in checks)
    return round(got / full * 25) if full else 0


# ── 系统（20）───────────────────────────────────────────────
def _score_system(device: DeviceReport, platform: PlatformReport,
                  findings: List[Finding]) -> int:
    checks = []

    # CPU / 内存能读到（6）
    if device.cpu.cores > 0 and device.memory.total_gb > 0:
        checks.append((6, 6))
    else:
        checks.append((2, 6))
        findings.append(Finding(LEVEL_WARNING, "系统", "未能完整读取 CPU/内存信息",
                                "确认权限，或该平台不受支持"))

    # 内存压力（6）
    mem = device.memory
    if mem.total_gb == 0:
        checks.append((6, 6))
    elif mem.used_percent < 80:
        checks.append((6, 6))
    elif mem.used_percent < 90:
        checks.append((4, 6))
        findings.append(Finding(LEVEL_WARNING, "系统", f"内存占用 {mem.used_percent}%",
                                "检查是否有异常进程"))
    else:
        checks.append((1, 6))
        findings.append(Finding(LEVEL_CRITICAL, "系统", f"内存占用过高 {mem.used_percent}%",
                                "检查内存泄漏进程，必要时扩容"))

    # 温度（5）
    temps = [t.temp_c for t in device.thermals if t.temp_c > 0]
    if not temps:
        checks.append((5, 5))       # 读不到温度不扣分
    else:
        hottest = max(temps)
        if hottest < 65:
            checks.append((5, 5))
        elif hottest < 80:
            checks.append((3, 5))
            findings.append(Finding(LEVEL_WARNING, "系统", f"温度偏高 {hottest}°C",
                                    "检查散热与风扇"))
        else:
            checks.append((0, 5))
            findings.append(Finding(LEVEL_CRITICAL, "系统", f"温度过高 {hottest}°C",
                                    "立即检查散热，避免降频或损伤硬件"))

    # 只读挂载 / 根分区（3）
    checks.append((3, 3))

    got = sum(g for g, _ in checks)
    full = sum(f for _, f in checks)
    return round(got / full * 20) if full else 0


# ── 服务（15）───────────────────────────────────────────────
def _score_services(rep: ServicesReport, findings: List[Finding]) -> int:
    checks = []

    # 有文件共享能力（8）——NAS 的基本职能
    if rep.has("文件共享"):
        checks.append((8, 8))
    else:
        checks.append((4, 8))
        findings.append(Finding(LEVEL_INFO, "服务", "未检测到 SMB/NFS 等文件共享服务",
                                "如果只是本机存储可以忽略"))

    # 高风险服务（7）
    risky = [i for i in rep.items if i.port in (23, 2375)]
    if not risky:
        checks.append((7, 7))
    else:
        checks.append((2, 7))
        for i in risky:
            findings.append(Finding(LEVEL_WARNING, "服务",
                                    f"{i.name}({i.port}) 正在监听",
                                    "关闭该服务或限制访问来源"))

    got = sum(g for g, _ in checks)
    full = sum(f for _, f in checks)
    return round(got / full * 15) if full else 0


def _score_ai(ai: AIReport) -> tuple:
    """AI 能力分（不计入总分）。"""
    if not ai.hardware_accelerated:
        return 0, "无 AI 加速硬件（纯存储用途无需关注）"
    base = 60
    if ai.inference_available:
        base += 25
    if ai.inference_test_ms and ai.inference_test_ms < 2000:
        base += 15
    primary = ai.primary
    name = primary.name if primary else ai.best_chip_type
    return min(base, 100), f"{name}（{ai.best_chip_type}）"


def compute_score(device: DeviceReport, storage: StorageReport,
                  network: NetworkReport, services: ServicesReport,
                  platform: PlatformReport, ai: AIReport) -> ScoreReport:
    """主入口：汇总各维度得分，产出总分 + 等级 + 问题清单。"""
    findings: List[Finding] = []

    s_storage = _score_storage(storage, findings)
    s_network = _score_network(network, findings)
    s_system = _score_system(device, platform, findings)
    s_services = _score_services(services, findings)

    total = s_storage + s_network + s_system + s_services
    grade, verdict = _grade(total)

    # 各模块自带的问题也收进来（去掉重复）
    for w in storage.warnings:
        findings.append(Finding(LEVEL_WARNING, "存储", w))
    for e in storage.errors:
        findings.append(Finding(LEVEL_CRITICAL, "存储", e))
    for w in network.warnings:
        findings.append(Finding(LEVEL_WARNING, "网络", w))
    for e in network.errors:
        findings.append(Finding(LEVEL_CRITICAL, "网络", e))
    for r in storage.raids:
        for e in r.errors:
            findings.append(Finding(LEVEL_CRITICAL, "存储", f"{r.name}: {e}"))
    for s in storage.smart:
        if s.healthy is False:
            findings.append(Finding(LEVEL_CRITICAL, "存储",
                                    f"{s.device} {s.message or 'SMART 检测未通过'}"))
    for w in services.warnings:
        findings.append(Finding(LEVEL_WARNING, "服务", w))
    for note in network.notes:
        findings.append(Finding(LEVEL_INFO, "网络", note))
    for note in services.notes:
        findings.append(Finding(LEVEL_INFO, "服务", note))
    for w in platform.warnings:
        findings.append(Finding(LEVEL_INFO, "平台", w))

    # 去重（同一句话只保留一次，保留更严重的级别）
    order = {LEVEL_CRITICAL: 0, LEVEL_WARNING: 1, LEVEL_INFO: 2}
    seen = {}
    for f in findings:
        key = (f.category, f.message)
        if key not in seen or order[f.level] < order[seen[key].level]:
            seen[key] = f
    findings = sorted(seen.values(), key=lambda f: (order[f.level], f.category))

    # 有严重问题时不允许显示「良好」等级：分数封顶到 59（C 级）
    if any(f.level == LEVEL_CRITICAL for f in findings):
        total = min(total, 59)
    grade, verdict = _grade(total)

    ai_score, ai_note = _score_ai(ai)

    return ScoreReport(
        total=total,
        grade=grade,
        verdict=verdict,
        categories=[
            CategoryScore("存储", s_storage, 40.0, []),
            CategoryScore("网络", s_network, 25.0, []),
            CategoryScore("系统", s_system, 20.0, []),
            CategoryScore("服务", s_services, 15.0, []),
        ],
        findings=findings,
        ai_score=ai_score,
        ai_note=ai_note,
    )
