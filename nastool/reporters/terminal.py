"""
nastool/reporters/terminal.py — 终端报告

信息层级按「结论 → 限制 → 明细 → 清单」组织，先给答案再给细节。

一个刻意的设计：**不可判定项会单独显示原因**。
      ? 硬盘 SMART 健康   缺少依赖：smartctl，本次未检测
  而不是悄悄跳过。用户必须知道"哪些没说清"，否则 100 分是骗人的。
"""
from __future__ import annotations

import textwrap
from typing import List

from ..model import (
    CATEGORY_NAMES,
    CATEGORY_ORDER,
    LOW_CONFIDENCE,
    CheckResult,
    Report,
    Status,
)

_COLORS = {
    "reset": "\033[0m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "grey": "\033[90m",
}

_STATUS_COLOR = {
    Status.PASS: "green",
    Status.WARN: "yellow",
    Status.FAIL: "red",
    Status.UNKNOWN: "blue",
    Status.SKIP: "grey",
}


class TerminalReporter:
    def __init__(self, verbose: bool = False, color: bool = True):
        self.verbose = verbose
        self.color = color
        self.lines: List[str] = []

    # ── 着色 ────────────────────────────────────────────────
    def _c(self, text: str, name: str) -> str:
        if not self.color:
            return text
        return f"{_COLORS.get(name, '')}{text}{_COLORS['reset']}"

    def _w(self, line: str = "") -> None:
        self.lines.append(line)

    # ── 最小宽度对齐（中文按 2 列算）────────────────────────
    @staticmethod
    def _width(text: str) -> int:
        return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)

    def _pad(self, text: str, width: int) -> str:
        gap = max(0, width - self._width(text))
        return text + " " * gap

    # ── 主体 ────────────────────────────────────────────────
    def render(self, report: Report) -> str:
        self.lines = []
        self._header(report)
        self._verdict(report)
        self._limitations(report)
        self._categories(report)
        self._details(report)
        if self.verbose:
            self._inventory(report)
        self._footer(report)
        return "\n".join(self.lines)

    def print(self, report: Report) -> None:  # noqa: A003 - 保持简单直观
        print(self.render(report))

    # ── 各段 ────────────────────────────────────────────────
    def _header(self, report: Report) -> None:
        meta = report.meta
        p = report.platform
        s = report.facts.storage if report.facts else None

        self._w()
        self._w("  " + self._c(f"nastool {meta.version}", "bold")
                + self._c(f"  ·  场景 {meta.profile}  ·  {meta.generated_at}", "dim"))
        self._w()

        vendor = " ".join(x for x in (getattr(p, "vendor", ""), getattr(p, "product", ""),
                                      getattr(p, "version", "")) if x)
        platform_line = vendor or getattr(p, "pretty_name", "") or meta.platform_summary
        model = getattr(p, "facts", {}).get("model", "")
        if model:
            platform_line += f"（{model}）"

        rows = [
            ("主机", meta.hostname or "未知"),
            ("平台", f"{platform_line}  ·  {getattr(p, 'arch', '')}  ·  "
                     f"内核 {getattr(p, 'kernel', '')}"),
        ]
        if s is not None:
            rows.append(("数据盘", f"{s.target_path}  ·  {s.target_free_gb} GB 可用 / "
                                   f"{s.target_total_gb} GB"))
        for label, value in rows:
            self._w(f"  {self._c(self._pad(label, 8), 'dim')}{value}")
        self._w()

    def _verdict(self, report: Report) -> None:
        sc = report.score
        cov = report.coverage

        total = "N/A" if sc.total is None else f"{sc.total}"
        grade = sc.grade
        grade_color = {"A": "green", "B": "green", "C": "yellow", "D": "red"}.get(grade, "grey")

        self._w(f"  {self._c(self._pad('结论', 8), 'dim')}"
                f"{self._c(total, 'bold')} 分 · {self._c(grade, grade_color)} 级 · {sc.verdict}")
        self._w(f"  {self._c(self._pad('覆盖', 8), 'dim')}"
                f"{cov.judged}/{cov.applicable} 项已判定（{cov.percent}%）"
                + (f"，{cov.unknown} 项不可判定" if cov.unknown else "")
                + (f"，{cov.skipped} 项不适用" if cov.skipped else ""))
        # 低置信项单独说明：这些结论存疑，其中 PASS 类不计入分数。
        # 不说清楚，用户会以为"分数算错了"。
        if cov.low_confidence:
            self._w(f"  {self._c(self._pad('', 8), 'dim')}"
                    f"{self._c(f'其中 {cov.low_confidence} 项结论存疑', 'magenta')}"
                    f"（{self._c('置信度不足，其中通过类未计入分数', 'dim')}）")
        self._w(f"  {self._c(self._pad('置信', 8), 'dim')}{sc.confidence:.2f}")

        if sc.capped and sc.cap_reason:
            self._w(f"  {self._c('!', 'red')} {self._c(sc.cap_reason, 'yellow')}")
        self._w()

    def _limitations(self, report: Report) -> None:
        notes: List[str] = list(report.collect_errors)
        p = report.platform
        if getattr(p, "in_container", False):
            notes.insert(0, f"运行在 {p.container_type} 容器内：SMART / RAID / 温度等项目可能不可见，"
                            "建议在宿主机上复检")
        if not getattr(p, "is_root", True) and getattr(p, "kind", "") in (
                "linux", "nas_appliance", "nas_software"):
            notes.append("以非 root 运行：SMART / RAID / 部分温度传感器读取受限")

        cov = report.coverage
        if cov.skipped >= cov.judged and cov.skipped:
            notes.append(f"本平台有 {cov.skipped} 项检测不适用（多为 Linux 专属："
                         f"SMART / RAID / 温度 / inode 等），结论仅基于其余 {cov.judged} 项")

        if not notes:
            return
        self._w("  " + self._c("⚠ 检测限制", "yellow"))
        for n in notes:
            for line in textwrap.wrap(n, width=76) or [n]:
                self._w(f"    {self._c('·', 'yellow')} {line}")
        self._w()

    def _categories(self, report: Report) -> None:
        # 权重为 0 的分类也要显示——只要它真的判定了东西。
        # 否则 JSON 里有这一类、终端和 HTML 里没有，同一份数据两种说法。
        cats = [c for c in report.score.categories
                if c.weight > 0 or c.score is not None]
        if not cats:
            return
        self._w("  " + self._c("分项", "dim"))
        for c in cats:
            if c.score is None:
                bar = self._c("— 未判定", "grey")
                score_text = "  —"
            else:
                filled = int(round(c.score / 100 * 20))
                color = "green" if c.score >= 85 else ("yellow" if c.score >= 60 else "red")
                bar = self._c("█" * filled + "░" * (20 - filled), color)
                score_text = f"{c.score:>3}"
            # 分母用「计入分数的项」，分子同时标出被剔除的低置信项——
            # 否则会出现「1/1 通过」这种让人以为全都查过了的显示。
            usable = c.judged - c.low_confidence
            ratio = f"{usable}/{c.total}"
            if c.low_confidence:
                ratio += self._c(f"（{c.low_confidence} 项存疑未计分）", "magenta")
            if usable and c.total and usable / c.total < 0.5:
                ratio += self._c(" 低覆盖", "grey")
            weight_note = (f"权重 {c.weight:.0f}" if c.weight > 0
                           else "权重 0 · 仅展示不计分")
            self._w(f"    {self._pad(c.name, 12)}{bar} {score_text}  "
                    f"{self._c(weight_note, 'dim')}  "
                    f"{self._c(ratio, 'dim')}")
        self._w()

    def _details(self, report: Report) -> None:
        grouped = report.by_category()
        self._w("  " + self._c("明细", "dim")
                + self._c("（✓ 通过  ! 告警  ✗ 严重  ? 不可判定  · 不适用）", "grey"))
        self._w()

        for cat in CATEGORY_ORDER:
            items = grouped.get(cat, [])
            if not items:
                continue
            # 低置信的项即使状态是 PASS 也要显示——它没计入分数，
            # 藏起来等于让用户以为"这类别没问题"。
            shown = items if self.verbose else [
                c for c in items
                if c.status not in (Status.PASS, Status.SKIP) or not c.counts_toward_score
            ]
            self._w(f"  {self._c(CATEGORY_NAMES.get(cat, cat), 'bold')}")

            if not shown:
                passed = len([c for c in items if c.status is Status.PASS])
                skipped = len(items) - passed
                if passed:
                    line = f"    {self._c('✓', 'green')} {self._c(f'{passed} 项通过', 'dim')}"
                    if skipped:
                        line += self._c(f"，{skipped} 项不适用", "grey")
                    self._w(line)
                else:
                    self._w(f"    {self._c('·', 'grey')} "
                            f"{self._c(f'{skipped} 项均不适用（平台或依赖不支持）', 'dim')}")
                self._w()
                continue

            for c in shown:
                self._render_check(c)
            if not self.verbose and len(shown) < len(items):
                self._w(f"    {self._c(f'… 另有 {len(items) - len(shown)} 项通过/不适用', 'grey')}")
            self._w()

    def _render_check(self, c: CheckResult) -> None:
        color = _STATUS_COLOR.get(c.status, "grey")
        self._w(f"    {self._c(c.status.glyph, color)} {self._pad(c.title, 18)}{c.summary}")

        # 低置信度标记：结论本身可能是对的，但数据不够可靠。
        # 用洋红而非黄——黄是「告警」的状态色，存疑是关于数据可靠性的元信息，
        # 同色系会让人误读成又一个告警。
        if c.confidence and c.confidence < LOW_CONFIDENCE and c.status is not Status.UNKNOWN:
            self._w(f"        {self._c(f'⚠ 结论存疑（置信度 {c.confidence:.2f}）', 'magenta')}")
            # 低置信的 PASS 不计入分数——必须说明，否则用户以为分数算错了。
            if not c.counts_toward_score:
                self._w(f"        {self._c('· 该项未计入分数（置信度不足，通过类不作为健康依据）', 'dim')}")

        if c.detail and (self.verbose or c.status in (Status.FAIL, Status.WARN)):
            for line in textwrap.wrap(c.detail, width=68):
                self._w(f"        {self._c(line, 'dim')}")
        if c.suggestion and c.status in (Status.FAIL, Status.WARN):
            for line in textwrap.wrap(f"建议：{c.suggestion}", width=68):
                self._w(f"        {self._c(line, 'cyan')}")
        if c.error:
            self._w(f"        {self._c('检查器异常：' + c.error, 'red')}")

        if self.verbose and c.evidence:
            for e in c.evidence[:6]:
                self._w(f"        {self._c(f'{e.source} · {e.key} = {e.value}', 'grey')}")

    def _inventory(self, report: Report) -> None:
        if not report.facts:
            return
        data = report.facts.summary()
        self._w("  " + self._c("设备清单", "dim"))

        st = data["storage"]
        if st["physical_disks"]:
            self._w("    物理盘")
            for d in st["physical_disks"][:12]:
                kind = "HDD" if d["rotational"] is True else ("SSD" if d["rotational"] is False else "?")
                self._w(f"      {self._pad(d['name'], 14)}{d['size_gb']:>7} GB  {kind}  {d['model']}")

        n = data["network"]
        if n["interfaces"]:
            self._w("    网卡")
            for i in n["interfaces"][:8]:
                speed = f"{i['speed_mbps']} Mbps" if i["speed_mbps"] else "-"
                self._w(f"      {self._pad(i['name'], 14)}{self._pad(i['ip'] or '(无 IP)', 16)}"
                        f"{speed:>10}  {'WiFi' if i['is_wireless'] else '有线'}")

        sv = data["services"]
        if sv["items"]:
            self._w("    服务")
            for i in sv["items"][:12]:
                self._w(f"      {self._pad(str(i['port']), 7)}"
                        f"{self._pad(i['name'], 22)}{i['category']}")
        self._w()

    def _footer(self, report: Report) -> None:
        self._w("  " + self._c(
            f"共 {report.coverage.total} 项检查 · 耗时 {report.meta.duration_s}s · "
            f"报告格式 v{report.meta.report_version} · 指纹 {report.meta.fingerprint}",
            "grey"))
        self._w()


