"""
nastool/diff.py — 两份报告的逐项对比

为什么不能只看总分变化：
    "总分稳定在 88，但那块盘的重映射扇区从 0 涨到了 12"
    —— 这是最要命的情况，而总分 diff 完全看不出来。

所以这里的核心是**逐项 diff + 证据级 diff**：
  · 新增严重问题 / 已修复 / 仍然严重
  · 状态恶化 / 好转（含 WARN 级别）
  · 数值型证据的变化（坏道数、通电时长、可用空间、温度）
  · 检查项增删（工具版本升级导致）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .model import SEVERITY_ORDER, Status

# 变化类型严重度（越小越需要优先看）
KIND_ORDER = {
    "new_failure": 0,
    "still_failing": 1,
    "evidence_worsened": 2,
    "new_warning": 3,
    "improved": 4,
    "evidence_improved": 5,
    "evidence_changed": 6,
    "fixed": 7,
    "added": 8,
    "removed": 9,
    "unchanged": 10,
}

KIND_LABELS = {
    "new_failure": "新增严重问题",
    "still_failing": "仍然严重",
    "evidence_worsened": "指标恶化",
    "new_warning": "新增告警",
    "improved": "有所好转",
    "evidence_improved": "指标好转",
    "evidence_changed": "指标变化",
    "fixed": "已修复",
    "added": "本次新增检测项",
    "removed": "本次未检测",
    "unchanged": "无变化",
}


@dataclass
class EvidenceDelta:
    source: str = ""
    key: str = ""
    old: Optional[float] = None
    new: Optional[float] = None
    delta: Optional[float] = None

    def text(self) -> str:
        if self.old is None or self.new is None:
            return f"{self.key}: {self.old} → {self.new}"
        sign = "+" if (self.delta or 0) > 0 else ""
        return f"{self.key}: {_fmt(self.old)} → {_fmt(self.new)}（{sign}{_fmt(self.delta)}）"


def _fmt(v: Optional[float]) -> str:
    if v is None:
        return "-"
    if isinstance(v, float) and abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.1f}" if isinstance(v, float) else str(v)


@dataclass
class Change:
    check_id: str
    title: str
    category: str
    kind: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    note: str = ""
    evidence: List[EvidenceDelta] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "title": self.title,
            "category": self.category,
            "kind": self.kind,
            "label": KIND_LABELS.get(self.kind, self.kind),
            "old_status": self.old_status,
            "new_status": self.new_status,
            "note": self.note,
            "evidence": [
                {"source": e.source, "key": e.key, "old": e.old,
                 "new": e.new, "delta": e.delta, "text": e.text()}
                for e in self.evidence
            ],
        }


@dataclass
class DiffResult:
    old_ts: str = ""
    new_ts: str = ""
    old_score: Optional[int] = None
    new_score: Optional[int] = None
    old_grade: str = ""
    new_grade: str = ""
    old_hostname: str = ""
    new_hostname: str = ""
    old_judged: int = 0
    new_judged: int = 0
    changes: List[Change] = field(default_factory=list)

    def of_kind(self, *kinds: str) -> List[Change]:
        return [c for c in self.changes if c.kind in kinds]

    @property
    def significant(self) -> List[Change]:
        return [c for c in self.changes if c.kind not in ("unchanged",)]

    def has_regression(self) -> bool:
        return bool(self.of_kind("new_failure", "still_failing", "evidence_worsened"))

    def score_delta(self) -> Optional[int]:
        if self.old_score is None or self.new_score is None:
            return None
        return self.new_score - self.old_score

    def to_dict(self) -> dict:
        return {
            "old_ts": self.old_ts, "new_ts": self.new_ts,
            "old_score": self.old_score, "new_score": self.new_score,
            "old_grade": self.old_grade, "new_grade": self.new_grade,
            "score_delta": self.score_delta(),
            "regression": self.has_regression(),
            "changes": [c.to_dict() for c in self.significant],
        }


# ── 工具 ────────────────────────────────────────────────────
def _index_checks(report: Dict[str, Any]) -> Dict[str, dict]:
    out = {}
    for c in report.get("checks", []) or []:
        cid = c.get("id")
        if cid:
            out[cid] = c
    return out


def _numeric_evidence(check: dict) -> Dict[Tuple[str, str], Tuple[float, str]]:
    """返回 {(source, key): (数值, 趋势语义)}。

    趋势语义来自证据的 trend 字段：
        up_bad  上升=恶化   up_good 上升=好转   "" 中性（不参与好坏判断）
    """
    out: Dict[Tuple[str, str], Tuple[float, str]] = {}
    for ev in check.get("evidence", []) or []:
        num = ev.get("num")
        if isinstance(num, (int, float)):
            out[(ev.get("source", ""), ev.get("key", ""))] = (
                float(num), ev.get("trend", "") or "")
    return out


def _status(val: Optional[str]) -> Optional[Status]:
    if not val:
        return None
    try:
        return Status(val)
    except ValueError:
        return None


# ── 主入口 ──────────────────────────────────────────────────
def diff_reports(old: Dict[str, Any], new: Dict[str, Any]) -> DiffResult:
    """对比两份报告 dict（Report.to_dict() 或历史库里的 JSON）。"""
    old_meta = old.get("meta", {}) or {}
    new_meta = new.get("meta", {}) or {}
    old_score = (old.get("score", {}) or {})
    new_score = (new.get("score", {}) or {})
    old_cov = old.get("coverage", {}) or {}
    new_cov = new.get("coverage", {}) or {}

    result = DiffResult(
        old_ts=old_meta.get("generated_at", ""),
        new_ts=new_meta.get("generated_at", ""),
        old_score=old_score.get("total"),
        new_score=new_score.get("total"),
        old_grade=old_score.get("grade", ""),
        new_grade=new_score.get("grade", ""),
        old_hostname=old_meta.get("hostname", ""),
        new_hostname=new_meta.get("hostname", ""),
        old_judged=old_cov.get("judged", 0),
        new_judged=new_cov.get("judged", 0),
    )

    old_checks = _index_checks(old)
    new_checks = _index_checks(new)

    for cid, new_c in new_checks.items():
        old_c = old_checks.get(cid)
        new_status = _status(new_c.get("status"))
        title = new_c.get("title", cid)
        category = new_c.get("category", "")

        if old_c is None:
            result.changes.append(Change(
                check_id=cid, title=title, category=category, kind="added",
                new_status=new_c.get("status"), note="本次首次执行该检查项",
            ))
            continue

        old_status = _status(old_c.get("status"))

        # 证据级变化：只有标了趋势方向的指标才判断好坏，
        # 否则"运行时长 +0.1 小时"会被报成恶化。
        old_num = _numeric_evidence(old_c)
        new_num = _numeric_evidence(new_c)
        deltas: List[EvidenceDelta] = []
        worsened = False
        improved = False
        for key in sorted(set(old_num) & set(new_num)):
            ov, trend = old_num[key]
            nv = new_num[key][0]
            if ov == nv:
                continue
            dv = nv - ov
            deltas.append(EvidenceDelta(source=key[0], key=key[1],
                                        old=ov, new=nv, delta=dv))
            if trend == "up_bad":
                worsened = worsened or dv > 0
                improved = improved or dv < 0
            elif trend == "up_good":
                improved = improved or dv > 0
                worsened = worsened or dv < 0

        kind = "unchanged"
        note = ""

        if old_status and new_status:
            if new_status is Status.FAIL and old_status is not Status.FAIL:
                kind = "new_failure"
                note = f"{old_status.label} → 严重"
            elif old_status is Status.FAIL and new_status is not Status.FAIL:
                kind = "fixed" if new_status is Status.PASS else "improved"
                note = f"严重 → {new_status.label}"
            elif old_status is Status.FAIL and new_status is Status.FAIL:
                kind = "still_failing"
                note = "上次已严重，本次仍未处理"
            elif new_status is Status.WARN and old_status is Status.PASS:
                kind = "new_warning"
                note = "通过 → 告警"
            elif new_status is Status.PASS and old_status is Status.WARN:
                kind = "improved"
                note = "告警 → 通过"
            elif new_status is Status.UNKNOWN and old_status is not Status.UNKNOWN:
                kind = "removed"
                note = "由可判定变为不可判定"
            elif worsened:
                kind = "evidence_worsened"
            elif improved:
                kind = "evidence_improved"

        if kind == "unchanged" and deltas and old_status is new_status is Status.PASS:
            # 状态没变但指标在动（例如坏道从 0 涨到 2）——这正是最该看的
            if worsened:
                kind = "evidence_worsened"
            elif improved:
                kind = "evidence_improved"

        result.changes.append(Change(
            check_id=cid, title=title, category=category, kind=kind,
            old_status=old_status.value if old_status else None,
            new_status=new_status.value if new_status else None,
            note=note, evidence=deltas,
        ))

    for cid, old_c in old_checks.items():
        if cid not in new_checks:
            result.changes.append(Change(
                check_id=cid, title=old_c.get("title", cid),
                category=old_c.get("category", ""), kind="removed",
                old_status=old_c.get("status"),
                note="本次未执行该检查项（可能被 --skip 或依赖缺失）",
            ))

    result.changes.sort(key=lambda c: (KIND_ORDER.get(c.kind, 99), c.check_id))
    return result
