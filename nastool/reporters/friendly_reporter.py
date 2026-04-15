# -*- coding: utf-8 -*-
"""
nastool/reporters/friendly_reporter.py - P2 普通人视角报告器

生成通俗易懂的健康报告：
- 术语翻译（工程师语言 → 普通人语言）
- 行动导向（每个问题都有具体操作步骤）
- 可视化评分（健康仪表盘）
- 无技术背景也能看懂
"""

import datetime
from typing import List, Optional

from checks.base import CheckResult, CheckSeverity, CheckCategory
from utils.terminology import (
    translate_result,
    translate_category,
    generate_suggestions,
)
from utils.health_scorer import calculate_health_score, HealthReport


class FriendlyReporter:
    """生成普通人能看懂的诊断报告"""

    # HTML 模板（深色主题 + 健康仪表盘）
    _TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🍊 NAS 体检报告 - {device_name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
         background: #0a0e1a; color: #e8eaf0; font-size: 15px; line-height: 1.6;
         padding: 20px; }}
  .wrap {{ max-width: 900px; margin: 0 auto; }}

  /* 顶部评分卡 */
  .score-card {{
    background: linear-gradient(135deg, #111827 0%, #1e2a3a 100%);
    border-radius: 20px; padding: 32px 28px; margin-bottom: 24px;
    border: 1px solid {score_border_color}; text-align: center;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  }}
  .score-num {{ font-size: 5rem; font-weight: 700; line-height: 1;
                color: {score_color}; letter-spacing: -4px; }}
  .score-grade {{ font-size: 1.2rem; color: {score_color}; margin: 8px 0 4px;
                  font-weight: 600; letter-spacing: 2px; }}
  .score-label {{ font-size: .95rem; color: #888; margin-bottom: 20px; }}
  .score-bar-wrap {{ background: #1a2235; border-radius: 8px; height: 10px;
                     overflow: hidden; margin: 16px 20px; }}
  .score-bar {{ height: 100%; border-radius: 8px; background: {score_color};
                width: {score_pct}%; transition: width .6s ease; }}
  .score-summary {{ font-size: .9rem; color: #aab; margin-top: 12px; }}

  /* 分类评分 */
  .cats {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 16px 0; }}
  .cat-badge {{ flex: 1; min-width: 120px; background: #111827; border-radius: 10px;
                padding: 10px 12px; border: 1px solid #1e2a3a; }}
  .cat-name {{ font-size: .78rem; color: #888; margin-bottom: 4px; }}
  .cat-score {{ font-size: 1.4rem; font-weight: 700; color: {score_color}; }}
  .cat-detail {{ font-size: .72rem; color: #666; }}
  .cat-bar-wrap {{ background: #1a2235; border-radius: 3px; height: 4px; margin-top: 4px; }}
  .cat-bar {{ height: 100%; border-radius: 3px; width: {cat_pct}%; }}

  /* 紧急建议区 */
  .urgent {{ background: #1a0a0a; border-left: 4px solid #f87171;
             border-radius: 0 10px 10px 0; padding: 16px 20px; margin-bottom: 20px; }}
  .urgent h3 {{ color: #f87171; font-size: 1rem; margin-bottom: 10px; }}
  .urgent h3::before {{ content: "🔴  "; }}
  .suggestion {{ background: #111827; border-radius: 10px; padding: 14px 18px;
                 margin-bottom: 10px; border: 1px solid #1e2a3a; }}
  .sug-title {{ font-weight: 600; color: {score_color}; margin-bottom: 4px; font-size: .95rem; }}
  .sug-problem {{ color: #c9a; font-size: .85rem; margin-bottom: 8px; }}
  .sug-why {{ color: #777; font-size: .8rem; padding-left: 12px; border-left: 2px solid #333;
               margin-bottom: 8px; }}
  .sug-action {{ background: #0d1420; border-radius: 6px; padding: 8px 12px;
                 font-size: .83rem; color: #8bc; line-height: 1.5; }}
  .sug-action strong {{ color: #6db; }}
  .sug-risk {{ display: inline-block; padding: 1px 8px; border-radius: 10px;
               font-size: .72rem; margin-top: 6px; }}

  /* 分类详情 */
  .cat-section {{ margin-bottom: 20px; }}
  .cat-header {{ display: flex; align-items: center; gap: 8px; padding: 10px 0;
                 border-bottom: 1px solid #1e2a3a; margin-bottom: 10px; }}
  .cat-header h2 {{ font-size: 1rem; color: #c9d; }}
  .cat-count {{ font-size: .78rem; color: #666; }}
  .check-item {{ background: #111827; border-radius: 8px; padding: 10px 14px;
                 margin-bottom: 8px; border-left: 3px solid {check_border}; }}
  .check-title {{ font-size: .88rem; color: #d0d; margin-bottom: 2px; }}
  .check-msg {{ font-size: .83rem; color: #8ab; }}
  .check-fix {{ background: #0d1f12; border-radius: 4px; padding: 6px 10px;
                font-size: .8rem; color: #4ade80; margin-top: 6px; }}
  .check-ok {{ border-left-color: #4ade80; }}
  .check-ok .check-title {{ color: #4ade80; }}
  .check-ok .check-msg {{ color: #6b8; }}

  /* 页脚 */
  .footer {{ text-align: center; color: #444; font-size: .78rem;
             margin-top: 32px; padding-top: 16px; border-top: 1px solid #1a2235; }}
  .footer a {{ color: #556; text-decoration: none; }}

  /* 打印友好 */
  @media print {{
    body {{ background: #fff; color: #222; }}
    .score-card, .suggestion, .check-item {{ border-color: #ddd; background: #f9f9f9; }}
    .score-num {{ color: #222; }}
  }}
</style>
</head>
<body>
<div class="wrap">

  <!-- 评分卡 -->
  <div class="score-card">
    <div class="score-num">{score}</div>
    <div class="score-grade">Grade {grade}</div>
    <div class="score-label">{level_name} · {total_checks} 项检测</div>
    <div class="score-bar-wrap"><div class="score-bar"></div></div>
    <div class="score-summary">
      ✅ {passed} 通过 &nbsp; ⚠️ {warnings} 警告 &nbsp; ❌ {critical} 严重
    </div>
    <div class="cats">{cat_badges}</div>
  </div>

  <!-- 紧急建议 -->
  {urgent_suggestions}

  <!-- 全部分类详情 -->
  {cat_sections}

  <div class="footer">
    🍊 nastools v4.0.2 · AI-NAS 健康体检报告<br>
    生成时间：{generated_at} &nbsp;·&nbsp;
    <a href="https://github.com/nastool">项目主页</a>
  </div>
</div>
</body>
</html>"""  # noqa: E501

    def __init__(self):
        self._cat_colors = {
            CheckCategory.STORAGE:  "#60a5fa",
            CheckCategory.SYSTEM:    "#a78bfa",
            CheckCategory.NETWORK:   "#34d399",
            CheckCategory.AI:        "#fbbf24",
            CheckCategory.SECURITY:  "#f87171",
            CheckCategory.NAS:       "#fb923c",
        }

    def build_html(
        self,
        results: List[CheckResult],
        device_name: str = "NAS 设备",
        previous_score: Optional[int] = None,
    ) -> str:
        """生成完整的 HTML 报告"""
        # 计算评分
        report: HealthReport = calculate_health_score(results, previous_score)

        # 生成紧急建议
        urgent_html = self._build_urgent_section(results)

        # 生成分类评分徽章
        cat_badges_html = self._build_cat_badges(report)

        # 生成分类详情
        cat_sections_html = self._build_cat_sections(results)

        # 评分颜色
        sc = score_color(report.overall_score)
        color_map = {
            "green":  "#4ade80",
            "cyan":   "#22d3ee",
            "yellow": "#fbbf24",
            "magenta":"#f472b6",
            "red":    "#f87171",
        }
        sc_hex = color_map.get(sc, "#4ade80")
        sc_border = color_map.get(sc, "#4ade80")

        # 检查边框颜色（用于 check-item）
        check_border = sc_hex  # 严重项用评分色

        return self._TEMPLATE.format(
            device_name=device_name,
            score=report.overall_score,
            grade=report.grade(),
            level_name=report.level_name,
            score_border_color=sc_border,
            score_pct=report.overall_score,
            total_checks=report.total_checks,
            passed=report.total_passed,
            warnings=report.total_warnings,
            critical=report.total_critical,
            cat_badges=cat_badges_html,
            urgent_suggestions=urgent_html,
            cat_sections=cat_sections_html,
            generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            check_border=check_border,
            cat_pct="{cat_pct}",  # placeholder，_build_cat_badges 单独处理
        )

    def _build_urgent_section(self, results: List[CheckResult]) -> str:
        """生成紧急建议区（只看 CRITICAL 和 WARNING）"""
        suggestions = generate_suggestions(results)
        urgent = [s for s in suggestions if s["urgency"] in ("now", "soon")]

        if not urgent:
            return ""

        items_html = ""
        for s in urgent[:5]:  # 最多显示 5 条
            risk_cls = "color:#f87171" if s["urgency"] == "now" else "color:#fbbf24"
            risk_icon = "🔴" if s["urgency"] == "now" else "🟡"

            action_lines = self._format_action(s["action"])
            benefit = s.get("benefit", "")
            fix_line = (
                f'<div class="check-fix">💡 {s["fix_description"]}</div>'
                if s["fix_description"] and s["fix_available"]
                else ""
            )

            items_html += f"""
  <div class="suggestion">
    <div class="sug-title">{s["title"]}</div>
    <div class="sug-problem" style="{risk_cls}">{risk_icon} {s["problem"]}</div>
    <div class="sug-why">💡 {s["why_matters"]}</div>
    <div class="sug-action"><strong>操作步骤：</strong>{action_lines}</div>
    {fix_line}
    <span class="sug-risk" style="background:#1e2a3a; color:#888">
      操作风险：{s["risk"]}
    </span>
  </div>"""

        return f"""
  <div class="urgent">
    <h3>建议立即处理的问题</h3>
    {items_html}
  </div>"""

    def _format_action(self, action: str) -> str:
        """把操作步骤格式化（处理换行）"""
        lines = action.split("\n")
        return "<br>".join(f"{i+1}. {l.strip()}" if l.strip() else "" for i, l in enumerate(lines) if l.strip())

    def _build_cat_badges(self, report: HealthReport) -> str:
        """生成分类评分徽章"""
        badges = ""
        for cat in report.category_scores:
            color = self._cat_colors.get(cat.category, "#888")
            sc = score_color(cat.score)
            color_map = {
                "green": "#4ade80", "cyan": "#22d3ee",
                "yellow": "#fbbf24", "magenta": "#f472b6", "red": "#f87171",
            }
            score_color_hex = color_map.get(sc, "#888")
            cat_name = translate_category(cat.category).split(" ", 1)[-1]

            badges += f"""
    <div class="cat-badge">
      <div class="cat-name">{cat_name}</div>
      <div class="cat-score" style="color:{score_color_hex}">{cat.score}</div>
      <div class="cat-detail">✅{cat.passed} ⚠️{cat.warnings} ❌{cat.critical}</div>
      <div class="cat-bar-wrap">
        <div class="cat-bar" style="width:{cat.score}%;background:{score_color_hex}"></div>
      </div>
    </div>"""
        return badges

    def _build_cat_sections(self, results: List[CheckResult]) -> str:
        """生成每个分类的详细检查项列表"""
        # 按类别分组
        by_cat = {}
        for r in results:
            by_cat.setdefault(r.category, []).append(r)

        sections = ""
        for cat, items in by_cat.items():
            cat_label = translate_category(cat)
            ok_items = [r for r in items if r.passed or r.severity == CheckSeverity.INFO]
            bad_items = [r for r in items if not r.passed and r.severity != CheckSeverity.INFO]

            items_html = ""

            # 先显示问题项
            for r in bad_items:
                t = translate_result(r)
                fix_html = (
                    f'<div class="check-fix">💡 {r.fix_description or "可使用自动修复"}</div>'
                    if r.fix_available else ""
                )
                border_color = "#f87171" if r.severity == CheckSeverity.CRITICAL else "#fbbf24"
                items_html += f"""
    <div class="check-item" style="border-left-color:{border_color}">
      <div class="check-title">{t["friendly_title"]}</div>
      <div class="check-msg">{t["friendly_message"]}</div>
      {fix_html}
    </div>"""

            # 再显示正常项
            for r in ok_items:
                t = translate_result(r)
                items_html += f"""
    <div class="check-item check-ok">
      <div class="check-title">{t["friendly_title"]}</div>
      <div class="check-msg">{r.current}</div>
    </div>"""

            sections += f"""
  <div class="cat-section">
    <div class="cat-header">
      <h2>{cat_label}</h2>
      <span class="cat-count">{len(items)} 项检测</span>
    </div>
    {items_html}
  </div>"""

        return sections

    def save(self, html: str, path: str) -> None:
        """保存 HTML 报告"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    def build_compact_text(self, results: List[CheckResult]) -> str:
        """生成紧凑文字报告（用于终端一行摘要）"""
        from utils.health_scorer import calculate_health_score

        report = calculate_health_score(results)
        suggestions = generate_suggestions(results)
        urgent = [s for s in suggestions if s["urgency"] in ("now", "soon")]

        lines = [
            f"🍊 NAS 体检报告  {report.level_label} ({report.overall_score}/100) Grade {report.grade()}",
            f"   ✅ {report.total_passed} 通过  ⚠️ {report.total_warnings} 警告  ❌ {report.total_critical} 严重",
            "",
        ]

        if urgent:
            lines.append("🔴 建议处理：")
            for s in urgent[:3]:
                icon = "🔴" if s["urgency"] == "now" else "🟡"
                lines.append(f"  {icon} {s['title']}：{s['problem']}")
        else:
            lines.append("✅ 系统状态良好，无紧急问题")

        return "\n".join(lines)
