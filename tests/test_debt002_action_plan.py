"""
DEBT-002：行动计划（priority / fix_risk）—— 契约与排序测试

这条改动不改变分数，改变的是「用户接下来做什么」。错了的后果不是报假健康，
而是**报错优先级**：把「换硬盘」排在「关 Telnet」后面，或者把高风险操作
排在低风险操作前面让用户先冒险。

**排序三层，从主到次**

| 层 | 键 | 解决什么问题 |
|---|---|---|
| 1 | priority 降序 | 「盘要坏」和「Telnet 开着」都是 FAIL，但差一个数量级 |
| 2 | 状态严重度 | 同优先级下 FAIL 先于 WARN |
| 3 | fix_risk 升序 | 同样急，先做不容易弄坏的那个（「只有半小时」的真实处境） |

同一个 (priority, status, fix_risk) 用 id 兜底——否则两次运行的顺序可能不同，
而「结论可复现」是这个产品的底线之一。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nastool.checks  # noqa: F401 - 导入即注册全部检查项
from nastool.model import (
    REPORT_VERSION,
    CheckResult,
    Report,
    Status,
)
from nastool.registry import RegistryError, all_meta, check, get
from nastool.reporters.html_reporter import HTMLReporter
from nastool.reporters.terminal import TerminalReporter


def _c(cid, status, priority=1, fix_risk="低", suggestion="做点什么",
       summary="当前状况", **kw):
    return CheckResult(id=cid, title=cid, category=kw.pop("category", "storage"),
                       status=status, summary=summary, suggestion=suggestion,
                       priority=priority, fix_risk=fix_risk, **kw)


def _report(*checks):
    r = Report()
    r.checks = list(checks)
    return r


# ── 1. 只收 WARN / FAIL ─────────────────────────────────────
def test_plan_only_contains_actionable_states():
    r = _report(
        _c("a.pass", Status.PASS),
        _c("b.warn", Status.WARN),
        _c("c.fail", Status.FAIL),
        _c("d.unknown", Status.UNKNOWN),
        _c("e.skip", Status.SKIP),
    )
    ids = [a.id for a in r.action_plan()]
    assert ids == ["c.fail", "b.warn"] or set(ids) == {"b.warn", "c.fail"}
    assert "a.pass" not in ids
    assert "d.unknown" not in ids, "UNKNOWN 需要的是'先让它能测'，不是'去修设备'"
    assert "e.skip" not in ids


def test_no_problem_means_empty_plan():
    r = _report(_c("a.pass", Status.PASS))
    assert r.action_plan() == []


# ── 2. 排序三层 ─────────────────────────────────────────────
def test_priority_dominates_status_severity():
    """高优先级的 WARN 要排在高优先级但风险更高之后……不，先看主维度：

    priority 3 的 WARN 必须排在 priority 1 的 FAIL 之前——
    这是「按紧急度而不是按状态字面」的核心。
    """
    r = _report(
        _c("low.fail", Status.FAIL, priority=1),
        _c("high.warn", Status.WARN, priority=3),
    )
    assert [a.id for a in r.action_plan()] == ["high.warn", "low.fail"]


def test_fail_before_warn_at_same_priority():
    r = _report(
        _c("b.warn", Status.WARN, priority=2),
        _c("a.fail", Status.FAIL, priority=2),
    )
    assert [a.id for a in r.action_plan()] == ["a.fail", "b.warn"]


def test_lower_fix_risk_first_at_same_priority_and_status():
    """同样急、同样严重时，先做那个不容易弄坏的。"""
    r = _report(
        _c("risky", Status.FAIL, priority=3, fix_risk="高"),
        _c("safe", Status.FAIL, priority=3, fix_risk="低"),
        _c("medium", Status.FAIL, priority=3, fix_risk="中"),
    )
    assert [a.id for a in r.action_plan()] == ["safe", "medium", "risky"]


def test_order_is_reproducible():
    """同分同权时用 id 兜底：两次运行必须给出一样顺序。"""
    checks = [_c(f"x.n{i}", Status.WARN, priority=2) for i in range(6)]
    first = [a.id for a in _report(*checks).action_plan()]
    second = [a.id for a in _report(*reversed(checks)).action_plan()]
    assert first == second == sorted(first)


def test_rank_is_continuous_from_one():
    r = _report(*[_c(f"x.n{i}", Status.WARN, priority=2) for i in range(4)])
    assert [a.rank for a in r.action_plan()] == [1, 2, 3, 4]


# ── 3. 契约字段 ─────────────────────────────────────────────
def test_report_version_is_4_1():
    assert REPORT_VERSION == "4.1"


def test_check_to_dict_carries_priority_fields():
    d = _c("a.x", Status.WARN, priority=3, fix_risk="高").to_dict()
    assert d["priority"] == 3
    assert d["fix_risk"] == "高"


def test_report_to_dict_has_action_plan():
    r = _report(_c("a.x", Status.FAIL, priority=3))
    d = r.to_dict()
    assert d["action_plan"]["count"] == 1
    item = d["action_plan"]["items"][0]
    assert item["id"] == "a.x"
    assert item["priority"] == 3
    assert item["priority_name"] == "立即处理"
    assert item["fix_risk"] == "低"
    assert item["why"] and item["action"]


def test_illegal_values_fall_back():
    """写错的值不能变成"无法排序"，要退回默认并保持可用。"""
    c = _c("a.x", Status.WARN, priority=9, fix_risk="very-high")
    assert c.effective_priority == 1
    assert c.effective_fix_risk == "中"


def test_priority_zero_is_legal_and_not_treated_as_missing():
    """0（可选优化）是合法值，不能被 `or` 之类的写法吃掉。"""
    c = _c("a.x", Status.WARN, priority=0)
    assert c.effective_priority == 0


# ── 4. 注册表校验：写错在导入时就炸，不留到报告里 ─────────────
def test_registry_rejects_out_of_range_priority():
    with pytest.raises(RegistryError):
        @check("tmp.bad_priority", "x", "storage", priority=5)
        def _f(ctx):  # pragma: no cover - 不应执行
            return {}


def test_registry_rejects_unknown_fix_risk():
    with pytest.raises(RegistryError):
        @check("tmp.bad_risk", "x", "storage", fix_risk="low")
        def _f(ctx):  # pragma: no cover - 不应执行
            return {}


def test_every_registered_check_declares_valid_priority():
    """55 项都必须有合法值——默认值能兜底，但漏标会悄悄退化成"全部一样急"。"""
    for m in all_meta():
        assert m.priority in (0, 1, 2, 3), m.id
        assert m.fix_risk in ("低", "中", "高"), m.id


def test_meta_dict_exposes_priority():
    m = get("storage.smart_health")
    assert m is not None
    d = m.to_dict()
    assert d["priority"] == 3
    assert d["fix_risk"] == "高"


def test_priority_spread_is_not_flat():
    """如果 55 项全落在同一个优先级，这个功能等于没做。"""
    prios = {m.priority for m in all_meta()}
    assert len(prios) >= 3, f"优先级分布过窄：{prios}"


# ── 5. 报告器：不能只算不显示 ────────────────────────────────
def test_terminal_shows_action_plan():
    r = _report(_c("a.x", Status.FAIL, priority=3, suggestion="立即备份数据"))
    out = TerminalReporter(verbose=False, color=False).render(r)
    assert "建议做什么" in out
    assert "立即处理" in out
    assert "立即备份数据" in out


def test_terminal_hides_plan_when_clean():
    r = _report(_c("a.x", Status.PASS))
    out = TerminalReporter(verbose=False, color=False).render(r)
    assert "建议做什么" not in out


def test_html_shows_action_plan():
    r = _report(_c("a.x", Status.WARN, priority=2, suggestion="清理一下"))
    html = HTMLReporter().build(r)
    assert "建议做什么" in html
    assert "尽快处理" in html
    assert "清理一下" in html


def test_high_fix_risk_is_called_out():
    """高风险操作必须明说，不能和低风险的一条并列铺开。"""
    r = _report(_c("a.x", Status.FAIL, priority=3, fix_risk="高"))
    assert "修它本身有风险" in HTMLReporter().build(r)
    assert "修它本身有风险" in TerminalReporter(color=False).render(r)
