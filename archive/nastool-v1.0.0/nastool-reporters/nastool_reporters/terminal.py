# -*- coding: utf-8 -*-
"""
reporters/terminal.py - v5.0.2 Terminal Reporter

Integrated terminology translation + weighted scoring + category display
"""

import sys
import io
from typing import List
from nastool_core.checks.base import CheckSummary, CheckResult, CheckSeverity, CheckCategory
from nastool_core.utils.terminology import translate_result, translate_category
from nastool_core.utils.health_scorer import calculate_health_score, score_color


def _fix_stdout_encoding():
    """Fix Windows GBK console: reconfigure stdout to UTF-8 if needed."""
    if sys.platform == "win32" and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, io.UnsupportedOperation):
            # Fallback: wrap with UTF-8 TextIOWrapper
            try:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            except (AttributeError, io.UnsupportedOperation):
                pass  # Can't fix, best effort


# Auto-fix on import
_fix_stdout_encoding()


class TerminalReporter:
    """v5.0.2 Terminal Reporter - User-friendly perspective"""

    W = 64  # Width

    # ANSI colors
    C = {
        "reset":   "\033[0m",
        "bold":    "\033[1m",
        "red":     "\033[91m",
        "green":   "\033[92m",
        "yellow":  "\033[93m",
        "cyan":    "\033[96m",
        "magenta": "\033[95m",
        "white":   "\033[97m",
        "gray":    "\033[90m",
    }

    def __init__(self, use_color: bool = True, use_emoji: bool = None):
        """
        Initialize reporter.
        
        Args:
            use_color: Whether to use ANSI colors (default: True)
            use_emoji: Whether to use emoji. Auto-detected if None.
        """
        # Handle color
        self.use_color = use_color
        if not use_color:
            # Disable colors by setting all to empty string
            self.C = {k: "" for k in self.C}
        
        # Handle emoji (auto-detect on Windows)
        if use_emoji is None:
            import sys
            self.use_emoji = sys.platform != "win32" and sys.stdout.encoding == "utf-8"
        else:
            self.use_emoji = use_emoji

    def _col(self, text: str, color: str) -> str:
        return f"{self.C.get(color, '')}{text}{self.C['reset']}"

    def _sev_icon(self, sev: CheckSeverity, passed: bool) -> str:
        if passed and sev == CheckSeverity.PASSED:
            return "[OK]"
        icons = {
            CheckSeverity.PASSED:  "[OK]",
            CheckSeverity.INFO:     "[i]" if not self.use_emoji else "i",
            CheckSeverity.WARNING:  "[!]",
            CheckSeverity.CRITICAL:"[X]",
        }
        return icons.get(sev, "[?]")

    def _sev_color(self, sev: CheckSeverity, passed: bool) -> str:
        if passed and sev == CheckSeverity.PASSED:
            return "green"
        colors = {
            CheckSeverity.PASSED:  "green",
            CheckSeverity.INFO:     "cyan",
            CheckSeverity.WARNING: "yellow",
            CheckSeverity.CRITICAL: "red",
        }
        return colors.get(sev, "white")

    def print_report(self, results: List[CheckResult]):
        """Print full diagnostic report (v5.0.2)"""
        # 1. Calculate weighted score
        report = calculate_health_score(results)
        sc = score_color(report.overall_score)
        color_map = {
            "green":  "green",
            "cyan":   "cyan",
            "yellow": "yellow",
            "magenta":"magenta",
            "red":    "red",
        }
        sc_c = color_map.get(sc, "green")

        # 2. Score banner
        self._print_score_banner(report, sc_c)

        # 3. Category scores
        self._print_category_scores(report, color_map)

        # 4. Category details
        self._print_by_category(results, color_map)

        # 5. Suggestions summary
        self._print_suggestions(results)

    def _print_score_banner(self, report, sc_c: str):
        """Score banner"""
        emoji = "[*]"
        info_icon = "[i]"
        print()
        print(self._col("+" + "-" * self.W + "+", "gray"))
        # Line 1: Score + Grade
        grade_line = f"  {emoji} Health Score  {report.overall_score} / 100      Grade {report.grade()}  {report.level_label}"
        print(self._col("|", "gray") + self._col(grade_line.center(self.W) + "  ", sc_c) + self._col("|", "gray"))
        # Line 2: Stats
        stats = f"  [OK] {report.total_passed} Passed    [!] {report.total_warnings} Warning    [X] {report.total_critical} Critical    {info_icon} {report.total_info} Info"
        print(self._col("|", "gray") + self._col(stats.center(self.W) + "  ", "gray") + self._col("|", "gray"))
        print(self._col("+" + "-" * self.W + "+", "gray"))
        print()

    def _print_category_scores(self, report, color_map):
        """Category scores in one line"""
        cat_items = []
        for cat_score in report.category_scores:
            sc = score_color(cat_score.score)
            c = color_map.get(sc, "white")
            name = translate_category(cat_score.category)  # Use .category attribute
            # Get short name after prefix
            short_name = name.split(" ", 1)[-1] if " " in name else name
            badge = f"{self._col(short_name, c)} {cat_score.score}"
            cat_items.append(badge)
        print(f"  Category Scores: {'    '.join(cat_items)}")
        print()

    def _print_by_category(self, results: List[CheckResult], color_map):
        """Print all checks by category"""
        # Group by category
        by_cat = {}
        for r in results:
            by_cat.setdefault(r.category, []).append(r)

        for cat, items in by_cat.items():
            cat_name = translate_category(cat)
            # Category header
            print()
            print(self._col("--- ", "gray") + self._col(cat_name, "bold") + self._col(" " + "-" * (self.W - len(cat_name) - 4) + " ", "gray"))

            # Print problem items first (WARNING + CRITICAL)
            bad = [r for r in items if not r.passed and r.severity not in (CheckSeverity.INFO,)]
            for r in bad:
                t = translate_result(r)
                icon = self._sev_icon(r.severity, r.passed)
                color = self._sev_color(r.severity, r.passed)
                title = t.get("friendly_title", r.title)
                msg = t.get("friendly_message", r.message)
                line = f"{icon} {title}: {msg}"
                print(self._col(f"  {line}", color))
                if r.fix_description:
                    print(self._col(f"     -> Fix: {r.fix_description}", "gray"))

            # Then print passed items
            ok = [r for r in items if r.passed or r.severity == CheckSeverity.INFO]
            for r in ok:
                icon = self._sev_icon(r.severity, r.passed)
                color = self._sev_color(r.severity, r.passed)
                t = translate_result(r)
                title = t.get("friendly_title", r.title)
                line = f"{icon} {title}: {r.current}"
                print(self._col(f"  {line}", "gray"))

    def _print_suggestions(self, results: List[CheckResult]):
        """Print actionable suggestions"""
        failed = [r for r in results if not r.passed and r.severity != CheckSeverity.INFO]
        if not failed:
            print()
            print(self._col("[OK] System status is good.", "green"))
            return

        print()
        print(self._col("--- Suggestions  " + "-" * (self.W - 16), "yellow"))
        for r in failed[:5]:
            icon = "[!]" if r.severity.value in ("warning", "critical") else "[i]"
            color = "red" if r.severity.value == "critical" else "yellow"
            print()
            print(self._col(f"  {icon} {r.title}", color))
            print(self._col(f"     {r.message}", "gray"))

    # --- Legacy API compatibility ---

    def print_summary(self, summary):
        """Legacy API: forward CheckSummary to print_report"""
        self.print_report(summary.results)


def print_report(results: List[CheckResult], use_color: bool = True):
    """Convenience function: print report"""
    reporter = TerminalReporter(use_color=use_color)
    reporter.print_report(results)


def print_summary(summary: CheckSummary, use_color: bool = True):
    """Convenience function: print summary"""
    reporter = TerminalReporter(use_color=use_color)
    reporter.print_summary(summary)