# ── 历史对比渲染 ────────────────────────────────────────────
def render_diff(diff, color: bool = True) -> str:
    def c(text: str, name: str) -> str:
        if not color:
            return text
        return f"{_COLORS.get(name, '')}{text}{_COLORS['reset']}"

    lines: List[str] = [""]
    lines.append(f"  {c('对比', 'bold')}  {diff.old_ts}  →  {diff.new_ts}")

    if diff.old_score is not None and diff.new_score is not None:
        delta = diff.score_delta()
        if diff.score_comparable:
            sign = "+" if (delta or 0) > 0 else ""
            arrow = f"{diff.old_score} → {diff.new_score}（{sign}{delta}）"
            tone = "green" if (delta or 0) > 0 else ("red" if (delta or 0) < 0 else "grey")
        else:
            # 口径变了：分数差值没有意义，只给两个数，不给差值。
            arrow = f"{diff.old_score} → {diff.new_score}（口径不同，差值不可比）"
            tone = "grey"
        lines.append(f"  {c('分数', 'dim')}  {c(arrow, 'bold')}   "
                     f"{diff.old_grade} → {diff.new_grade}")

    # 口径变更提示：必须显眼，否则用户会把口径差当成设备变差。
    if diff.caliber_note:
        lines.append(f"  {c('⚠', 'yellow')} {c(diff.caliber_note, 'yellow')}")
    lines.append("")

    changes = diff.significant
    if not changes:
        lines.append(f"  {c('没有实质变化。', 'green')}")
        lines.append("")
        return "\n".join(lines)

    groups = [
        ("new_failure", "新增严重问题", "red"),
        ("still_failing", "仍然严重", "red"),
        ("evidence_worsened", "指标恶化", "yellow"),
        ("new_warning", "新增告警", "yellow"),
        ("improved", "有所好转", "green"),
        ("evidence_improved", "指标好转", "green"),
        ("evidence_changed", "指标变化", "grey"),
        ("fixed", "已修复", "green"),
        ("added", "新增检测项", "grey"),
        ("removed", "本次未检测", "grey"),
    ]

    for kind, label, color_name in groups:
        items = diff.of_kind(kind)
        if not items:
            continue
        lines.append(f"  {c(label, color_name)}")
        for ch in items:
            lines.append(f"    {c('·', color_name)} {ch.title}  {c(ch.note, 'dim')}")
            for e in ch.evidence[:4]:
                lines.append(f"        {c(e.text(), 'grey')}")
        lines.append("")

    return "\n".join(lines)
