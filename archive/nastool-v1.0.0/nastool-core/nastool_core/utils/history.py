"""
History Tracker Module for nastool

Track health score history and show trends.

Usage:
    from utils.history import HistoryTracker

    tracker = HistoryTracker()
    tracker.record(score=85, results=check_results)
    tracker.show_trend()
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .logger import get_logger
from .config import Config

logger = get_logger(__name__)


@dataclass
class HistoryEntry:
    """Single history entry"""

    timestamp: str
    score: int
    status: str
    checks_total: int
    checks_passed: int
    warnings: int
    critical: int
    profile: Optional[str] = None


class HistoryTracker:
    """
    Track and analyze health score history.

    Features:
    - Record diagnostic results
    - Show trend over time
    - Compare with previous runs
    - Export/Import history

    Example:
        tracker = HistoryTracker()
        tracker.record(score=85, results=results)
        trend = tracker.get_trend(days=7)
        tracker.print_trend()
    """

    MAX_ENTRIES = 100  # Maximum history entries to keep
    HISTORY_FILE = "history.json"

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize history tracker.

        Args:
            data_dir: Optional data directory path
        """
        self.data_dir = Path(data_dir or Config.DATA_DIR or ".")
        self.history_file = self.data_dir / self.HISTORY_FILE
        self.history: List[HistoryEntry] = []

        self._load()

    def _load(self) -> None:
        """Load history from file"""
        if not self.history_file.exists():
            logger.debug(f"History file not found: {self.history_file}")
            return

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.history = [HistoryEntry(**entry) for entry in data.get("entries", [])]

            logger.info(f"Loaded {len(self.history)} history entries")

        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            self.history = []

    def _save(self) -> None:
        """Save history to file"""
        # Create data directory if needed
        self.data_dir.mkdir(parents=True, exist_ok=True)

        try:
            data = {
                "version": "1.0",
                "entries": [
                    {
                        "timestamp": e.timestamp,
                        "score": e.score,
                        "status": e.status,
                        "checks_total": e.checks_total,
                        "checks_passed": e.checks_passed,
                        "warnings": e.warnings,
                        "critical": e.critical,
                        "profile": e.profile,
                    }
                    for e in self.history[-self.MAX_ENTRIES :]  # Keep last N entries
                ],
            }

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(self.history)} history entries")

        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def record(
        self, score: int, results: List[Any] = None, status: str = "healthy", profile: str = None
    ) -> HistoryEntry:
        """
        Record a diagnostic run.

        Args:
            score: Health score (0-100)
            results: Optional list of check results
            status: System status
            profile: Device profile used

        Returns:
            Created HistoryEntry
        """
        from nastool_core.checks import CheckSeverity

        # Calculate stats from results
        checks_total = len(results) if results else 0
        checks_passed = sum(1 for r in results if r.severity == CheckSeverity.PASSED) if results else 0
        warnings = sum(1 for r in results if r.severity == CheckSeverity.WARNING) if results else 0
        critical = sum(1 for r in results if r.severity == CheckSeverity.CRITICAL) if results else 0

        entry = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            score=score,
            status=status,
            checks_total=checks_total,
            checks_passed=checks_passed,
            warnings=warnings,
            critical=critical,
            profile=profile,
        )

        self.history.append(entry)
        self._save()

        logger.info(f"Recorded history entry: score={score}, status={status}")

        return entry

    def get_trend(self, days: int = 7) -> Dict[str, Any]:
        """
        Get trend analysis for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Trend data with scores, average, and trend direction
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        recent = [e for e in self.history if datetime.fromisoformat(e.timestamp) >= cutoff]

        if not recent:
            return {
                "days": days,
                "entries": 0,
                "average": None,
                "trend": "no_data",
                "scores": [],
            }

        scores = [e.score for e in recent]
        average = sum(scores) / len(scores)

        # Determine trend
        if len(scores) >= 2:
            first_half = sum(scores[: len(scores) // 2]) / (len(scores) // 2 or 1)
            second_half = sum(scores[len(scores) // 2 :]) / (len(scores) - len(scores) // 2 or 1)

            if second_half > first_half + 5:
                trend = "improving"
            elif second_half < first_half - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "days": days,
            "entries": len(recent),
            "average": round(average, 1),
            "trend": trend,
            "scores": scores,
            "min": min(scores),
            "max": max(scores),
        }

    def compare_last(self, score: int) -> Dict[str, Any]:
        """
        Compare current score with last run.

        Args:
            score: Current health score

        Returns:
            Comparison data
        """
        if not self.history:
            return {
                "has_previous": False,
                "current": score,
                "previous": None,
                "change": None,
            }

        last = self.history[-1]
        change = score - last.score

        return {
            "has_previous": True,
            "current": score,
            "previous": last.score,
            "change": change,
            "previous_time": last.timestamp,
        }

    def print_trend(self, days: int = 7) -> None:
        """Print trend report to console"""
        trend = self.get_trend(days)

        print("\n" + "=" * 50)
        print(f"📈 Health Trend (Last {days} Days)")
        print("=" * 50)

        if trend["entries"] == 0:
            print("\nNo history data available.")
            print("Run diagnostics regularly to build history.")
            return

        # Average score
        print(f"\n📊 Average Score: {trend['average']}/100")

        # Trend direction
        trend_icons = {
            "improving": "📈",
            "declining": "📉",
            "stable": "->",
            "insufficient_data": "❓",
        }
        icon = trend_icons.get(trend["trend"], "❓")

        print(f"{icon} Trend: {trend['trend'].upper()}")

        # Range
        print(f"📊 Range: {trend['min']} - {trend['max']}")

        # Recent scores
        scores = trend["scores"]
        if len(scores) > 0:
            print(f"\nRecent Scores:")

            # Simple ASCII chart
            max_score = max(scores)
            for i, score in enumerate(scores[-10:]):  # Last 10 entries
                bar_len = int(score / 5)  # Scale to 20 chars max
                bar = "█" * bar_len + "░" * (20 - bar_len)
                print(f"  [{i + 1:2d}] {bar} {score}")

        print("\n" + "=" * 50)

    def print_comparison(self, score: int) -> None:
        """Print comparison with last run"""
        comparison = self.compare_last(score)

        if not comparison["has_previous"]:
            print("\nℹ No previous run to compare.")
            return

        change = comparison["change"]

        if change > 0:
            icon = "📈"
            msg = f"improved by {change} points"
        elif change < 0:
            icon = "📉"
            msg = f"declined by {abs(change)} points"
        else:
            icon = "->"
            msg = "no change"

        print(f"\n{icon} Compared to last run: {msg}")
        print(f"   Previous: {comparison['previous']}/100")
        print(f"   Current:  {comparison['current']}/100")
        print(f"   Last run: {comparison['previous_time']}")

    def clear(self) -> None:
        """Clear history"""
        self.history = []
        self._save()
        logger.info("History cleared")


def show_history(days: int = 7) -> None:
    """Convenience function to show history"""
    tracker = HistoryTracker()
    tracker.print_trend(days)


if __name__ == "__main__":
    # Standalone history viewer
    import argparse

    parser = argparse.ArgumentParser(description="View health history")
    parser.add_argument("--days", type=int, default=7, help="Days to show")
    parser.add_argument("--clear", action="store_true", help="Clear history")
    args = parser.parse_args()

    tracker = HistoryTracker()

    if args.clear:
        tracker.clear()
        print("[OK] History cleared")
    else:
        tracker.print_trend(args.days)
