"""
nastool/scoring.py — 聚合成分数与覆盖度

只做三件事，不做任何具体判定：

  1. 把已判定的 CheckResult 按分类和权重折算成 0-100 的分类得分
  2. 按 profile 权重合成总分（未参与的分类不计入分母）
  3. 算出覆盖度与整体置信度

两条不可动摇的规则（产品的可信度就靠这两条）：

  · **不可判定（UNKNOWN）不扣分，但降低覆盖度。**
    读不到 SMART 不能算「硬盘坏了」，也不能算「硬盘没事」——
    它只能算「这次没测到」，并在报告里明确显示盲区比例。

  · **存在严重问题时总分封顶 59。**
    避免「97 分 A 级」下面挂着一块随时要挂的盘这种自相矛盾的结论。
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .model import (
    CATEGORY_NAMES,
    GRADE_VERDICT,
    CategoryScore,
    CheckResult,
    Coverage,
    Score,
    Status,
)
from .profiles import Profile

# 单条检查折算成得分的系数
STATUS_VALUE = {
    Status.PASS: 1.0,
    Status.WARN: 0.5,
    Status.FAIL: 0.0,
}

CRITICAL_CAP = 59


def _grade(total: Optional[int]) -> str:
    if total is None:
        return "N/A"
    if total >= 90:
        return "A"
    if total >= 80:
        return "B"
    if total >= 60:
        return "C"
    return "D"


def build_coverage(checks: Sequence[CheckResult]) -> Coverage:
    cov = Coverage(total=len(checks))
    for c in checks:
        if c.status.judged:
            cov.judged += 1
        elif c.status is Status.UNKNOWN:
            cov.unknown += 1
        else:
            cov.skipped += 1
    return cov


def _category_score(items: Sequence[CheckResult], weight: float) -> CategoryScore:
    judged = [c for c in items if c.status.judged]
    cat = CategoryScore(
        category=items[0].category if items else "",
        name=CATEGORY_NAMES.get(items[0].category, "") if items else "",
        weight=weight,
        judged=len(judged),
        total=len(items),
    )
    if not judged:
        cat.score = None
        return cat

    got = sum(c.weight * STATUS_VALUE[c.status] for c in judged)
    full = sum(c.weight for c in judged)
    cat.score = round(got / full * 100) if full else None
    return cat


def _weighted_confidence(judged: Sequence[CheckResult]) -> float:
    """整体置信度：按权重加权。不可判定的项权重为 0，只影响覆盖度。"""
    if not judged:
        return 0.0
    total_w = sum(c.weight for c in judged)
    if not total_w:
        return 0.0
    return round(sum(c.weight * c.confidence for c in judged) / total_w, 3)


def _ai_score(ai_facts) -> Tuple[int, str]:
    """AI 能力分：独立展示，不参与总分（除非 profile 明确给 ai 权重）。"""
    if ai_facts is None or not getattr(ai_facts, "hardware_accelerated", False):
        return 0, "无 AI 加速硬件（纯存储用途无需关注）"
    base = 60
    if getattr(ai_facts, "inference_available", False):
        base += 25
    ms = getattr(ai_facts, "inference_test_ms", 0) or 0
    if ms and ms < 2000:
        base += 15
    primary = getattr(ai_facts, "primary", None)
    name = getattr(primary, "name", "") if primary is not None else ""
    return min(base, 100), f"{name or ai_facts.best_chip_type}（{ai_facts.best_chip_type}）"


def compute(checks: Sequence[CheckResult], profile: Profile,
            ai_facts=None) -> Tuple[Score, Coverage]:
    """主入口：返回 (Score, Coverage)。"""
    coverage = build_coverage(checks)

    by_cat = {}
    for c in checks:
        by_cat.setdefault(c.category, []).append(c)

    categories: List[CategoryScore] = []
    for cat_key in profile.active:
        items = by_cat.get(cat_key, [])
        if not items:
            continue
        categories.append(_category_score(items, profile.weight(cat_key)))

    # 总分：只对「有得分且权重 > 0」的分类加权平均
    scored = [(c.score, c.weight) for c in categories
              if c.score is not None and c.weight > 0]
    if scored:
        w_sum = sum(w for _, w in scored)
        total: Optional[int] = round(sum(s * w for s, w in scored) / w_sum) if w_sum else None
    else:
        total = None

    # 封顶规则一：存在严重问题 → 不允许更高等级
    failures = [c for c in checks if c.status is Status.FAIL]
    reasons = []
    if failures and total is not None and total > CRITICAL_CAP:
        total = CRITICAL_CAP
        reasons.append(f"存在 {len(failures)} 项严重问题，总分封顶 {CRITICAL_CAP}")

    # 封顶规则二：盲区太大 → 不给高等级
    # 一份一半项目没判定的报告，即使剩下的都通过，也不能说"状态良好"。
    blind = coverage.blind_percent
    if total is not None and coverage.applicable:
        if blind >= 50 and total > 74:
            total = 74
            reasons.append(f"{blind}% 的适用项不可判定（盲区过大），等级封顶 C")
        elif blind >= 30 and total > 84:
            total = 84
            reasons.append(f"{blind}% 的适用项不可判定，等级封顶 B")

    grade = _grade(total)
    confidence = _weighted_confidence([c for c in checks if c.status.judged])
    ai_score, ai_note = _ai_score(ai_facts)

    return Score(
        total=total,
        grade=grade,
        verdict=GRADE_VERDICT.get(grade, ""),
        confidence=confidence,
        categories=categories,
        capped=bool(reasons),
        cap_reason="；".join(reasons),
        ai_score=ai_score,
        ai_note=ai_note,
    ), coverage
