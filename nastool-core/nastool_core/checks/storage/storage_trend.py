from typing import Optional
"""
checks/storage/storage_trend.py - Storage space trend check
检测存储空间使用趋势，识别快速增长趋势
"""

import os
import time
import subprocess
import json
from pathlib import Path
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class StorageTrendCheck(Check):
    """Check storage space usage trend"""

    check_id = "storage_trend"
    title = "存储空间趋势"
    description = "监测存储空间使用率变化趋势，预测何时用满"
    category = CheckCategory.STORAGE

    # 记录文件（保存在本地目录）
    STATE_DIR = Path.home() / ".nastool"
    STATE_FILE = STATE_DIR / "storage_trend.json"
    # 趋势警告阈值：每日增长 > 5%
    TREND_WARNING = 5.0  # percent per day
    TREND_CRITICAL = 10.0  # percent per day

    def run(self) -> CheckResult:
        """Run storage trend check"""
        # 获取当前磁盘使用率
        current = self._get_disk_usage("/")
        if current is None:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="无法获取磁盘使用信息",
                current="未知",
                expected="正常",
            ))

        used_percent = current["used_percent"]

        # 加载历史数据
        history = self._load_history()
        trend = self._calculate_trend(history, current)

        # 更新历史记录
        self._save_history(history, current)

        if trend is None:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="趋势数据不足，需要 2 天以上数据才能计算趋势",
                current=f"当前 {used_percent:.1f}% 已用",
                expected="存储趋势正常",
                details={"history_days": len(history)},
            ))

        # 趋势判断
        daily_rate = trend["daily_rate"]
        days_to_full = trend["days_to_full"]
        trend_status = trend["trend"]

        if trend_status == "critical":
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"存储快速增长！每日约 +{daily_rate:.1f}%，预计 {days_to_full:.0f} 天后用满",
                current=f"{used_percent:.1f}% 已用",
                expected=f"每日增长 < {self.TREND_WARNING}%",
                fix_available=True,
                fix_description=f"存储空间增长较快，建议立即清理：{self._cleanup_suggestion(current)}",
                details={
                    "trend": trend_status,
                    "daily_rate_pct": daily_rate,
                    "days_to_full": days_to_full,
                    "current_pct": used_percent,
                },
            )

        if trend_status == "warning":
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"存储使用率上升（每日 +{daily_rate:.1f}%），预计 {days_to_full:.0f} 天后用满",
                current=f"{used_percent:.1f}% 已用",
                expected=f"每日增长 < {self.TREND_WARNING}%",
                details={
                    "trend": trend_status,
                    "daily_rate_pct": daily_rate,
                    "days_to_full": days_to_full,
                },
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"存储趋势稳定（每日约 +{daily_rate:.1f}%）",
            current=f"{used_percent:.1f}% 已用",
            expected=f"每日增长 < {self.TREND_WARNING}%",
            details={
                "trend": "stable",
                "daily_rate_pct": daily_rate,
                "days_to_full": days_to_full,
            },
        )

    def _get_disk_usage(self, path: str) -> Optional[dict]:
        """Get disk usage for given path"""
        try:
            import shutil
            stat = shutil.disk_usage(path)
            total = stat.total / (1024**3)
            used = stat.used / (1024**3)
            free = stat.free / (1024**3)
            used_percent = (stat.used / stat.total) * 100
            return {
                "total_gb": total,
                "used_gb": used,
                "free_gb": free,
                "used_percent": used_percent,
                "timestamp": int(time.time()),
            }
        except Exception:
            return None

    def _load_history(self) -> list:
        """Load historical usage data"""
        try:
            if self.STATE_FILE.exists():
                with open(self.STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("history", [])
        except Exception:
            pass
        return []

    def _save_history(self, history: list, current: dict) -> None:
        """Save current usage to history"""
        # 去重（同一天只保留最新）
        today = time.strftime("%Y-%m-%d")
        history = [h for h in history if h.get("date") != today]
        history.append({
            "date": today,
            "used_percent": current["used_percent"],
            "free_gb": current["free_gb"],
            "timestamp": current["timestamp"],
        })
        # 保留最多 30 天
        history = history[-30:]

        try:
            self.STATE_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"history": history, "updated": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _calculate_trend(self, history: list, current: dict) -> Optional[dict]:
        """Calculate daily growth rate from history"""
        if len(history) < 2:
            return None

        # 按时间排序
        points = [(h["used_percent"], h["timestamp"]) for h in history]
        points.append((current["used_percent"], current["timestamp"]))
        points.sort(key=lambda x: x[1])

        first_pct, first_ts = points[0]
        last_pct, last_ts = points[-1]

        days = (last_ts - first_ts) / 86400
        if days < 1:
            return None

        daily_rate = (last_pct - first_pct) / days

        # 预测多少天用满（以100%计）
        if daily_rate <= 0:
            days_to_full = 9999
        else:
            remaining = 100 - last_pct
            days_to_full = remaining / daily_rate if daily_rate > 0 else 9999

        trend = "stable"
        if daily_rate >= self.TREND_CRITICAL:
            trend = "critical"
        elif daily_rate >= self.TREND_WARNING:
            trend = "warning"

        return {
            "daily_rate": daily_rate,
            "days_to_full": days_to_full,
            "trend": trend,
            "history_points": len(points),
        }

    def _cleanup_suggestion(self, current: dict) -> str:
        """Generate cleanup suggestion"""
        suggestions = []
        if current["free_gb"] < 5:
            suggestions.append("清理 Docker 镜像（docker system prune -a）")
            suggestions.append("清理日志文件（find /var/log -name '*.gz' -delete）")
        if current["free_gb"] < 20:
            suggestions.append("清理旧文件或考虑扩容")
        return "；".join(suggestions) if suggestions else "清理旧文件或扩容"
