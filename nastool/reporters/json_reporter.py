"""
nastool/reporters/json_reporter.py — 结构化 JSON 报告

JSON 是这个产品对外最重要的接口：上报、历史库、二次分析、CI 判定都靠它。
所以格式必须稳定，`meta.report_version` 是向后兼容的契约。

结构（v3.0）：
    meta          工具版本、场景、时间、指纹
    score         总分 / 等级 / 分类得分 / 置信度 / 是否封顶
    coverage      覆盖了多少项、多少项不可判定
    checks[]      逐项结论（含证据与置信度）—— 真正的价值在这里
    platform      平台识别结果
    facts         设备清单（展示用，非判定依据）
    collect_errors 采集器自身失败（不影响判定，但要如实记录）
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


class JSONReporter:
    def build(self, report) -> Dict[str, Any]:
        """把 Report 转成可序列化的 dict。"""
        return report.to_dict()

    def dumps(self, report, indent: int = 2) -> str:
        return json.dumps(self.build(report), ensure_ascii=False, indent=indent)

    def dump(self, report, path: str, indent: int = 2) -> str:
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.dumps(report, indent=indent))
        return path

    # ── 便捷读取（历史 / diff 用）───────────────────────────
    @staticmethod
    def load(path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None
