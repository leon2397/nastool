"""
reporters/json_reporter.py — JSON 结构化报告输出
用于程序化处理或导出到文件
"""

import json
import datetime
from dataclasses import asdict


def _dict(obj) -> dict:
    """将 dataclass 递归转 dict（处理嵌套 list）"""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _dict(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, list):
        return [_dict(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _dict(v) for k, v in obj.items()}
    return obj


class JSONReporter:
    """输出结构化 JSON 报告"""

    def __init__(self):
        self.data = {}

    def build(
        self, device_rpt, storage_rpt, network_rpt, ai_rpt, adapter_rpt, all_ok: bool
    ) -> dict:
        self.data = {
            "report_version": "1.0",
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall_pass": all_ok,
            "device": _dict(device_rpt),
            "storage": _dict(storage_rpt),
            "network": _dict(network_rpt),
            "ai_accelerator": _dict(ai_rpt),
            "adapter": _dict(adapter_rpt) if adapter_rpt else {},
        }
        return self.data

    def dumps(self, indent: int = 2) -> str:
        return json.dumps(self.data, ensure_ascii=False, indent=indent)

    def dump(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def summary(self) -> str:
        """摘要一行，用于快速查看"""
        parts = []
        for key in ["device", "storage", "network", "ai_accelerator"]:
            sub = self.data.get(key, {})
            if isinstance(sub, dict):
                parts.append(f"{key}={'ok' if sub.get('ok') else 'fail'}")
        return " | ".join(parts)
