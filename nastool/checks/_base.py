"""
checks/_base.py — 检查项编写辅助

每个检查项返回一个 dict（由引擎补上 id/title/category/weight），
这样写一项检查只需要关心"判什么、看到什么、建议什么"，不重复样板。

    @check("storage.capacity", "数据盘容量", "storage", weight=3)
    def capacity(ctx):
        if not ctx.storage.target_total_gb:
            return R(Status.UNKNOWN, "无法读取容量")
        return R(Status.PASS, f"已用 {ctx.storage.target_use_percent}%",
                 evidence=[ev("shutil.disk_usage", "use_percent",
                              ctx.storage.target_use_percent,
                              num=ctx.storage.target_use_percent)])
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from ..model import Evidence, Status

__all__ = ["R", "ev", "Status"]


def R(status: Status,
      summary: str = "",
      detail: str = "",
      suggestion: str = "",
      evidence: Optional[Sequence[Evidence]] = None,
      confidence: Optional[float] = None,
      error: str = "") -> dict:
    """构造一条检查结果。confidence 留空由引擎按状态给默认值。"""
    return {
        "status": status,
        "summary": summary,
        "detail": detail,
        "suggestion": suggestion,
        "evidence": list(evidence or []),
        "confidence": confidence,
        "error": error,
    }


def ev(source: str, key: str, value, note: str = "",
       num: Optional[float] = None, trend: str = "") -> Evidence:
    """
    构造一条证据。

    数值型指标务必带 num；如果它的变化有明确好坏方向，再带 trend：
        trend="up_bad"   坏道数、错误计数、使用率
        trend="up_good"  剩余空间
    不确定方向就不要填，否则历史对比会出现"运行时长增加=恶化"这种噪音。
    """
    if num is None and isinstance(value, (int, float)) and not isinstance(value, bool):
        num = float(value)
    return Evidence(source=source, key=key, value=str(value), note=note,
                    num=num, trend=trend)
