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
#
# 4.1（DEBT-002）：新增「可执行性」两个字段与一份行动计划——
#   · checks[] 新增 priority（0–3）与 fix_risk（低/中/高）
#   · 顶层新增 action_plan（只由 WARN/FAIL 生成，按优先级排序）
#   · 纯新增，不改既有字段的含义与取值，4.0 的消费方可忽略这两个字段
# 4.0（DEBT-009）：coverage 的口径变了——
#   · 新增 low_confidence / trustworthy / trustworthy_percent 三个字段
#   · blind_percent 现在 = (unknown + low_confidence) / applicable
#   · score 的计算方式变了：低置信的 PASS 不计入分母
# 历史库里的旧分数与新口径**不可直接比较**，对比时会提示口径变更。
REPORT_VERSION = "4.1"

# 低于此置信度的判定项，在报告里标注「结论存疑」。
# 置信度低不等于判定错，而是「数据不足以支撑这个结论」——
# 典型来源：多源读数互相矛盾（见 nastool/fusion.py）。
LOW_CONFIDENCE = 0.7

# 低于此置信度的判定项**不计入分数分母**（DEBT-009）。
#
# 为什么用 `<=` 而不是 `<`：多源冲突时置信度恰好落在 0.5，
# 用严格小于会把最需要提示的那一类漏掉。
#
# 为什么只看 PASS：置信度低意味着「数据不足以支撑结论」。
#   · PASS  不可信 —— 不能因为读不准就断言「没问题」，从分母剔除，
#                    相当于「这次没测到」，同时计入盲区拉低覆盖度。
#   · FAIL/WARN 仍要计入 —— 宁可误报不可漏报。把可疑的严重问题
#                    从分数里抹掉，等于让设备看起来比实际更健康。
# 这条与「温度取 MAX 而非平均」是同一条安全保守逻辑。
MIN_CONFIDENCE_FOR_SCORING = 0.5


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

# ── 可执行性：优先级与修复风险（DEBT-002）────────────────────
#
# 这两个字段回答「先做哪个」和「这一条修起来有没有风险」，是报告从
# 「体检诊断」走向「照着做的清单」的关键。为什么由判定项声明而不是评分器
# 推算：判定项比评分器更清楚这件事多急——「硬盘坏道」和「Telnet 开着」
# 都是 FAIL，但紧急程度差一个数量级，任何统一公式都算不出这个差别。
#
# priority（问题本身的紧急度）
PRIORITY_NAMES = {
    3: "立即处理",   # 数据丢失 / 安全暴露 / 设备随时可能挂
    2: "尽快处理",   # 服务不可用或即将不可用
    1: "计划处理",   # 配置不合理、性能受损、版本落后
    0: "可选优化",   # 有则更好，不做也不影响使用
}
PRIORITY_DEFAULT = 1     # 忘标时的兜底：按「计划处理」，而不是被降级成「可选」

