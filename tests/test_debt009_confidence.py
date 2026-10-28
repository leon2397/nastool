"""
DEBT-009：置信度参与判定 —— 不变式测试

这条改动动的是分数的分母，错了就是「报假健康」，所以单独建文件守住。

**核心规则（非对称）**

| 判定 | 置信度 | 是否计入分数 | 理由 |
|---|---|---|---|
| PASS | 低（≤ 0.5） | **不计入** | 不能因为读不准就断言「没问题」 |
| PASS | 高（> 0.5） | 计入 | — |
| WARN / FAIL | 低 | **仍然计入** | 宁可误报不可漏报 |
| WARN / FAIL | 高 | 计入 | — |
| UNKNOWN / SKIP | — | 不计入 | 不是「低置信」，是「没测」 |

**为什么必须非对称**：如果低置信的 FAIL 也被剔除，那么一块「疑似坏了」的盘
不会拉低分数、不会触发封顶——报告会说这台设备健康。这比误报严重得多。
这与「温度取 MAX 而非平均」是同一条安全保守逻辑。

**为什么阈值是 `<= 0.5`**：多源读数冲突时置信度恰好落在 0.5，
用严格小于 `< 0.5` 会把最需要提示的那一类全部漏掉。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nastool.diff import diff_reports
from nastool.model import (
    MIN_CONFIDENCE_FOR_SCORING,
    CheckResult,
    Report,
    ReportMeta,
    Status,
)
from nastool.profiles import get_profile
from nastool.reporters.html_reporter import HTMLReporter
from nastool.reporters.terminal import TerminalReporter, render_diff
from nastool.scoring import compute


def _c(cid, status, category="storage", weight=1.0, confidence=0.9):
    return CheckResult(id=cid, title=cid, category=category,
                       status=status, weight=weight, confidence=confidence)


def _report(checks, profile="nas"):
    from nastool.collect import PlatformFacts
    r = Report()
    r.meta = ReportMeta(generated_at="2026-01-01 00:00:00", hostname="test",
                        version="0.3.5", fingerprint="fp123", profile=profile)
    r.platform = PlatformFacts()
    r.checks = checks
    r.score, r.coverage = compute(checks, get_profile(profile))
    return r


# ── 规则 1：低置信的 PASS 不进分母 ──────────────────────────
def test_low_confidence_pass_excluded_from_denominator():
    """低置信 PASS 被剔除后，分母只算剩下的项。"""
    checks = [
        _c("storage.a", Status.PASS, confidence=0.9),
        _c("storage.b", Status.PASS, confidence=0.45),   # 低置信
        _c("storage.c", Status.PASS, confidence=0.9),
    ]
    score, coverage = compute(checks, get_profile("nas"))

    # b 被剔除，a 与 c 都是通过 → 分类得分 100
    assert score.categories[0].score == 100
    # 但"已判定"仍是 3 项——它确实判定了，只是不可信
    assert coverage.judged == 3
    assert coverage.low_confidence == 1
    # 有可信结论的只有 2 项
    assert coverage.trustworthy == 2


def test_low_confidence_pass_removed_does_not_hide_a_failure():
    """
    关键不变式：低置信 PASS 被剔除，不能顺带把别的问题也抹掉。

    如果实现写成「整类不参与」，那么这一类的 FAIL 也会消失。
    """
    checks = [
        _c("storage.lowconf_pass", Status.PASS, confidence=0.4),
        _c("storage.real_fail", Status.FAIL, confidence=0.95),
    ]
    score, _ = compute(checks, get_profile("nas"))

    assert score.categories[0].score is not None
    assert score.categories[0].score < 100
    assert score.total is not None and score.total <= 59


# ── 规则 2：低置信的 FAIL/WARN 仍然计入 ─────────────────────
def test_low_confidence_fail_still_counts_and_caps():
    """低置信的严重问题必须拉低分数并触发封顶——这是防漏报的关键。"""
    checks = [
        _c("storage.a", Status.PASS, confidence=0.9),
        _c("storage.bad", Status.FAIL, confidence=0.4),
    ]
    score, _ = compute(checks, get_profile("nas"))

    # 分数被拉低（不是 100）
    assert score.categories[0].score is not None
    assert score.categories[0].score < 100
    # 总分封顶在 59 以内
    assert score.total is not None and score.total <= 59
    assert score.grade in ("C", "D")


def test_low_confidence_fail_alone_still_produces_a_score():
    """
    如果低置信 FAIL 被剔除，这一项的分类得分会变成 None，
    总分变成 N/A——设备看起来"测不出问题"，而不是"测出严重问题"。
    """
    checks = [_c("storage.bad", Status.FAIL, confidence=0.4)]
    score, _ = compute(checks, get_profile("nas"))

    assert score.categories[0].score is not None
    assert score.total is not None
    assert score.total <= 59


def test_low_confidence_warn_still_in_denominator():
    """低置信 WARN 仍计入分母（PASS 才被剔除）。"""
    checks = [
        _c("storage.a", Status.PASS, confidence=0.9),
        _c("storage.w", Status.WARN, confidence=0.4),
    ]
    score, _ = compute(checks, get_profile("nas"))

    # (100 + 50) / 2 = 75
    assert score.categories[0].score == 75


def test_asymmetry_is_real_not_accidental():
    """同一置信度下，PASS 与 FAIL 的处理必须不同。"""
    low = 0.4
    p = _c("storage.x", Status.PASS, confidence=low)
    f = _c("storage.x", Status.FAIL, confidence=low)

    assert p.counts_toward_score is False
    assert f.counts_toward_score is True


# ── 规则 3：阈值边界 ────────────────────────────────────────
def test_threshold_is_inclusive():
    """
    阈值必须用 `<=`：多源冲突时置信度恰好是 0.5，
    用严格小于会漏掉最需要提示的一类。
    """
    assert MIN_CONFIDENCE_FOR_SCORING == 0.5

    at_threshold = _c("storage.x", Status.PASS, confidence=0.5)
    below = _c("storage.y", Status.PASS, confidence=0.49)
    above = _c("storage.z", Status.PASS, confidence=0.51)

    assert at_threshold.counts_toward_score is False
    assert below.counts_toward_score is False
    assert above.counts_toward_score is True


def test_boundary_conflict_confidence_is_excluded():
    """
    复现真实场景：thermal 多源冲突时置信度恰好落在 0.5。
    这个值正好卡在边界上，必须被排除。
    """
    checks = [
        _c("system.thermal", Status.PASS, category="system", confidence=0.5),
        _c("system.other", Status.PASS, category="system", confidence=0.95),
    ]
    score, coverage = compute(checks, get_profile("nas"))

    assert coverage.low_confidence == 1
    assert coverage.judged == 2
    assert coverage.trustworthy == 1


# ── 规则 4：覆盖度口径 ──────────────────────────────────────
def test_low_confidence_counts_as_blind_spot():
    """低置信项计入盲区——结论有限，就不该给高等级。"""
    checks = [
        _c("storage.a", Status.PASS, confidence=0.9),
        _c("storage.b", Status.PASS, confidence=0.45),
    ]
    score, coverage = compute(checks, get_profile("nas"))

    assert coverage.blind_percent == 50.0
    assert coverage.trustworthy_percent == 50.0
    # 一半适用项不可信 → 触发盲区封顶
    assert score.capped is True
    assert score.total is not None and score.total <= 74


def test_unknown_and_low_confidence_are_counted_separately():
    """
    UNKNOWN（没测到）与低置信（测到了但不可信）是两回事，
    报告必须能分开显示，否则用户会以为所有不确定都是"工具没装好"。
    """
    checks = [
        _c("storage.a", Status.PASS, confidence=0.9),
        _c("storage.b", Status.UNKNOWN, confidence=0.0),
        _c("storage.c", Status.PASS, confidence=0.4),
    ]
    _, coverage = compute(checks, get_profile("nas"))

    assert coverage.unknown == 1
    assert coverage.low_confidence == 1
    assert coverage.judged == 2
    assert coverage.applicable == 3


def test_skipped_items_are_not_blind_spots():
    """SKIP 不算盲区（平台不适用），低置信才算。"""
    checks = [
        _c("storage.a", Status.PASS, confidence=0.9),
        _c("storage.b", Status.SKIP, confidence=0.0),
    ]
    _, coverage = compute(checks, get_profile("nas"))

    assert coverage.skipped == 1
    assert coverage.blind_percent == 0.0


# ── 规则 5：三个报告器说法一致 ──────────────────────────────
def test_all_reporters_explain_excluded_item():
    """终端、HTML、JSON 都要说清楚"这项没计入分数"。"""
    checks = [
        _c("storage.a", Status.PASS, confidence=0.9),
        _c("storage.lowconf", Status.PASS, confidence=0.4),
    ]
    r = _report(checks)

    text = TerminalReporter(color=False).render(r)
    assert "未计入分数" in text
    assert "结论存疑" in text

    html = HTMLReporter().build(r)
    assert "未计入分数" in html
    assert "结论存疑" in html

    d = r.to_dict()
    assert d["coverage"]["low_confidence"] == 1
    assert d["coverage"]["trustworthy"] == 1


def test_reporters_show_low_confidence_count():
    checks = [
        _c("storage.a", Status.PASS, confidence=0.9),
        _c("storage.lowconf", Status.PASS, confidence=0.4),
    ]
    r = _report(checks)

    assert "结论存疑" in TerminalReporter(color=False).render(r)
    assert "结论存疑" in HTMLReporter().build(r)


# ── 规则 5b：被剔除的项必须可见，不能被折叠隐藏 ──────────────
def test_excluded_item_is_not_hidden_in_details():
    """
    低置信的 PASS 状态上仍是 PASS，非 verbose 模式下本来会被折叠成
    "N 项通过"——但它没计入分数，藏起来等于让用户以为这类别没问题。
    """
    checks = [
        _c("storage.ok", Status.PASS, confidence=0.9),
        _c("storage.lowconf", Status.PASS, confidence=0.4),
    ]
    r = _report(checks)
    text = TerminalReporter(color=False).render(r)

    # 不能只显示 "1 项通过" 就把低置信项藏起来
    assert "未计入分数" in text
    assert "结论存疑" in text


def test_category_ratio_shows_excluded_count():
    """
    分类行不能显示成 "1/1 通过"——那会让人以为整类都查过了。
    分母要用计入分数的项数，并把被剔除的数量标出来。
    """
    checks = [
        _c("storage.ok", Status.PASS, category="storage", confidence=0.9),
        _c("storage.lowconf", Status.PASS, category="storage", confidence=0.4),
    ]
    r = _report(checks)
    text = TerminalReporter(color=False).render(r)

    assert "存疑未计分" in text


def test_category_score_exposes_low_confidence():
    checks = [
        _c("storage.ok", Status.PASS, category="storage", confidence=0.9),
        _c("storage.lowconf", Status.PASS, category="storage", confidence=0.4),
    ]
    score, _ = compute(checks, get_profile("nas"))
    cat = score.categories[0]

    assert cat.judged == 2
    assert cat.low_confidence == 1
    assert cat.usable == 1
    assert cat.to_dict()["usable"] == 1
    assert cat.to_dict()["low_confidence"] == 1


def test_coverage_trustworthy_differs_from_category_usable():
    """
    覆盖度与分类的两个「分母」含义不同，别混为一谈（ADR-0011）。

    低置信的 FAIL 是关键样本：它**不可信**，但**照样计入分数**
    （非对称规则，宁可误报不可漏报）。于是：
      · 覆盖度的 trustworthy = judged − 全部低置信项 = 1（结论不可信）
      · 分类的 usable        = 真正参与打分的项数   = 2（FAIL 计入了）

    如果把两个字段都叫 `usable`，读 JSON 的人会以为
    `coverage.usable` 就是「参与打分的项数」——那是错的。
    """
    checks = [
        _c("storage.ok", Status.PASS, category="storage", confidence=0.9),
        _c("storage.lowconf_fail", Status.FAIL, category="storage", confidence=0.4),
    ]
    score, coverage = compute(checks, get_profile("nas"))
    cat = score.categories[0]

    # 覆盖度口径：低置信 FAIL 算「不可信」
    assert coverage.judged == 2
    assert coverage.low_confidence == 1
    assert coverage.trustworthy == 1

    # 分类口径：低置信 FAIL 照样参与打分
    assert cat.judged == 2
    assert cat.low_confidence == 0
    assert cat.usable == 2

    # 覆盖度里不再有 usable 字段，避免与分类的 usable 同名不同义
    cov = coverage.to_dict()
    assert cov["trustworthy"] == 1
    assert "usable" not in cov
    assert "usable_percent" not in cov


def test_low_confidence_fail_still_caps_score():
    """低置信的 FAIL 必须照样触发封顶 59——它是不可信，不是没事。"""
    checks = [
        _c("storage.ok", Status.PASS, category="storage", confidence=0.95),
        _c("storage.ok2", Status.PASS, category="storage", confidence=0.95),
        _c("storage.lowconf_fail", Status.FAIL, category="storage", confidence=0.4),
    ]
    score, _ = compute(checks, get_profile("nas"))

    assert score.total is not None and score.total <= 59
    assert score.capped is True


# ── 规则 6：口径变更时分数不可比 ────────────────────────────
def test_diff_warns_when_report_version_changed():
    """
    DEBT-009 改变了分数算法，report_version 从 3.0 升到 4.0。
    旧历史与新报告的分数差值不可直接解读——对比时必须提示。
    """
    old = {
        "meta": {"report_version": "3.0", "generated_at": "t1", "hostname": "h"},
        "score": {"total": 90, "grade": "A"},
        "coverage": {"judged": 10},
        "checks": [],
    }
    new = {
        "meta": {"report_version": "4.0", "generated_at": "t2", "hostname": "h"},
        "score": {"total": 85, "grade": "B"},
        "coverage": {"judged": 10},
        "checks": [],
    }
    result = diff_reports(old, new)

    assert result.score_comparable is False
    assert result.caliber_note
    # 差值不可解读 → 返回 None，而不是误导性的 -5
    assert result.score_delta() is None
    assert result.to_dict()["score_delta"] is None
    assert "不可比" in result.to_dict()["caliber_note"] or "不可直接解读" in result.to_dict()["caliber_note"]


def test_diff_comparable_when_same_report_version():
    old = {
        "meta": {"report_version": "4.0", "generated_at": "t1", "hostname": "h"},
        "score": {"total": 90, "grade": "A"},
        "coverage": {"judged": 10},
        "checks": [],
    }
    new = {
        "meta": {"report_version": "4.0", "generated_at": "t2", "hostname": "h"},
        "score": {"total": 85, "grade": "B"},
        "coverage": {"judged": 10},
        "checks": [],
    }
    result = diff_reports(old, new)

    assert result.score_comparable is True
    assert result.score_delta() == -5


def test_diff_rendering_shows_caliber_warning():
    old = {
        "meta": {"report_version": "3.0", "generated_at": "t1", "hostname": "h"},
        "score": {"total": 90, "grade": "A"},
        "coverage": {"judged": 10},
        "checks": [],
    }
    new = {
        "meta": {"report_version": "4.0", "generated_at": "t2", "hostname": "h"},
        "score": {"total": 85, "grade": "B"},
        "coverage": {"judged": 10},
        "checks": [],
    }
    out = render_diff(diff_reports(old, new), color=False)
    assert "口径" in out
    # 不能显示成误导性的差值
    assert "-5" not in out


# ── 规则 7：与既有不变式不冲突 ──────────────────────────────
def test_high_confidence_behavior_unchanged():
    """高置信度的行为必须和 DEBT-009 之前完全一致。"""
    checks = [
        _c("storage.a", Status.PASS, confidence=0.9),
        _c("storage.b", Status.PASS, confidence=0.95),
        _c("storage.c", Status.PASS, confidence=1.0),
    ]
    score, coverage = compute(checks, get_profile("nas"))

    assert score.categories[0].score == 100
    assert coverage.low_confidence == 0
    assert coverage.trustworthy == 3
    assert coverage.blind_percent == 0.0


def test_mixed_confidence_still_reports_full_coverage():
    """混合置信度下，"已判定"的口径不变（低置信项仍算判定了）。"""
    checks = [
        _c("storage.a", Status.PASS, confidence=0.9),
        _c("storage.b", Status.PASS, confidence=0.45),
        _c("storage.c", Status.PASS, confidence=0.7),
    ]
    _, coverage = compute(checks, get_profile("nas"))

    assert coverage.judged == 3
    assert coverage.percent == 100.0
    # 0.7 高于阈值 0.5，不算低置信（它是"存疑"但不"不可信"）
    assert coverage.low_confidence == 1
