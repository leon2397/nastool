# -*- coding: utf-8 -*-
"""
utils/history.py — 检测历史存储与查询

功能：
1. 检测结果持久化到本地 JSON
2. 按设备 IP 分组存储
3. 支持查询历史记录
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Any


# ══════════════════════════════════════════════════════════════════
# 配置
# ══════════════════════════════════════════════════════════════════

# 历史存储目录（在 nastools_pkg/data/ 下）
# 使用绝对路径避免 __file__ 问题
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(_pkg_dir), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "detect_history.json")

# 保留最近 N 条记录
MAX_HISTORY_PER_DEVICE = 50
MAX_DEVICES = 20


# ══════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════


class DetectHistory:
    """检测历史记录"""

    def __init__(
        self, device_ip: str, results: List[Dict], timestamp: Optional[float] = None
    ):
        self.device_ip = device_ip
        self.results = results
        self.timestamp = timestamp or time.time()
        self.id = self._generate_id()

    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return f"{self.device_ip}_{int(self.timestamp * 1000)}"

    @property
    def datetime_str(self) -> str:
        """人类可读的时间字符串"""
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def summary(self) -> Dict[str, int]:
        """检测结果摘要"""
        passed = sum(1 for r in self.results if r.get("severity") == "passed")
        warn = sum(1 for r in self.results if r.get("severity") in ("warning", "warn"))
        crit = sum(1 for r in self.results if r.get("severity") == "critical")
        fixable = sum(1 for r in self.results if r.get("fix_id", ""))
        return {
            "passed": passed,
            "warning": warn,
            "critical": crit,
            "fixable": fixable,
            "total": len(self.results),
        }

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "id": self.id,
            "device_ip": self.device_ip,
            "timestamp": self.timestamp,
            "datetime": self.datetime_str,
            "summary": self.summary,
            "results": self.results,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "DetectHistory":
        """从字典反序列化"""
        return cls(
            device_ip=data["device_ip"],
            results=data["results"],
            timestamp=data["timestamp"],
        )


# ══════════════════════════════════════════════════════════════════
# 存储管理
# ══════════════════════════════════════════════════════════════════


class HistoryManager:
    """历史记录管理器"""

    def __init__(self, history_file: str = HISTORY_FILE):
        self.history_file = history_file
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

    def _load_all(self) -> Dict[str, List[Dict]]:
        """加载所有历史记录"""
        if not os.path.exists(self.history_file):
            return {}

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_all(self, data: Dict[str, List[Dict]]):
        """保存所有历史记录"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save(self, history: DetectHistory):
        """保存一条检测记录"""
        all_history = self._load_all()

        # 获取该设备的记录列表
        device_key = history.device_ip
        if device_key not in all_history:
            all_history[device_key] = []

        # 添加新记录
        all_history[device_key].append(history.to_dict())

        # 限制每个设备的记录数
        if len(all_history[device_key]) > MAX_HISTORY_PER_DEVICE:
            all_history[device_key] = all_history[device_key][-MAX_HISTORY_PER_DEVICE:]

        # 限制设备数
        if len(all_history) > MAX_DEVICES:
            # 按最近活动时间排序，保留最新的
            device_times = {}
            for ip, records in all_history.items():
                if records:
                    device_times[ip] = records[-1]["timestamp"]
            sorted_devices = sorted(
                device_times.items(), key=lambda x: x[1], reverse=True
            )
            keep_devices = [d[0] for d in sorted_devices[:MAX_DEVICES]]
            all_history = {k: v for k, v in all_history.items() if k in keep_devices}

        self._save_all(all_history)

    def get_device_history(
        self, device_ip: str, limit: int = 10
    ) -> List[DetectHistory]:
        """获取指定设备的历史记录"""
        all_history = self._load_all()

        if device_ip not in all_history:
            return []

        records = all_history[device_ip][-limit:]
        return [DetectHistory.from_dict(r) for r in reversed(records)]

    def get_all_devices(self) -> List[Dict]:
        """获取所有设备列表（含最近检测信息）"""
        all_history = self._load_all()

        devices = []
        for ip, records in all_history.items():
            if records:
                latest = records[-1]
                devices.append(
                    {
                        "ip": ip,
                        "last_detect": latest["datetime"],
                        "last_summary": latest["summary"],
                        "total_records": len(records),
                    }
                )

        # 按最近检测时间排序
        devices.sort(key=lambda x: x["last_detect"], reverse=True)
        return devices

    def get_record_by_id(self, record_id: str) -> Optional[DetectHistory]:
        """根据 ID 获取特定记录"""
        all_history = self._load_all()

        for ip, records in all_history.items():
            for record in records:
                if record["id"] == record_id:
                    return DetectHistory.from_dict(record)

        return None

    def delete_device_history(self, device_ip: str):
        """删除指定设备的所有历史"""
        all_history = self._load_all()

        if device_ip in all_history:
            del all_history[device_ip]
            self._save_all(all_history)

    def clear_all(self):
        """清空所有历史"""
        if os.path.exists(self.history_file):
            os.remove(self.history_file)


# ══════════════════════════════════════════════════════════════════
# 全局实例
# ══════════════════════════════════════════════════════════════════

_history_manager: Optional[HistoryManager] = None


def get_history_manager() -> HistoryManager:
    """获取历史管理器单例"""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager


def save_detect_history(device_ip: str, results: List[Dict]) -> DetectHistory:
    """保存检测历史（便捷函数）"""
    history = DetectHistory(device_ip, results)
    get_history_manager().save(history)
    return history


def get_device_history(device_ip: str, limit: int = 10) -> List[DetectHistory]:
    """获取设备历史（便捷函数）"""
    return get_history_manager().get_device_history(device_ip, limit)


def get_all_devices() -> List[Dict]:
    """获取所有设备（便捷函数）"""
    return get_history_manager().get_all_devices()
