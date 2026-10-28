"""
nastool/history.py — 检测历史（SQLite）

单次报告只是快照，两次报告才有趋势。

库里存的是完整报告 JSON（而不是拆开的指标），原因是：
  - 未来新增检查项时，老记录仍然可读
  - diff 可以直接在任意两个历史版本之间做，不依赖当前代码
  - report_version 字段保证格式演进可控
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".nastool", "history.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT    NOT NULL,
    hostname     TEXT    DEFAULT '',
    fingerprint  TEXT    DEFAULT '',
    profile      TEXT    DEFAULT '',
    score        INTEGER,
    grade        TEXT    DEFAULT '',
    confidence   REAL    DEFAULT 0,
    judged       INTEGER DEFAULT 0,
    total        INTEGER DEFAULT 0,
    version      TEXT    DEFAULT '',
    report_json  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_host_ts ON runs(hostname, ts DESC);
"""


@dataclass
class RunRow:
    id: int
    ts: str
    hostname: str
    profile: str
    score: Optional[int]
    grade: str
    confidence: float
    judged: int
    total: int
    version: str

    def to_dict(self) -> dict:
        return {
            "id": self.id, "ts": self.ts, "hostname": self.hostname,
            "profile": self.profile, "score": self.score, "grade": self.grade,
            "confidence": self.confidence, "judged": self.judged,
            "total": self.total, "version": self.version,
        }


class HistoryStore:
    def __init__(self, path: str = DEFAULT_DB):
        self.path = path
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ── 写入 ────────────────────────────────────────────────
    def save(self, report) -> int:
        data = report.to_dict()
        meta = data["meta"]
        score = data["score"]
        cov = data["coverage"]
        cur = self._conn.execute(
            "INSERT INTO runs (ts, hostname, fingerprint, profile, score, grade,"
            " confidence, judged, total, version, report_json)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                meta.get("generated_at", ""), meta.get("hostname", ""),
                meta.get("fingerprint", ""), meta.get("profile", ""),
                score.get("total"), score.get("grade", ""),
                score.get("confidence", 0.0),
                cov.get("judged", 0), cov.get("total", 0),
                meta.get("version", ""),
                json.dumps(data, ensure_ascii=False),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    # ── 查询 ────────────────────────────────────────────────
    def list(self, hostname: str = "", limit: int = 20) -> List[RunRow]:
        if hostname:
            rows = self._conn.execute(
                "SELECT id,ts,hostname,profile,score,grade,confidence,judged,total,version"
                " FROM runs WHERE hostname=? ORDER BY id DESC LIMIT ?",
                (hostname, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id,ts,hostname,profile,score,grade,confidence,judged,total,version"
                " FROM runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [RunRow(**dict(r)) for r in rows]

    def latest_id(self, hostname: str = "") -> Optional[int]:
        rows = self.list(hostname=hostname, limit=1)
        return rows[0].id if rows else None

    def load(self, run_id: Optional[int] = None,
             hostname: str = "") -> Optional[Dict[str, Any]]:
        """读取一份完整报告 JSON。run_id 为空时取最近一次。"""
        if run_id is None:
            run_id = self.latest_id(hostname)
            if run_id is None:
                return None
        row = self._conn.execute(
            "SELECT report_json FROM runs WHERE id=?", (run_id,)
        ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["report_json"])
        except (ValueError, TypeError):
            return None

    # ── 维护 ────────────────────────────────────────────────
    def prune(self, keep_days: int = 365) -> int:
        """删除超过 keep_days 天的记录；返回删除条数。"""
        cur = self._conn.execute(
            "DELETE FROM runs WHERE julianday('now') - julianday(ts) > ?",
            (keep_days,),
        )
        self._conn.commit()
        return cur.rowcount or 0

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False