# fix_risk（修这个动作本身的风险）
#
# 与 priority 是两个维度：priority 是「不修会怎样」，fix_risk 是「修的时候
# 可能弄坏什么」。一个高优先级 + 高风险的项（换硬盘）要提醒备份；
# 高优先级 + 低风险的项（关掉 Telnet）可以直接动手。
FIX_RISK_ORDER = {"低": 0, "中": 1, "高": 2}
FIX_RISK_DEFAULT = "中"   # 不确定时假设有风险，宁可让用户多看一眼

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
    # None / 空串 = 「判定项没单独指定，用注册表里的声明」。
    # 保留"未指定"这个状态是有意的：引擎要在组装时才知道该继承哪个值，
    # 所以不在这里归一化，而是通过 effective_* 读取。
    priority: Optional[int] = None     # 0–3：出问题时这件事多急（DEBT-002）
    fix_risk: str = ""                 # 低/中/高：修它本身的风险

    @property
    def effective_priority(self) -> int:
        """读优先级：非法或缺省时退回默认，报告器不必到处判空。"""
        return self.priority if self.priority in PRIORITY_NAMES else PRIORITY_DEFAULT

    @property
    def effective_fix_risk(self) -> str:
        return self.fix_risk if self.fix_risk in FIX_RISK_ORDER else FIX_RISK_DEFAULT

    @property
    def low_confidence(self) -> bool:
        """置信度低到不足以支撑这个结论（数据不够，而非判定错）。"""
        return self.confidence <= MIN_CONFIDENCE_FOR_SCORING

    @property
    def counts_toward_score(self) -> bool:
        """
        这一项是否计入分数分母。

        非对称规则（见 MIN_CONFIDENCE_FOR_SCORING 的说明）：
          · 低置信的 PASS      → 不计入。不能因为读不准就断言「没问题」。
          · 低置信的 WARN/FAIL → **仍然计入**。宁可误报不可漏报，
                                 把可疑的严重问题从分数里抹掉，
                                 等于让设备看起来比实际更健康。
          · UNKNOWN / SKIP     → 本就不计入（不是「低置信」，是「没测」）。
        """
        if not self.status.judged:
            return False
        if self.status is Status.PASS:
            return not self.low_confidence
        return True

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
            "priority": self.effective_priority,
            "fix_risk": self.effective_fix_risk,
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

    `low_confidence` 是第三种"不确定"，与 UNKNOWN 不同：
      · UNKNOWN          —— **没测到**（读不到、权限不足、工具缺失）
      · low_confidence   —— **测到了但不可信**（多源读数互相矛盾）
    两者都会让"结论有限"，所以都计入盲区；但成因不同，报告要分开显示，
    否则用户会以为所有不确定都是"工具没装好"。
    """

    total: int = 0
    judged: int = 0
    unknown: int = 0
    skipped: int = 0
    low_confidence: int = 0

    @property
    def applicable(self) -> int:
        return max(0, self.total - self.skipped)

    @property
    def trustworthy(self) -> int:
        """
        有可信结论的项数（判定了，且置信度够高）。

        **注意它与 `CategoryScore.usable` 不是一回事**（见 ADR-0011）：
          · 本字段 = judged − 全部低置信项，包括低置信的 FAIL。
            低置信 FAIL 虽不可信，但它**确实计入了分数**（非对称规则），
            所以这里衡量的是「结论有多可信」，不是「有多少项参与了打分」。
          · `CategoryScore.usable` = 真正参与该分类打分的项数。
            它的分母必须与实际打分分母一致，否则报告里的分母对不上分数。

        两者名字不同、含义不同，别再混用。
        """
        return max(0, self.judged - self.low_confidence)

    @property
    def percent(self) -> float:
        return round(self.judged / self.applicable * 100, 1) if self.applicable else 0.0

    @property
    def trustworthy_percent(self) -> float:
        """可信结论的占比——比 percent 更能代表"这份报告能有多可靠"。"""
        return round(self.trustworthy / self.applicable * 100, 1) if self.applicable else 0.0

    @property
    def blind_percent(self) -> float:
        """
        盲区占比 = 读不到 + 读到了但不可信。

        低置信项也算盲区：如果一半的检查结论都存在争议，
        那这份报告就不该给出"状态良好"的评价。
        """
        blind = self.unknown + self.low_confidence
        return round(blind / self.applicable * 100, 1) if self.applicable else 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "applicable": self.applicable,
            "judged": self.judged,
            "unknown": self.unknown,
            "skipped": self.skipped,
            "low_confidence": self.low_confidence,
            "trustworthy": self.trustworthy,
            "percent": self.percent,
            "trustworthy_percent": self.trustworthy_percent,
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
    low_confidence: int = 0          # 判定了但未计入分数的项数（DEBT-009）

    @property
    def usable(self) -> int:
        """
        真正计入分数的项数。

        低置信的 PASS 被剔除（不进分母），低置信的 WARN/FAIL 仍然计入。
        这个分母**必须**与实际打分用的分母一致——否则报告里显示的
        「12/15」和分数就对不上账了。
        """
        return max(0, self.judged - self.low_confidence)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "name": self.name,
            "weight": self.weight,
            "score": self.score,
            "judged": self.judged,
            "total": self.total,
            "low_confidence": self.low_confidence,
            "usable": self.usable,
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


# ── 行动计划 ────────────────────────────────────────────────
@dataclass
class ActionItem:
    """
    一条「建议做什么」。

    只由 WARN / FAIL 生成：PASS 不需要行动，而 UNKNOWN 需要的不是"行动"
    而是"先让它能测"——那是 `--self-test` 的职责（DEBT-011），混进这里
    会让用户拿着一份"请安装 smartctl"的清单去修一台其实完好的机器。
    """

    rank: int
    id: str
    title: str
    category: str
    status: Status
    priority: int
    fix_risk: str
    why: str = ""       # 现在是什么状况（即 summary）
    action: str = ""    # 建议怎么做（即 suggestion）

    @property
    def priority_name(self) -> str:
        return PRIORITY_NAMES.get(self.priority, str(self.priority))

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "status": self.status.value,
            "priority": self.priority,
            "priority_name": self.priority_name,
            "fix_risk": self.fix_risk,
            "why": self.why,
            "action": self.action,
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

    def action_plan(self) -> List[ActionItem]:
        """
        把 WARN / FAIL 排成一份「先做哪个」的清单（DEBT-002）。

        排序三层，每层都有理由：
          1. **priority 降序** —— 主维度。「硬盘要坏」和「Telnet 开着」
             都是 FAIL，但前者可能导致数据全丢，不该并列
          2. **状态严重度** —— 同优先级下 FAIL 在 WARN 前面
          3. **fix_risk 升序** —— 同样紧急的两件事，先做那个不容易弄坏的。
             这一层解决的是"我今晚只有半小时"的真实处境
          最后用 id 兜底，保证同一份报告两次运行顺序一致（结论可复现）
        """
        items = [c for c in self.checks
                 if c.status in (Status.FAIL, Status.WARN)]
        items.sort(key=lambda c: (
            -c.effective_priority,
            SEVERITY_ORDER[c.status],
            FIX_RISK_ORDER.get(c.effective_fix_risk, len(FIX_RISK_ORDER)),
            c.id,
        ))
        return [
            ActionItem(
                rank=i, id=c.id, title=c.title, category=c.category,
                status=c.status, priority=c.effective_priority,
                fix_risk=c.effective_fix_risk,
                why=c.summary, action=c.suggestion,
            )
            for i, c in enumerate(items, 1)
        ]

    @property
    def healthy(self) -> bool:
        return not self.failures()

    def summary_line(self) -> str:
        total = "N/A" if self.score.total is None else str(self.score.total)
        return (f"{total} 分 / {self.score.grade} 级 · "
                f"严重 {len(self.failures())} 项 · 告警 {len(self.warnings())} 项 · "
                f"不可判定 {self.coverage.unknown} 项（覆盖 {self.coverage.percent}%）")

    def to_dict(self) -> dict:
        plan = self.action_plan()
        d = {
            "meta": self.meta.to_dict(),
            "score": self.score.to_dict(),
            "coverage": self.coverage.to_dict(),
            "action_plan": {
                "count": len(plan),
                "items": [a.to_dict() for a in plan],
            },
            "checks": [c.to_dict() for c in self.sorted_checks()],
        }
        if self.platform is not None and hasattr(self.platform, "to_dict"):
            d["platform"] = self.platform.to_dict()
        if self.facts is not None and hasattr(self.facts, "to_dict"):
            d["facts"] = self.facts.to_dict()
        if self.collect_errors:
            d["collect_errors"] = list(self.collect_errors)
        return d
