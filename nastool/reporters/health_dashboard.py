"""
nastool/reporters/health_dashboard.py - Health Score Dashboard
v4.0.2 健康评分可视化仪表盘
"""

from checks.base import CheckSummary
from utils.health_scorer import calculate_health_score, score_color, HealthReport


class HealthDashboard:
    """彩色健康评分仪表盘输出器"""

    # ANSI 颜色
    C = {
        "reset":   "\033[0m",
        "bold":    "\033[1m",
        "dim":     "\033[2m",
        "red":     "\033[91m",
        "green":   "\033[92m",
        "yellow":  "\033[93m",
        "blue":    "\033[94m",
        "cyan":    "\033[96m",
        "magenta": "\033[95m",
        "white":   "\033[97m",
        "bg_green":   "\033[42m",
        "bg_red":     "\033[41m",
        "bg_yellow":  "\033[43m",
    }

    def print_dashboard(self, summary: CheckSummary, previous_score: int = None, compact: bool = False):
        """
        打印完整健康仪表盘

        compact=True  只打印综合评分（一行）
        """
        if compact:
            self._print_compact(summary)
            return

        report = summary.get_health_report(previous_score)
        width = 64

        # ── 标题 ──────────────────────────────────
        print()
        print(self._bar(width, "─"))
        print(f"  🍊  nastool  v4.0.2  健康评分")
        print(self._bar(width, "─"))

        # ── 综合评分区 ─────────────────────────────
        self._print_score_panel(report, width)

        # ── 分类评分条 ─────────────────────────────
        self._print_category_bars(report, width)

        # ── 问题列表 ───────────────────────────────
        self._print_issues(report, width)

        # ── 建议 ─────────────────────────────────
        self._print_recommendation(report, width)

        print(self._bar(width, "─"))

    def _print_compact(self, summary: CheckSummary):
        """紧凑输出：一行评分"""
        report = summary.get_health_report()
        color = score_color(report.overall_score)
        icon = "✅" if report.overall_score >= 80 else "⚠️" if report.overall_score >= 60 else "❌"
        print(f"{icon} 健康评分: {self._c(report.overall_score, color)}/100 "
              f"[{report.level_name}]  "
              f"✅{report.total_passed}  ⚠️{report.total_warnings}  ❌{report.total_critical}")

    def _print_score_panel(self, report: HealthReport, width: int):
        """打印评分面板"""
        color = score_color(report.overall_score)

        # 大数字评分
        score_str = f"{report.overall_score}"
        grade_str = f"Grade: {report.grade()}"
        level_str = report.level_label

        print()
        print(f"    {self._c(level_str, color)}")
        print(f"    {self._c(score_str, color)} {self._c('/100', 'dim')}   {grade_str}")
        print()

        # 进度条
        bar_filled, bar_color = self._make_bar(report.overall_score, width - 12)
        print(f"    [{self._c(bar_filled, bar_color)}{self._c('░' * (width - 12 - len(bar_filled)), 'dim')}]")
        print()

        # 统计
        stats_line = (
            f"  {self._c('✅', 'green')} {report.total_passed} 通过  "
            f"{self._c('⚠️', 'yellow')} {report.total_warnings} 警告  "
            f"{self._c('❌', 'red')} {report.total_critical} 严重  "
            f"{self._c('ℹ️', 'cyan')} {report.total_info} 信息"
        )
        print(stats_line)

        # 分数变化
        if report.previous_score is not None:
            delta = report.score_change
            if delta > 0:
                delta_str = f"  {self._c('↑ +' + str(delta), 'green')} vs上次"
            elif delta < 0:
                delta_str = f"  {self._c('↓ ' + str(delta), 'red')} vs上次"
            else:
                delta_str = f"  {self._c('→ 无变化', 'dim')} vs上次"
            print(delta_str)

    def _print_category_bars(self, report: HealthReport, width: int):
        """打印分类评分条"""
        print()
        print(f"  {self._c('📊 分类评分', 'bold')}")
        print(f"  {self._bar(width - 4, '─', indent=2)}")

        for cat in report.category_scores:
            bar_len = 24
            filled = int(round(cat.score / 100 * bar_len))
            bar_color = score_color(cat.score)

            # 分类标签
            cat_label = f"{cat.name:<8}"
            bar_str = f"[{self._c('█' * filled, bar_color)}{'░' * (bar_len - filled)}]"
            score_label = f" {cat.score:>3}/100"

            # 问题数量
            issue_info = ""
            if cat.critical > 0:
                issue_info = f"  ❌{cat.critical}"
            elif cat.warnings > 0:
                issue_info = f"  ⚠️{cat.warnings}"

            print(f"  {cat_label} {bar_str}{self._c(score_label, bar_color)}{issue_info}")

    def _print_issues(self, report: HealthReport, width: int):
        """打印问题列表"""
        if not report.critical_items:
            return

        print()
        print(f"  {self._c('🔴 紧急事项', 'red', bold=True)}")

        for i, item in enumerate(report.critical_items[:5], 1):
            title = f"[{i}] {item.title}"
            msg = self._truncate(item.message, width - 14)
            print(f"  {self._c('❌', 'red')} {self._c(title, 'red', bold=True)}")
            print(f"      {self._c(msg, 'dim')}")
            if item.fix_description:
                fix = self._truncate(f"   → {item.fix_description}", width - 4)
                print(f"  {self._c(fix, 'cyan')}")

    def _print_recommendation(self, report: HealthReport, width: int):
        """打印修复建议"""
        if report.total_critical > 0:
            msg = f"存在 {report.total_critical} 个紧急问题，请立即处理！"
            print(f"\n  💡 {self._c(msg, 'yellow', bold=True)}")
            print(f"     运行 python arm_diagnose.py --fix 进行自动修复")
        elif report.total_warnings > 0:
            msg = f"存在 {report.total_warnings} 个可优化项，建议处理"
            print(f"\n  💡 {self._c(msg, 'cyan')}")
            print(f"     运行 python arm_diagnose.py --fix 进行修复")
        else:
            print(f"\n  💡 {self._c('系统状态良好！🍊', 'green', bold=True)}")

    # ── 工具方法 ──────────────────────────────────────────

    def _bar(self, width: int, char: str, indent: int = 0) -> str:
        return " " * indent + char * width

    def _c(self, text: str, color: str, bold: bool = False) -> str:
        prefix = self.C.get("bold", "") if bold else ""
        return f"{prefix}{self.C.get(color, '')}{text}{self.C['reset']}"

    def _make_bar(self, score: int, width: int) -> tuple:
        """生成进度条字符串和颜色"""
        filled = int(round(score / 100 * width))
        if score >= 90: color = "green"
        elif score >= 80: color = "cyan"
        elif score >= 70: color = "yellow"
        elif score >= 60: color = "magenta"
        else: color = "red"
        return "█" * filled, color

    def _truncate(self, text: str, width: int) -> str:
        """截断超长文本"""
        if len(text) <= width:
            return text
        return text[:width - 1] + "…"

    def score_only(self, summary: CheckSummary) -> int:
        """直接返回评分数字（供脚本调用）"""
        return summary.get_health_report().overall_score
