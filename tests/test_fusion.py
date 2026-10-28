"""
多源数据融合与一致性验证的测试

对应 DEBT-001。核心要锁住的行为：
  - 温度取最高值而非平均值（安全保守）
  - 同一测量点多来源矛盾要被识别出来
  - 不同测量点的温差**不能**被误报成矛盾
  - 矛盾时降低置信度，但不隐藏矛盾
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nastool.checks.system import thermal
from nastool.collect.device import ThermalInfo
from nastool.fusion import (
    ConsistencyResult,
    FusionMethod,
    SourceValue,
    fuse,
    normalize_point,
    validate,
)
from nastool.model import Status


# ── 替身 ────────────────────────────────────────────────────
class _Ctx:
    """温度判定用的最小上下文替身。"""

    def __init__(self, thermals, warn=75.0, crit=85.0):
        self.device = type("D", (), {"thermals": thermals})()
        self._warn, self._crit = warn, crit

    def thermal_limits(self):
        return (self._warn, self._crit)

    def chip_hint(self):
        return "generic"


def _t(zone, temp, ztype, source):
    return ThermalInfo(zone=zone, temp_c=temp, zone_type=ztype, source=source)


# ── 融合方法 ────────────────────────────────────────────────
def test_fuse_weighted_average():
    vals = [SourceValue("a", 40.0, weight=1.0), SourceValue("b", 60.0, weight=3.0)]
    r = fuse(vals, method=FusionMethod.WEIGHTED_AVERAGE)
    assert r.value == 55.0
    assert set(r.sources_used) == {"a", "b"}


def test_fuse_median_ignores_outlier():
    vals = [SourceValue("a", 10.0), SourceValue("b", 12.0), SourceValue("c", 90.0)]
    r = fuse(vals, method=FusionMethod.MEDIAN)
    assert r.value == 12.0


def test_fuse_majority_vote():
    vals = [SourceValue("a", 1.0), SourceValue("b", 1.0), SourceValue("c", 2.0)]
    r = fuse(vals, method=FusionMethod.MAJORITY_VOTE)
    assert r.value == 1.0


def test_fuse_trusted_source_prefers_trusted():
    vals = [SourceValue("sysfs", 50.0, weight=1.0),
            SourceValue("api", 60.0, weight=1.0, trusted=True)]
    r = fuse(vals, method=FusionMethod.TRUSTED_SOURCE)
    assert r.value == 60.0


def test_fuse_max_takes_worst_not_average():
    """温度必须取最高值——平均会低估散热风险。"""
    vals = [SourceValue("soc", 45.0), SourceValue("hotspot", 60.0)]
    r = fuse(vals, method=FusionMethod.MAX)
    assert r.value == 60.0
    assert r.value != fuse(vals, method=FusionMethod.WEIGHTED_AVERAGE).value


def test_fuse_no_usable_source_returns_none():
    r = fuse([SourceValue("a", 10.0, available=False)])
    assert r.value is None
    assert r.ok is False


def test_fuse_single_source_has_lower_confidence():
    one = fuse([SourceValue("a", 45.0)])
    two = fuse([SourceValue("a", 45.0), SourceValue("b", 46.0)])
    assert one.confidence < two.confidence


# ── 一致性验证 ──────────────────────────────────────────────
def test_validate_consistent_within_tolerance():
    c = validate([SourceValue("hwmon", 45.0), SourceValue("tz", 47.0)], key="temp_c")
    assert c.consistent is True
    assert c.spread == 2.0


def test_validate_detects_conflict():
    """DEBT-001 的核心场景：两个来源差 15°C。"""
    c = validate([SourceValue("hwmon", 45.0), SourceValue("tz", 60.0)], key="temp_c")
    assert c.consistent is False
    assert c.spread == 15.0
    assert c.tolerance == 5.0


def test_validate_two_sources_do_not_name_outliers():
    """只有两个来源时无法认定谁是错的，不能标离群。"""
    c = validate([SourceValue("hwmon", 45.0), SourceValue("tz", 60.0)], key="temp_c")
    assert c.outliers == []


def test_validate_three_sources_can_name_outlier():
    c = validate([SourceValue("a", 45.0), SourceValue("b", 46.0),
                  SourceValue("c", 90.0)], key="temp_c")
    assert c.consistent is False
    assert c.outliers == ["c"]


def test_validate_single_source_is_trivially_consistent():
    c = validate([SourceValue("a", 45.0)], key="temp_c")
    assert c.consistent is True
    assert "单一来源" in c.summary()


def test_validate_conflict_lowers_fusion_confidence():
    conflict = fuse([SourceValue("a", 45.0), SourceValue("b", 60.0)], tolerance=5.0)
    agree = fuse([SourceValue("a", 45.0), SourceValue("b", 46.0)], tolerance=5.0)
    assert conflict.confidence < agree.confidence


# ── 测量点归一化 ────────────────────────────────────────────
def test_normalize_point_aliases():
    assert normalize_point("cpu") == "cpu"
    assert normalize_point("soc") == "cpu"
    assert normalize_point("cpu-thermal") == "cpu"
    assert normalize_point("soc_thermal") == "cpu"
    assert normalize_point("x86_pkg_temp") == "cpu"
    assert normalize_point("gpu") == "gpu"


def test_normalize_point_keeps_unknown_distinct():
    """未知测量点不能被强行归到一起，否则会误报矛盾。"""
    assert normalize_point("weird_sensor") != normalize_point("other_sensor")


# ── 温度判定的端到端行为 ────────────────────────────────────
def test_thermal_single_source_passes():
    r = thermal(_Ctx([_t("hwmon/0", 45.0, "cpu", "hwmon")]))
    assert r["status"] is Status.PASS


def test_thermal_uses_max_not_average():
    """45 与 70 不同测量点时，报的是 70 而不是平均值。"""
    r = thermal(_Ctx([_t("hwmon/0", 45.0, "cpu", "hwmon"),
                      _t("hwmon/1", 70.0, "gpu", "hwmon")]))
    assert "70.0" in r["summary"]
    assert "57" not in r["summary"]


def test_thermal_same_point_conflict_is_flagged():
    """同一测量点两来源差 15°C → WARN，列出两个来源，置信度下降。"""
    r = thermal(_Ctx([_t("hwmon/0", 45.0, "cpu", "hwmon"),
                      _t("thermal_zone0", 60.0, "cpu-thermal", "thermal_zone")]))
    assert r["status"] is Status.WARN
    assert "争议" in r["summary"]
    assert "hwmon" in r["detail"]
    assert "thermal_zone" in r["detail"]
    assert r["confidence"] <= 0.5


def test_thermal_different_points_not_flagged_as_conflict():
    """CPU 45 + GPU 70 不是矛盾——测量点归一化必须正确。"""
    r = thermal(_Ctx([_t("hwmon/0", 45.0, "cpu", "hwmon"),
                      _t("hwmon/1", 70.0, "gpu", "hwmon")]))
    assert r["status"] is Status.PASS
    assert "争议" not in r["summary"]


def test_thermal_conflict_plus_overheat_is_fail():
    """既有分歧又确实过热 → FAIL（安全优先），但仍保留分歧信息。"""
    r = thermal(_Ctx([_t("hwmon/0", 80.0, "cpu", "hwmon"),
                      _t("thermal_zone0", 95.0, "cpu-thermal", "thermal_zone")],
                     warn=75.0, crit=85.0))
    assert r["status"] is Status.FAIL
    assert "争议" in r["summary"]


def test_thermal_consistent_sources_mention_cross_validation():
    r = thermal(_Ctx([_t("hwmon/0", 45.0, "cpu", "hwmon"),
                      _t("thermal_zone0", 47.0, "cpu-thermal", "thermal_zone")]))
    assert r["status"] is Status.PASS
    assert "交叉验证" in r["summary"]


# ── 低置信度在报告中可见 ────────────────────────────────────
def test_low_confidence_check_is_flagged_in_all_reporters():
    """融合分歧会降低置信度，用户必须能在报告里看到这件事。"""
    from nastool.collect import PlatformFacts
    from nastool.model import CheckResult, Report, ReportMeta
    from nastool.profiles import get_profile
    from nastool.reporters.html_reporter import HTMLReporter
    from nastool.reporters.terminal import TerminalReporter
    from nastool.scoring import compute

    checks = [
        CheckResult(id="system.thermal", title="温度", category="system",
                    status=Status.WARN, weight=3, confidence=0.5,
                    summary="最高温度 60.0°C，但温度读数存在争议"),
        CheckResult(id="system.uptime", title="运行时长", category="system",
                    status=Status.PASS, weight=1, confidence=0.95,
                    summary="运行 100 小时"),
    ]
    r = Report()
    r.meta = ReportMeta(generated_at="t", hostname="h", version="0.3.3",
                        fingerprint="fp", profile="nas")
    r.platform = PlatformFacts()
    r.checks = checks
    r.score, r.coverage = compute(checks, get_profile("nas"))

    text = TerminalReporter(color=False).render(r)
    assert "结论存疑" in text
    assert "0.50" in text

    html = HTMLReporter().build(r)
    assert "结论存疑" in html


def test_high_confidence_check_is_not_flagged():
    """正常项不该被无端标成存疑——否则这个标记就失去意义。"""
    from nastool.collect import PlatformFacts
    from nastool.model import CheckResult, Report, ReportMeta
    from nastool.profiles import get_profile
    from nastool.reporters.terminal import TerminalReporter
    from nastool.scoring import compute

    checks = [CheckResult(id="system.uptime", title="运行时长", category="system",
                          status=Status.PASS, weight=1, confidence=0.95,
                          summary="运行 100 小时")]
    r = Report()
    r.meta = ReportMeta(generated_at="t", hostname="h", version="0.3.3",
                        fingerprint="fp", profile="nas")
    r.platform = PlatformFacts()
    r.checks = checks
    r.score, r.coverage = compute(checks, get_profile("nas"))

    assert "结论存疑" not in TerminalReporter(color=False).render(r)
