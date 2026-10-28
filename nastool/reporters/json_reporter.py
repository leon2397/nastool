"""
reporters/json_reporter.py — 结构化 JSON 报告

字段稳定、可直接给自动化流水线消费：
  overall  一句话结论（含分数与等级）
  platform / device / storage / network / services / ai_accelerator  各模块原始数据
  score    分项得分与问题清单
"""
import datetime
import json
from dataclasses import asdict, is_dataclass

REPORT_VERSION = "2.0"


def _plain(obj):
    """dataclass / list / dict 递归转纯 JSON 类型。"""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _plain(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_plain(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


class JSONReporter:
    def __init__(self):
        self.data = {}

    def build(self, result) -> dict:
        s = result.score
        findings = [asdict(f) for f in s.findings]
        self.data = {
            "report_version": REPORT_VERSION,
            "tool": {"name": "nastool", "version": result.meta.version},
            "generated_at": result.meta.generated_at
            or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration_s": result.meta.duration_s,
            "hostname": result.meta.hostname,
            "platform_summary": result.meta.platform_summary,
            "options": result.meta.options,
            "overall": {
                "pass": result.overall_ok,
                "score": s.total,
                "grade": s.grade,
                "verdict": s.verdict,
                "critical_count": len([f for f in s.findings if f.level == "critical"]),
                "warning_count": len([f for f in s.findings if f.level == "warning"]),
            },
            "score": {
                "total": s.total,
                "grade": s.grade,
                "categories": [asdict(c) for c in s.categories],
                "findings": findings,
                "ai_score": s.ai_score,
                "ai_note": s.ai_note,
            },
            "platform": _plain(result.platform),
            "device": _plain(result.device),
            "storage": _plain(result.storage),
            "network": _plain(result.network),
            "services": _plain(result.services),
            "ai_accelerator": _plain(result.ai),
            "adapter": _plain(result.adapter) if result.adapter else {},
        }
        return self.data

    def dumps(self, indent: int = 2) -> str:
        return json.dumps(self.data, ensure_ascii=False, indent=indent)

    def dump(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def summary(self) -> str:
        o = self.data.get("overall", {})
        return f"{o.get('score')}/100 {o.get('grade')} 级 — {o.get('verdict')}"
