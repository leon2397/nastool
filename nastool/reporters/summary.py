"""
reporters/summary.py - One-line summary reporter
"""

from checks.base import CheckSummary


class SummaryReporter:
    """Generate one-line summary for user"""

    def generate(self, summary: CheckSummary) -> str:
        """Generate one-line summary"""
        if summary.score >= 90:
            status = "Excellent"
            emoji = "🌟"
        elif summary.score >= 75:
            status = "Good"
            emoji = "✅"
        elif summary.score >= 50:
            status = "Fair"
            emoji = "⚠️"
        else:
            status = "Poor"
            emoji = "❌"

        parts = []

        # Critical issues
        if summary.critical > 0:
            parts.append(f"{summary.critical} critical issue{'s' if summary.critical > 1 else ''}")

        # Warnings
        if summary.warnings > 0:
            parts.append(f"{summary.warnings} warning{'s' if summary.warnings > 1 else ''}")

        if parts:
            issues = ", ".join(parts)
            return f"{emoji} {status} ({summary.score}/100) - {issues}"
        else:
            return f"{emoji} {status} ({summary.score}/100) - All checks passed"

    def get_recommendation(self, summary: CheckSummary) -> str:
        """Get recommendation based on results"""
        if summary.critical > 0:
            return "Run with --fix to resolve critical issues before deploying NAS"
        elif summary.warnings > 0:
            return "Consider running --fix to address warnings for optimal performance"
        else:
            return "System ready for NAS deployment"
