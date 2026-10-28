"""
nastool/model.py — 全系统统一数据模型

这是整个产品的契约层，四层结构都只认这里的类型：

    collect/   采集原始事实（不做判定）      → Facts
    checks/    逐项判定                      → CheckResult
    scoring.py 聚合成分数与覆盖度            → Score / Coverage
    reporters/ 呈现                          → 终端 / JSON / HTML

三条设计原则（也是产品可信度的来源）：

1. **「读不到」是独立状态，不是失败。**
   UNKNOWN 不扣分，但会拉低覆盖度和置信度。
   这样「不可判定」既不会被误报成「硬盘要坏」，也无法伪装成「一切正常」。

2. **每条结论都带证据。**
   Evidence 回答「你凭什么这么说」，是二手验机 / 远程售后能被复核的前提。

3. **每条结论都带置信度。**
   单一来源、存在冲突、权限受限都会降低置信度。
   聚合后的 report.confidence 就是整份报告的可信度。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# 报告格式版本：向后兼容契约，任何破坏性变更必须升这里
REPORT_VERSION = "3.0"


class Status(str, Enum):
    """单条检查的判定结果。"""

    PASS = "pass"        # 通过
    WARN = "warn"        # 有问题但可用
    FAIL = "fail"        # 严重问题，需立即处理
    SKIP = "skip"        # 不适用（平台不支持 / 当前场景不检测）
    UNKNOWN = "unknown"  # 无法判定（读不到、权限不足、工具缺失）

    @property
    def judged(self) -> bool:
        """是否算「已判定」——只有已判定的项参与打分。"""
        return self in (Status.PASS, Status.WARN, Status.FAIL)

    @property
    def glyph(self) -> str:
        return {
            Status.PASS: "✓",
            Status.WARN: "!",
            Status.FAIL: "✗",
            Status.SKIP: "·",
            Status.UNKNOWN: "?",
        }[self]

    @property
    def label(self) -> str:
        return {
            Status.PASS: "通过",
            Status.WARN: "告警",
            Status.FAIL: "严重",
            Status.SKIP: "不适用",
            Status.UNKNOWN: "不可判定",
        }[self]


# 严重度排序：越小越严重（用于报告排序）
SEVERITY_ORDER = {
    Status.FAIL: 0,
    Status.WARN: 1,
    Status.UNKNOWN: 2,
    Status.PASS: 3,
    Status.SKIP: 4,
}

# 分类：键是稳定的机器标识，值是给人看的名字
CATEGORY_ORDER = ["storage", "security", "system", "network", "services", "ai", "usb"]

CATEGORY_NAMES = {
    "storage": "存储",
    "security": "安全",
    "system": "系统与硬件",
    "network": "网络",
    "services": "服务与端口",
    "ai": "AI 算力",
    "usb": "外设",
}


def category_name(cat: str) -> str:
    return CATEGORY_NAMES.get(cat, cat)


# ── 证据 ────────────────────────────────────────────────────
@dataclass
class Evidence:
    """
    一条可复核的观测事实。

    source 说明「从哪读的」，key/value 说明「读到了什么」。
    num 用于历史对比；trend 说明数值变化的方向含义：
        "up_bad"   上升代表恶化（坏道数、错误计数、使用率）
        "up_good"  上升代表好转（剩余空间）
        ""         中性（温度、负载、通电时长——波动不代表好坏）
    只有标了方向的指标才参与"恶化/好转"判断，避免把"运行时长+0.1小时"报成恶化。
    """

    source: str = ""
    key: str = ""
    value: str = ""
    note: str = ""
    num: Optional[float] = None
    trend: str = ""

    def to_dict(self) -> dict:
        d = {"source": self.source, "key": self.key, "value": self.value}
        if self.note:
            d["note"] = self.note
        if self.num is not None:
            d["num"] = self.num
        if self.trend:
            d["trend"] = self.trend
        return d


# ── 单条检查结果 ────────────────────────────────────────────
@dataclass
class CheckResult:
    id: str
    title: str
    category: str
    status: Status = Status.UNKNOWN
    confidence: float = 0.0
    summary: str = ""
    detail: str = ""
    suggestion: str = ""
    evidence: List[Evidence] = field(default_factory=list)
    weight: float = 1.0
    duration_ms: int = 0
    error: str = ""      # 检查器自身异常（与「检测对象有问题」区分开）

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "status": self.status.value,
            "confidence": round(self.confidence, 3),
            "summary": self.summary,
            "detail": self.detail,
            "suggestion": self.suggestion,
            "weight": self.weight,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "evidence": [e.to_dict() for e in self.evidence],
        }


# ── 覆盖度 ──────────────────────────────────────────────────
@dataclass
class Coverage:
    """
    本次检测「到底判定了多少」。

    口径说明：分母用 **适用项数**（总数 - 不适用），而不是总数。
    在 Windows 上跑，一堆 Linux 专属检查会标 SKIP，这不该算作"盲区"；
    真正需要警惕的是 UNKNOWN——明明适用却读不到。

    这是可信度的另一半：一份只判定了 30% 适用项的报告，
    即使分数 100 也必须让人一眼看出它结论有限。
    """

    total: int = 0
    judged: int = 0
    unknown: int = 0
    skipped: int = 0

    @property
    def applicable(self) -> int:
        return max(0, self.total - self.skipped)

    @property
    def percent(self) -> float:
        return round(self.judged / self.applicable * 100, 1) if self.applicable else 0.0

    @property
    def blind_percent(self) -> float:
        return round(self.unknown / self.applicable * 100, 1) if self.applicable else 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "applicable": self.applicable,
            "judged": self.judged,
            "unknown": self.unknown,
            "skipped": self.skipped,
            "percent": self.percent,
            "blind_percent": self.blind_percent,
        }


# ── 分类得分 ────────────────────────────────────────────────
@dataclass
class CategoryScore:
    category: str
    name: str
    weight: float = 0.0
    score: Optional[int] = None     # None = 该类没有可判定项
    judged: int = 0
    total: int = 0

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "name": self.name,
            "weight": self.weight,
            "score": self.score,
            "judged": self.judged,
            "total": self.total,
        }


# ── 总分 ────────────────────────────────────────────────────
GRADE_VERDICT = {
    "A": "状态良好，可放心使用",
    "B": "基本可用，建议按提示优化",
    "C": "存在明显问题，建议尽快处理",
    "D": "存在严重问题，需立即处理",
    "N/A": "有效数据不足，无法给出等级",
}


@dataclass
class Score:
    total: Optional[int] = None
    grade: str = "N/A"
    verdict: str = ""
    confidence: float = 0.0
    categories: List[CategoryScore] = field(default_factory=list)
    capped: bool = False          # 是否因严重问题被封顶
    cap_reason: str = ""
    ai_score: int = 0             # AI 能力分，独立展示，不进总分
    ai_note: str = ""

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "grade": self.grade,
            "verdict": self.verdict,
            "confidence": round(self.confidence, 3),
            "capped": self.capped,
            "cap_reason": self.cap_reason,
            "ai_score": self.ai_score,
            "ai_note": self.ai_note,
            "categories": [c.to_dict() for c in self.categories],
        }


# ── 报告元信息 ──────────────────────────────────────────────
@dataclass
class ReportMeta:
    tool: str = "nastool"
    version: str = ""
    report_version: str = REPORT_VERSION
    generated_at: str = ""
    duration_s: float = 0.0
    hostname: str = ""
    profile: str = "nas"
    python: str = ""
    platform_summary: str = ""
    fingerprint: str = ""      # 设备指纹：判断两次报告是不是同一台机器
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "version": self.version,
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "duration_s": self.duration_s,
            "hostname": self.hostname,
            "profile": self.profile,
            "python": self.python,
            "platform_summary": self.platform_summary,
            "fingerprint": self.fingerprint,
            "options": self.options,
        }


# ── 完整报告 ────────────────────────────────────────────────
@dataclass
class Report:
    meta: ReportMeta = field(default_factory=ReportMeta)
    platform: Any = None                     # collect.platform.PlatformFacts
    facts: Any = None                        # collect.Facts 汇总
    checks: List[CheckResult] = field(default_factory=list)
    score: Score = field(default_factory=Score)
    coverage: Coverage = field(default_factory=Coverage)
    collect_errors: List[str] = field(default_factory=list)   # 采集器自身失败（不算判定）

    # ── 便捷查询 ──
    def failures(self) -> List[CheckResult]:
        return [c for c in self.checks if c.status is Status.FAIL]

    def warnings(self) -> List[CheckResult]:
        return [c for c in self.checks if c.status is Status.WARN]

    def unknowns(self) -> List[CheckResult]:
        return [c for c in self.checks if c.status is Status.UNKNOWN]

    def get(self, check_id: str) -> Optional[CheckResult]:
        for c in self.checks:
            if c.id == check_id:
                return c
        return None

    def by_category(self) -> Dict[str, List[CheckResult]]:
        out: Dict[str, List[CheckResult]] = {}
        for c in self.checks:
            out.setdefault(c.category, []).append(c)
        for items in out.values():
            items.sort(key=lambda x: (SEVERITY_ORDER[x.status], x.id))
        return out

    def sorted_checks(self) -> List[CheckResult]:
        return sorted(self.checks, key=lambda c: (
            CATEGORY_ORDER.index(c.category) if c.category in CATEGORY_ORDER else 99,
            SEVERITY_ORDER[c.status],
            c.id,
        ))

    @property
    def healthy(self) -> bool:
        return not self.failures()

    def summary_line(self) -> str:
        total = "N/A" if self.score.total is None else str(self.score.total)
        return (f"{total} 分 / {self.score.grade} 级 · "
                f"严重 {len(self.failures())} 项 · 告警 {len(self.warnings())} 项 · "
                f"不可判定 {self.coverage.unknown} 项（覆盖 {self.coverage.percent}%）")

    def to_dict(self) -> dict:
        d = {
            "meta": self.meta.to_dict(),
            "score": self.score.to_dict(),
            "coverage": self.coverage.to_dict(),
            "checks": [c.to_dict() for c in self.sorted_checks()],
        }
        if self.platform is not None and hasattr(self.platform, "to_dict"):
            d["platform"] = self.platform.to_dict()
        if self.facts is not None and hasattr(self.facts, "to_dict"):
            d["facts"] = self.facts.to_dict()
        if self.collect_errors:
            d["collect_errors"] = list(self.collect_errors)
        return d
