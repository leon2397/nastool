"""
Smart Summary Output for nastool

Provides intelligent, user-friendly summary of diagnostic results.

Features:
- One-sentence conclusion at top
- Only shows issues that need attention
- Actionable recommendations
- Clear visual hierarchy
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from logger import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Overall health status"""

    EXCELLENT = "excellent"  # All checks passed, no issues
    GOOD = "good"  # Minor issues, not critical
    WARNING = "warning"  # Some issues need attention
    CRITICAL = "critical"  # Serious issues need immediate action


@dataclass
class SummaryItem:
    """Single summary item"""

    category: str  # e.g., "CPU", "Memory", "Disk"
    status: str  # "ok", "warning", "error"
    message: str  # User-friendly message
    suggestion: Optional[str] = None  # What to do about it
    priority: int = 0  # Higher = more important


class SmartSummary:
    """
    Intelligent summary generator for diagnostic results.

    Usage:
        summary = SmartSummary()
        summary.add("CPU", "ok", "CPU 使用率 35%")
        summary.add("Disk", "warning", "磁盘剩余 15%", "清理旧文件")

        print(summary.generate())
    """

    def __init__(self):
        self.items: List[SummaryItem] = []
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = 0
        self.warning_checks = 0

    def add(
        self, category: str, status: str, message: str, suggestion: str = None, priority: int = 0
    ):
        """Add a summary item"""
        self.items.append(
            SummaryItem(
                category=category,
                status=status,
                message=message,
                suggestion=suggestion,
                priority=priority,
            )
        )

        self.total_checks += 1

        if status == "ok":
            self.passed_checks += 1
        elif status == "warning":
            self.warning_checks += 1
        else:
            self.failed_checks += 1

    def get_overall_status(self) -> HealthStatus:
        """Determine overall health status"""
        if self.failed_checks > 0:
            return HealthStatus.CRITICAL
        elif self.warning_checks > 3:
            return HealthStatus.WARNING
        elif self.warning_checks > 0:
            return HealthStatus.GOOD
        else:
            return HealthStatus.EXCELLENT

    def get_one_sentence_summary(self) -> str:
        """Generate one-sentence summary"""
        status = self.get_overall_status()

        if status == HealthStatus.EXCELLENT:
            return "🎉 设备健康！所有检查通过"

        elif status == HealthStatus.GOOD:
            return f"✅ 设备整体良好，{self.warning_checks} 个小问题可优化"

        elif status == HealthStatus.WARNING:
            return f"⚠️ 设备状态一般，{self.warning_checks} 个问题需要关注"

        else:  # CRITICAL
            return f"❌ 设备需要维护，{self.failed_checks} 个严重问题待处理"

    def generate(self, verbose: bool = False) -> str:
        """
        Generate formatted summary output.

        Args:
            verbose: If True, show all items; if False, only show issues

        Returns:
            Formatted string for display
        """
        lines = []

        # 1. One-sentence conclusion
        lines.append("=" * 50)
        lines.append(self.get_one_sentence_summary())
        lines.append("=" * 50)
        lines.append("")

        # 2. Issues that need attention (sorted by priority)
        issues = [item for item in self.items if item.status != "ok"]
        issues.sort(key=lambda x: x.priority, reverse=True)

        if issues:
            lines.append("📋 需要关注的问题：")
            lines.append("")

            for i, item in enumerate(issues, 1):
                icon = "❌" if item.status == "error" else "⚠️"
                lines.append(f"  {i}. {icon} {item.category}: {item.message}")

                if item.suggestion:
                    lines.append(f"     💡 建议：{item.suggestion}")
                lines.append("")

        # 3. Quick stats (if verbose or all passed)
        if verbose or not issues:
            lines.append("📊 检查统计：")
            lines.append(f"  总检查项：{self.total_checks}")
            lines.append(f"  ✅ 通过：{self.passed_checks}")
            if self.warning_checks > 0:
                lines.append(f"  ⚠️ 警告：{self.warning_checks}")
            if self.failed_checks > 0:
                lines.append(f"  ❌ 失败：{self.failed_checks}")
            lines.append("")

        # 4. Next steps
        if issues:
            lines.append("🚀 下一步：")
            if self.failed_checks > 0:
                lines.append("  运行 python arm_diagnose.py --fix 自动修复")
            else:
                lines.append("  运行 python arm_diagnose.py --fix 查看修复建议")

        return "\n".join(lines)

    def generate_html(self) -> str:
        """Generate HTML summary for web/report"""
        status = self.get_overall_status()
        status_colors = {
            HealthStatus.EXCELLENT: "#28a745",
            HealthStatus.GOOD: "#17a2b8",
            HealthStatus.WARNING: "#ffc107",
            HealthStatus.CRITICAL: "#dc3545",
        }

        html = f"""
<div style="font-family: sans-serif; max-width: 800px; margin: 0 auto;">
    <div style="background: {status_colors[status]}; color: white; padding: 20px; border-radius: 10px; text-align: center;">
        <h1 style="margin: 0;">{self.get_one_sentence_summary()}</h1>
    </div>
    
    <div style="margin-top: 20px;">
"""

        issues = [item for item in self.items if item.status != "ok"]
        issues.sort(key=lambda x: x.priority, reverse=True)

        if issues:
            html += "<h2>需要关注的问题</h2>"
            for item in issues:
                icon = "❌" if item.status == "error" else "⚠️"
                html += f"""
        <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid {status_colors[status]};">
            <strong>{icon} {item.category}</strong>: {item.message}
            {f"<br><small>💡 {item.suggestion}</small>" if item.suggestion else ""}
        </div>
"""

        html += """
    </div>
</div>
"""
        return html


# Convenience function
def create_summary(results: Dict[str, Any]) -> SmartSummary:
    """
    Create summary from check results.

    Args:
        results: Dict with category -> {status, message, suggestion}

    Returns:
        SmartSummary instance
    """
    summary = SmartSummary()

    for category, data in results.items():
        summary.add(
            category=category,
            status=data.get("status", "ok"),
            message=data.get("message", ""),
            suggestion=data.get("suggestion"),
            priority=data.get("priority", 0),
        )

    return summary


if __name__ == "__main__":
    # Demo
    summary = SmartSummary()

    # Add some checks
    summary.add("CPU", "ok", "CPU 使用率 35%", priority=5)
    summary.add("Memory", "ok", "内存使用率 45%", priority=5)
    summary.add("Disk", "warning", "磁盘剩余 15%", "清理旧文件或扩容", priority=8)
    summary.add("Network", "ok", "网络延迟 5ms", priority=3)
    summary.add("AI", "error", "未检测到 GPU", "安装 CUDA 驱动", priority=10)

    print(summary.generate())
    print()
    print("HTML 版本：")
    print(summary.generate_html()[:500] + "...")
