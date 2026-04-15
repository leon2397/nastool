# -*- coding: utf-8 -*-
"""
reporters/terminal.py - v5.0.2 Terminal Reporter

集成术语翻译 + 加权评分 + 分类展示
"""

from typing import List
from checks.base import CheckSummary, CheckResult, CheckSeverity, CheckCategory
from utils.terminology import translate_result, translate_category
from utils.health_scorer import calculate_health_score, score_color


class TerminalReporter:
    """v5.0.2 终端诊断报告器 — 普通人视角"""

    W = 64  # 宽度

    # ANSI 颜色
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

    def _col(self, text: str, color: str) -> str:
        return f"{self.C.get(color, '')}{text}{self.C['reset']}"

    def _sev_icon(self, sev: CheckSeverity, passed: bool) -> str:
        if passed and sev == CheckSeverity.PASSED:
            return "✅"
        icons = {
            CheckSeverity.PASSED:  "✅",
            CheckSeverity.INFO:     "ℹ️",
            CheckSeverity.WARNING:  "⚠️",
            CheckSeverity.CRITICAL:"❌",
        }
        return icons.get(sev, "❓")

    def _sev_color(self, sev: CheckSeverity, passed: bool) -> str:
        if passed and sev == CheckSeverity.PASSED:
            return "green"
        colors = {
            CheckSeverity.PASSED:  "green",
            CheckSeverity.INFO:     "cyan",
            CheckSeverity.WARNING:  "yellow",
            CheckSeverity.CRITICAL: "red",
        }
        return colors.get(sev, "white")

    def print_report(self, results: List[CheckResult]):
        """打印完整诊断报告（v5.0.2）"""
        # 1. 计算加权评分
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

        # 2. 评分横幅
        self._print_score_banner(report, sc_c)

        # 3. 分类评分
        self._print_category_scores(report, color_map)

        # 4. 分类详情
        self._print_by_category(results, color_map)

        # 5. 建议摘要
        self._print_suggestions(results)

    def _print_score_banner(self, report, sc_c: str):
        """评分横幅"""
        print()
        print(self._col("┌" + "─" * self.W + "┐", "gray"))
        # 第一行：分数 + 等级
        grade_line = f"  🍊 健康评分  {report.overall_score} / 100      Grade {report.grade()}  {report.level_label}"
        print(self._col("│", "gray") + self._col(grade_line.center(self.W) + "  ", sc_c) + self._col("│", "gray"))
        # 第二行：统计
        stats = f"  ✅ {report.total_passed} 通过    ⚠️ {report.total_warnings} 警告    ❌ {report.total_critical} 严重    ℹ️ {report.total_info} 提示"
        print(self._col("│", "gray") + self._col(stats.center(self.W) + "  ", "gray") + self._col("│", "gray"))
        print(self._col("└" + "─" * self.W + "┘", "gray"))
        print()

    def _print_category_scores(self, report, color_map):
        """分类评分一行"""
        cat_items = []
        for cat in report.category_scores:
            sc = score_color(cat.score)
            c = color_map.get(sc, "white")
            name = translate_category(cat.category)
            # 取 emoji 后面的中文
            short_name = name.split(" ", 1)[-1] if " " in name else name
            badge = f"{self._col(short_name, c)} {cat.score}"
            cat_items.append(badge)
        print(f"  分类评分：{'    '.join(cat_items)}")
        print()

    def _print_by_category(self, results: List[CheckResult], color_map):
        """按类别打印所有检测项"""
        # 分组
        by_cat = {}
        for r in results:
            by_cat.setdefault(r.category, []).append(r)

        for cat, items in by_cat.items():
            cat_name = translate_category(cat)
            # 分类标题
            print()
            print(self._col("━━━ ", "gray") + self._col(cat_name, "bold") + self._col(" " + "━" * (self.W - len(cat_name) - 4) + " ", "gray"))

            # 先打印问题项（WARNING + CRITICAL）
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
                    print(self._col(f"     → 修复：{r.fix_description}", "gray"))

            # 再打印通过项
            ok = [r for r in items if r.passed or r.severity == CheckSeverity.INFO]
            for r in ok:
                icon = self._sev_icon(r.severity, r.passed)
                color = self._sev_color(r.severity, r.passed)
                t = translate_result(r)
                title = t.get("friendly_title", r.title)
                line = f"{icon} {title}: {r.current}"
                print(self._col(f"  {line}", "gray"))

    def _print_suggestions(self, results: List[CheckResult]):
        """打印建议摘要"""
        from utils.terminology import generate_suggestions
        suggestions = generate_suggestions(results)
        urgent = [s for s in suggestions if s["urgency"] in ("now", "soon")]

        if not urgent:
            print()
            print(self._col("✅ 系统状态良好，暂无需紧急处理的问题。", "green"))
            return

        print()
        print(self._col("━━━ 建议处理  " + "━" * (self.W - 12), "yellow"))
        for s in urgent[:5]:
            icon = "🔴" if s["urgency"] == "now" else "🟡"
            color = "red" if s["urgency"] == "now" else "yellow"
            print()
            print(self._col(f"  {icon} {s['title']}", color))
            print(self._col(f"     问题：{s['problem']}", "gray"))
            print(self._col(f"     原因：{s['why_matters']}", "gray"))
            print(self._col(f"     操作：{s['action']}", "gray"))

    # ─── 以下为兼容旧 API ───────────────────────────────

    def print_summary(self, summary):
        """兼容旧 API：将 CheckSummary 转发到 print_report"""
        self.print_report(summary.results)
