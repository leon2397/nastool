"""
Progress Bar Module for nastool

Provides real-time progress feedback during diagnostics.

Usage:
    from utils.progress import ProgressBar, ProgressTracker

    tracker = ProgressTracker(total=28, desc="Running diagnostics")
    for check in checks:
        result = run_check(check)
        tracker.update(check.id, result.severity)
    tracker.finish()
"""

import sys
import time
from typing import Optional, List
from enum import Enum


class CheckStatus(Enum):
    """Check status for progress display"""

    OK = "✅"
    WARNING = "⚠️"
    CRITICAL = "❌"
    SKIPPED = "⏭️"
    RUNNING = "🔄"


class ProgressBar:
    """
    ASCII progress bar with percentage and status.

    Example:
        [████████████░░░░░░░░] 60% | Running: disk_space
    """

    def __init__(self, width: int = 40):
        self.width = width

    def render(self, current: int, total: int, status: str = "") -> str:
        """Render progress bar string"""
        if total == 0:
            return ""

        percent = current / total
        filled = int(self.width * percent)
        empty = self.width - filled

        bar = "█" * filled + "░" * empty
        percent_str = f"{int(percent * 100):3d}%"

        if status:
            return f"[{bar}] {percent_str} | {status}"
        return f"[{bar}] {percent_str}"

    def print(self, current: int, total: int, status: str = "") -> None:
        """Print progress bar to stderr (overwrites current line)"""
        bar = self.render(current, total, status)
        sys.stderr.write(f"\r{bar}")
        sys.stderr.flush()


class ProgressTracker:
    """
    Track diagnostic progress with real-time updates.

    Features:
    - Progress bar with percentage
    - Current check name
    - Result status (OK/WARNING/CRITICAL)
    - Final summary

    Example output:
        🔍 Running diagnostics...

        [1/28] System: Python version...              ✅ OK
        [2/28] System: pip installed...               ✅ OK
        [3/28] System: Memory check...                ⚠️ WARN (85% used)
        [4/28] Network: DNS resolve...                ✅ OK
        ...

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        📊 Health Score: 85/100
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """

    def __init__(
        self, total: int, desc: str = "Running diagnostics", show_progress_bar: bool = True
    ):
        self.total = total
        self.desc = desc
        self.show_progress_bar = show_progress_bar
        self.current = 0
        self.results: List[dict] = []
        self.start_time = time.time()
        self.progressBar = ProgressBar(width=40)

        # Category tracking
        self.categories: dict = {}
        self.current_category = ""

    def start(self) -> None:
        """Print start message"""
        print(f"\n🔍 {self.desc}...\n")

    def update(
        self, check_id: str, status: CheckStatus, message: str = "", category: str = ""
    ) -> None:
        """
        Update progress with check result.

        Args:
            check_id: Check identifier (e.g., "python_version")
            status: Check status (OK/WARNING/CRITICAL/SKIPPED/RUNNING)
            message: Optional message (e.g., "85% used")
            category: Check category (e.g., "system", "network")
        """
        self.current += 1

        # Track by category
        if category:
            self.current_category = category
            if category not in self.categories:
                self.categories[category] = {"ok": 0, "warning": 0, "critical": 0, "skipped": 0}
            if status == CheckStatus.OK:
                self.categories[category]["ok"] += 1
            elif status == CheckStatus.WARNING:
                self.categories[category]["warning"] += 1
            elif status == CheckStatus.CRITICAL:
                self.categories[category]["critical"] += 1
            elif status == CheckStatus.SKIPPED:
                self.categories[category]["skipped"] += 1

        # Store result
        self.results.append(
            {"check_id": check_id, "status": status, "message": message, "category": category}
        )

        # Print status line
        self._print_status(check_id, status, message, category)

        # Update progress bar if enabled
        if self.show_progress_bar and sys.stderr.isatty():
            self.progressBar.print(self.current, self.total, f"{check_id}...")

    def _print_status(
        self, check_id: str, status: CheckStatus, message: str, category: str
    ) -> None:
        """Print status line with alignment"""
        # Format: [1/28] System: disk_space...           ✅ OK
        prefix = f"[{self.current}/{self.total}]"
        if category:
            prefix += f" {category.title()}:"

        # Check ID with padding
        check_display = check_id.replace("_", " ").title()
        check_str = f"{prefix} {check_display}..."

        # Pad to 45 characters for alignment
        check_str = check_str.ljust(45)

        # Status message
        if message:
            status_msg = f"{status.value} {status.name} ({message})"
        else:
            status_msg = f"{status.value} {status.name}"

        # Print (clear progress bar first if using stderr)
        if self.show_progress_bar and sys.stderr.isatty():
            sys.stderr.write("\r" + " " * 80 + "\r")
            sys.stderr.flush()

        print(f"  {check_str}{status_msg}")

    def finish(self, score: Optional[int] = None) -> dict:
        """
        Print final summary and return statistics.

        Args:
            score: Optional health score (0-100)

        Returns:
            dict with statistics
        """
        elapsed = time.time() - self.start_time

        # Clear progress bar
        if self.show_progress_bar and sys.stderr.isatty():
            sys.stderr.write("\r" + " " * 80 + "\r")
            sys.stderr.flush()

        # Print separator
        print()
        print("━" * 50)

        # Health score
        if score is not None:
            if score >= 90:
                emoji = "✅"
                status = "Excellent"
            elif score >= 70:
                emoji = "✅"
                status = "Good"
            elif score >= 50:
                emoji = "⚠️"
                status = "Warning"
            else:
                emoji = "❌"
                status = "Critical"

            print(f"📊 Health Score: {score}/100 {emoji} {status}")
        else:
            print(f"📊 Completed: {self.current}/{self.total} checks")

        print("━" * 50)

        # Category summary
        if self.categories:
            print()
            print("📋 By Category:")
            for cat, stats in sorted(self.categories.items()):
                total_cat = stats["ok"] + stats["warning"] + stats["critical"] + stats["skipped"]
                ok_pct = (stats["ok"] / total_cat * 100) if total_cat > 0 else 0
                print(
                    f"  {cat.title():12} {ok_pct:5.1f}% OK ({stats['warning']} warn, {stats['critical']} crit)"
                )

        # Time
        print()
        print(f"⏱️  Completed in {elapsed:.1f}s")

        # Return statistics
        return {
            "total": self.total,
            "completed": self.current,
            "elapsed_seconds": elapsed,
            "categories": self.categories,
            "score": score,
        }

    def print_error(self, error: Exception) -> None:
        """Print error message"""
        if self.show_progress_bar and sys.stderr.isatty():
            sys.stderr.write("\r" + " " * 80 + "\r")
            sys.stderr.flush()
        print(f"\n❌ Error: {error}")

    def print_warning(self, message: str) -> None:
        """Print warning message"""
        if self.show_progress_bar and sys.stderr.isatty():
            sys.stderr.write("\r" + " " * 80 + "\r")
            sys.stderr.flush()
        print(f"⚠️  Warning: {message}")


def create_tracker(total: int, desc: str = "Running diagnostics") -> ProgressTracker:
    """Factory function to create progress tracker"""
    return ProgressTracker(total=total, desc=desc)
