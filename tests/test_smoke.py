"""
端到端与架构不变式测试

重点验证两条「不可动摇的规则」，它们是这个产品可信度的根基：
  1. 不可判定（UNKNOWN）不扣分，但会降低覆盖度
  2. 存在严重问题时总分封顶 59
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nastool.diff import diff_reports
from nastool.engine import RunOptions, run
from nastool.history import HistoryStore
from nastool.model import (
    REPORT_VERSION,
    CheckResult,
    Report,
    ReportMeta,
    Status,
)
from nastool.profiles import get_profile
from nastool.registry import all_meta, count_by_category
from nastool.reporters.html_reporter import HTMLReporter
from nastool.reporters.json_reporter import JSONReporter
from nastool.reporters.terminal import TerminalReporter, render_diff
from nastool.scoring import compute


# ── 构造工具 ────────────────────────────────────────────────
def _c(cid, status, category="storage", weight=1.0, confidence=0.9):
    return CheckResult(id=cid, title=cid, category=category,
                       status=status, weight=weight, confidence=confidence)


def _report(checks, ts="2026-01-01 00:00:00", hostname="test"):
    from nastool.collect import PlatformFacts
    r = Report()
    r.meta = ReportMeta(generated_at=ts, hostname=hostname, version="0.3.3",
                        fingerprint="fp123", profile="nas")
    r.platform = PlatformFacts()
    r.checks = checks
    r.score, r.coverage = compute(checks, get_profile("nas"))
    return r


# ── 不变式 1：不可判定不扣分，只降覆盖度 ────────────────────
def test_unknown_does_not_deduct_category_score():
    checks = [
        _c("storage.path_exists", Status.PASS),
        _c("storage.smart_health", Status.UNKNOWN, confidence=0.0),
    ]
    score, coverage = compute(checks, get_profile("nas"))

    # 分类得分只按已判定项折算，不可判定不扣分
    assert score.categories[0].score == 100
    assert score.categories[0].judged == 1
    assert coverage.judged == 1
    assert coverage.unknown == 1
    assert coverage.percent == 50.0

    # 但一半适用项读不到，属于盲区过大，总分要封顶——这是第二道保险
    assert score.capped is True
    assert score.total is not None and score.total <= 74


def test_small_blind_spot_does_not_cap():
    checks = [_c(f"storage.c{i}", Status.PASS) for i in range(9)]
    checks.append(_c("storage.smart_health", Status.UNKNOWN, confidence=0.0))

    score, coverage = compute(checks, get_profile("nas"))
    assert score.capped is False
    assert score.total == 100
    assert coverage.percent == 90.0
    assert coverage.blind_percent == 10.0


def test_all_unknown_gives_no_score():
    checks = [_c("storage.path_exists", Status.UNKNOWN, confidence=0.0)]
    score, coverage = compute(checks, get_profile("nas"))

    assert score.total is None
    assert score.grade == "N/A"
    assert coverage.percent == 0.0


# ── 不变式 2：严重问题封顶 59 ───────────────────────────────
def test_failure_caps_total_at_59():
    checks = [
        _c("storage.a", Status.PASS),
        _c("storage.b", Status.PASS),
        _c("storage.c", Status.PASS),
        _c("storage.d", Status.FAIL),
    ]
    score, _ = compute(checks, get_profile("nas"))
    assert score.total is not None and score.total <= 59
    assert score.capped is True
    assert score.grade in ("C", "D")


def test_warn_does_not_cap():
    checks = [_c("storage.a", Status.PASS), _c("storage.b", Status.WARN)]
    score, _ = compute(checks, get_profile("nas"))
    assert score.capped is False
    assert score.total == 75  # (1*1.0 + 1*0.5) / 2


def test_skipped_excluded_from_scoring():
    checks = [
        _c("storage.a", Status.PASS),
        _c("storage.b", Status.SKIP, confidence=0.0),
    ]
    score, coverage = compute(checks, get_profile("nas"))
    assert score.total == 100
    assert coverage.skipped == 1
    assert coverage.judged == 1


# ── 注册表 ──────────────────────────────────────────────────
def test_registry_loaded():
    metas = all_meta()
    assert len(metas) >= 40, f"注册项过少：{len(metas)}"

    ids = [m.id for m in metas]
    assert len(ids) == len(set(ids)), "检查项 id 重复"

    for m in metas:
        assert "." in m.id
        assert m.title
        assert m.function is not None

    counts = count_by_category()
    for cat in ("storage", "security", "system", "network", "services"):
        assert counts.get(cat, 0) > 0, f"分类 {cat} 没有任何检查项"


# ── 真实运行 ────────────────────────────────────────────────
def test_real_run_structure():
    with tempfile.TemporaryDirectory() as tmp:
        options = RunOptions(
            storage_path=tmp,
            do_speed_test=False, do_smart=False,
            do_ai=False, do_internet_check=False,
            profile="dev",
        )
        report = run(options)

    assert report.meta.generated_at
    assert report.meta.report_version == REPORT_VERSION
    assert report.meta.fingerprint
    assert report.checks, "没有执行任何检查项"
    assert report.coverage.total == len(report.checks)
    assert report.coverage.judged > 0, "一项都没判定出来，检查项全部失效"

    # 存储路径指向临时目录，这项必须通过
    path_check = report.get("storage.path_exists")
    assert path_check is not None
    assert path_check.status is Status.PASS

    for c in report.checks:
        assert isinstance(c.status, Status)
        assert 0.0 <= c.confidence <= 1.0


def test_run_with_only_filter():
    with tempfile.TemporaryDirectory() as tmp:
        options = RunOptions(
            storage_path=tmp, do_speed_test=False, do_smart=False,
            do_ai=False, do_internet_check=False,
            profile="dev", only=["storage.capacity"],
        )
        report = run(options)
    assert len(report.checks) == 1
    assert report.checks[0].id == "storage.capacity"


# ── 报告器 ──────────────────────────────────────────────────
def test_json_report_schema():
    checks = [_c("storage.a", Status.PASS), _c("storage.b", Status.WARN)]
    report = _report(checks)
    data = JSONReporter().build(report)

    for key in ("meta", "score", "coverage", "checks", "platform"):
        assert key in data, f"缺少字段 {key}"

    assert data["meta"]["report_version"] == REPORT_VERSION
    assert data["coverage"]["total"] == 2
    assert isinstance(data["checks"], list)
    assert data["checks"][0]["id"]
    assert data["score"]["grade"]

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "r.json")
        JSONReporter().dump(report, path)
        assert os.path.getsize(path) > 300
        assert JSONReporter.load(path)["meta"]["hostname"] == "test"


def test_html_self_contained():
    checks = [
        _c("storage.a", Status.PASS),
        _c("storage.b", Status.FAIL),
    ]
    html = HTMLReporter().build(_report(checks))

    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "nastool" in html
    assert "http://" not in html
    assert "https://" not in html
    assert "src=" not in html
    assert "{score}" not in html


def test_terminal_renders():
    checks = [
        _c("storage.a", Status.PASS),
        _c("storage.b", Status.WARN),
        _c("storage.c", Status.UNKNOWN, confidence=0.0),
    ]
    text = TerminalReporter(color=False).render(_report(checks))

    assert "结论" in text
    assert "覆盖" in text
    assert "存储" in text
    assert "不可判定" in text


# ── 历史与 diff ─────────────────────────────────────────────
def _dict_report(checks, ts, total):
    return {
        "meta": {"generated_at": ts, "hostname": "h1", "fingerprint": "fp1"},
        "score": {"total": total, "grade": "B"},
        "coverage": {"judged": len(checks), "total": len(checks)},
        "checks": checks,
    }


def test_history_roundtrip():
    checks = [_c("storage.a", Status.PASS)]
    report = _report(checks)

    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "h.db")
        with HistoryStore(db) as store:
            run_id = store.save(report)
            assert run_id > 0
            rows = store.list()
            assert len(rows) == 1
            assert rows[0].hostname == "test"
            loaded = store.load(run_id)
            assert loaded["meta"]["hostname"] == "test"
            assert store.latest_id("test") == run_id
            assert store.load(hostname="test")["score"]["total"] == 100


def test_diff_detects_evidence_worsening():
    old = _dict_report([{
        "id": "storage.smart_bad_sectors", "title": "坏道计数", "category": "storage",
        "status": "pass",
        "evidence": [{"source": "smartctl", "key": "reallocated_sector_ct",
                      "value": "0", "num": 0, "trend": "up_bad"}],
    }], "2026-01-01", 90)

    new = _dict_report([{
        "id": "storage.smart_bad_sectors", "title": "坏道计数", "category": "storage",
        "status": "pass",
        "evidence": [{"source": "smartctl", "key": "reallocated_sector_ct",
                      "value": "12", "num": 12, "trend": "up_bad"}],
    }], "2026-01-08", 90)

    result = diff_reports(old, new)
    assert result.has_regression() is True
    worsened = result.of_kind("evidence_worsened")
    assert worsened
    assert worsened[0].evidence[0].delta == 12
    assert "12" in render_diff(result, color=False)


def test_diff_ignores_neutral_evidence():
    """中性指标（运行时长、温度）的波动不该被报成恶化。"""
    old = _dict_report([{
        "id": "system.uptime", "title": "运行时长", "category": "system",
        "status": "pass",
        "evidence": [{"source": "board", "key": "uptime_hours",
                      "value": "74.7", "num": 74.7}],
    }], "2026-01-01", 95)

    new = _dict_report([{
        "id": "system.uptime", "title": "运行时长", "category": "system",
        "status": "pass",
        "evidence": [{"source": "board", "key": "uptime_hours",
                      "value": "74.8", "num": 74.8}],
    }], "2026-01-02", 95)

    result = diff_reports(old, new)
    assert result.has_regression() is False
    assert result.significant == []


def test_diff_detects_new_failure():
    old = _dict_report([{"id": "storage.raid_state", "title": "阵列健康",
                         "category": "storage", "status": "pass"}], "t1", 95)
    new = _dict_report([{"id": "storage.raid_state", "title": "阵列健康",
                         "category": "storage", "status": "fail"}], "t2", 59)

    result = diff_reports(old, new)
    assert [c.kind for c in result.of_kind("new_failure")] == ["new_failure"]
    assert result.score_delta() == -36


# ── 连接器契约 ──────────────────────────────────────────────
def test_ainas_connector_maps_v3_report():
    """AINAS 连接器必须从 3.0 报告的 facts/platform 里取字段。

    这是真实踩过的坑：报告格式从 2.0 升到 3.0 后，顶层 device/storage/
    ai_accelerator 全没了，连接器还在读旧键，结果推过去的设备信息全空。
    """
    from nastool.connectors.ainas import AinasConnector

    payload = {
        "meta": {"report_version": REPORT_VERSION, "hostname": "nas1"},
        "score": {"total": 88, "grade": "B"},
        "platform": {"pretty_name": "群晖 DSM 7.2", "arch": "aarch64",
                     "product": "DS920+"},
        "facts": {
            "storage": {"target_path": "/volume1", "use_percent": 62.5},
            "ai": {"best_chip_type": "rockchip"},
        },
    }

    captured = {}
    conn = AinasConnector(host="127.0.0.1", port=8000, device_name="nas1")
    conn.local_ip = lambda: "192.168.1.10"          # noqa: E731
    conn._get = lambda path, timeout=None: {"status": "healthy"}

    def fake_post(path, params, timeout=None):
        captured["register"] = params
        return {"device_id": "nas1"}

    def fake_post_json(path, body, timeout=None):
        captured["diagnosis"] = body
        return {}

    conn._post = fake_post
    conn._post_json = fake_post_json

    ok, msg = conn.push(payload)
    assert ok is True, msg

    reg = captured["register"]
    assert reg["npu_type"] == "rockchip"
    assert reg["storage_usage"] == 62.5

    diag = captured["diagnosis"]
    assert diag["score"] == 88
    assert diag["grade"] == "B"
    assert diag["chip_type"] == "rockchip"
    assert diag["os"] == "群晖 DSM 7.2"
    assert diag["arch"] == "aarch64"
    assert diag["storage_path"] == "/volume1"
    assert diag["report"] is payload


def test_ainas_connector_tolerates_missing_facts():
    """facts 缺失时不能抛异常，只能退化成空值。"""
    from nastool.connectors.ainas import AinasConnector

    captured = {}
    conn = AinasConnector(device_name="nas2")
    conn.local_ip = lambda: "127.0.0.1"             # noqa: E731
    conn._get = lambda path, timeout=None: {"status": "healthy"}
    conn._post = lambda path, params, timeout=None: {"device_id": "nas2"}
    conn._post_json = lambda path, body, timeout=None: captured.update(body) or {}

    ok, _ = conn.push({"score": {}, "facts": {}})
    assert ok is True
    assert captured["score"] is None
    assert captured["storage_path"] == ""


# ── 报告一致性 ──────────────────────────────────────────────
def test_zero_weight_category_visible_in_all_reporters():
    """权重为 0 但确有判定的分类，必须在终端 / HTML / JSON 里都能看到。

    verify 场景下 ai 权重为 0（只展示、不计分）。若报告器按 weight > 0 过滤，
    就会出现「JSON 里有这一类、终端和 HTML 里没有」——同一份数据三种说法。
    """
    from nastool.collect import PlatformFacts

    checks = [
        _c("storage.capacity", Status.PASS, category="storage", weight=4),
        _c("ai.hardware", Status.PASS, category="ai", weight=3),
    ]
    r = Report()
    r.meta = ReportMeta(generated_at="t", hostname="h", version="0.3.3",
                        fingerprint="fp", profile="verify")
    r.platform = PlatformFacts()
    r.checks = checks
    r.score, r.coverage = compute(checks, get_profile("verify"))

    ai_cat = next(c for c in r.score.categories if c.category == "ai")
    assert ai_cat.weight == 0
    assert ai_cat.score == 100          # 判定了就不该是 None

    text = TerminalReporter(color=False).render(r)
    assert "AI 算力" in text
    assert "仅展示" in text

    html = HTMLReporter().build(r)
    assert "AI 算力" in html
    assert "仅展示" in html
