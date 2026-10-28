"""
nastool/reporters/html_reporter.py — 单文件自包含 HTML 报告

三条硬约束：
  1. **零外部资源**：不引 CDN、不引字体、不引图片，断网可开、可直接发微信/邮件
  2. **可打印**：A4 打印时不丢内容（这份报告最常见的用途就是"发出去"）
  3. **结论优先**：打开先看到分数、等级、覆盖度、严重问题，再往下才是清单

判断依据全部来自 CheckResult；facts 只用于展示设备清单，不参与结论。
"""
from __future__ import annotations

import html
import os
from typing import Any, Dict, List

from ..model import CATEGORY_NAMES, CATEGORY_ORDER, CheckResult, Report, Status

_STATUS_STYLE = {
    Status.PASS: ("pass", "✓", "通过"),
    Status.WARN: ("warn", "!", "告警"),
    Status.FAIL: ("fail", "✗", "严重"),
    Status.UNKNOWN: ("unknown", "?", "不可判定"),
    Status.SKIP: ("skip", "·", "不适用"),
}

_CSS = """
* { box-sizing: border-box; }
body { margin:0; padding:32px 20px 60px; background:#f5f6f8; color:#1f2329;
       font:14px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",
       "Hiragino Sans GB","Microsoft YaHei",sans-serif; }
.wrap { max-width:1080px; margin:0 auto; }
.card { background:#fff; border-radius:12px; padding:22px 26px; margin-bottom:18px;
        box-shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.10); }
h1 { font-size:19px; margin:0 0 4px; font-weight:600; letter-spacing:.2px; }
h2 { font-size:15px; margin:26px 0 10px; font-weight:600; color:#1f2329;
     display:flex; align-items:center; gap:8px; }
h2 .count { font-size:12px; font-weight:400; color:#8f959e; }
.sub { color:#8f959e; font-size:12.5px; }
.mono { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }

/* 结论区 */
.verdict { display:flex; gap:26px; align-items:center; flex-wrap:wrap; }
.ring { position:relative; width:118px; height:118px; flex:0 0 auto; }
.ring svg { transform:rotate(-90deg); }
.ring .num { position:absolute; inset:0; display:flex; flex-direction:column;
             align-items:center; justify-content:center; }
.ring .num b { font-size:31px; line-height:1; font-weight:600; }
.ring .num span { font-size:11px; color:#8f959e; margin-top:3px; }
.facts { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
         gap:14px 22px; flex:1; min-width:260px; }
.facts div { font-size:13px; }
.facts .k { color:#8f959e; font-size:11.5px; margin-bottom:2px; }
.facts .v { font-weight:500; }

/* 覆盖度条 */
.covbar { height:7px; background:#eef0f3; border-radius:4px; overflow:hidden; margin-top:8px; }
.covbar span { display:block; height:100%; background:#1a73e8; border-radius:4px; }

/* 分项 */
.cats { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px 26px; }
.cat-item .row { display:flex; justify-content:space-between; font-size:13px; margin-bottom:4px; }
.cat-item .bar { height:6px; background:#eef0f3; border-radius:4px; overflow:hidden; }
.cat-item .bar span { display:block; height:100%; border-radius:4px; }

/* 检查项 */
.check { display:flex; gap:10px; padding:8px 0; border-top:1px solid #f0f1f3; }
.check:first-child { border-top:none; }
.pill { flex:0 0 auto; width:18px; height:18px; border-radius:50%; color:#fff;
        font-size:11px; display:flex; align-items:center; justify-content:center;
        margin-top:2px; font-weight:700; }
.pass { background:#0f9d58; } .warn { background:#f4b400; }
.fail { background:#db4437; } .unknown { background:#1a73e8; }
.skip { background:#c8ccd1; }
.check .body { flex:1; min-width:0; }
.check .title { font-weight:500; }
.check .sum { color:#4e5969; font-size:13px; }
.check .detail, .check .fix { font-size:12.5px; color:#8f959e; margin-top:3px; }
.check .fix { color:#1a73e8; }
.ev { margin:6px 0 0; padding:8px 10px; background:#f7f8fa; border-radius:6px;
      font-size:12px; color:#4e5969; font-family:ui-monospace,Menlo,Consolas,monospace; }
.ev div { padding:1px 0; }

/* 表格 */
table { width:100%; border-collapse:collapse; font-size:12.5px; }
th { text-align:left; color:#8f959e; font-weight:500; padding:6px 8px;
     border-bottom:1px solid #eef0f3; }
td { padding:6px 8px; border-bottom:1px solid #f5f6f8; }
tr:last-child td { border-bottom:none; }
.num { text-align:right; font-family:ui-monospace,Menlo,Consolas,monospace; }

.note { background:#fff8e6; border-left:3px solid #f4b400; padding:10px 14px;
        border-radius:0 6px 6px 0; font-size:12.5px; color:#7a5c00; margin-top:10px; }
.note.err { background:#fdecea; border-color:#db4437; color:#8a1f17; }
.cap { background:#fdecea; color:#8a1f17; padding:8px 12px; border-radius:6px;
       font-size:12.5px; margin-top:10px; }
footer { color:#a5aab1; font-size:11.5px; text-align:center; margin-top:26px; }

@media print {
  body { background:#fff; padding:0; }
  .card { box-shadow:none; border:1px solid #e5e6eb; break-inside:avoid; }
  details { display:block; }
}
"""


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _score_color(score) -> str:
    if score is None:
        return "#c8ccd1"
    if score >= 85:
        return "#0f9d58"
    if score >= 60:
        return "#f4b400"
    return "#db4437"


class HTMLReporter:
    # ── 片段 ────────────────────────────────────────────────
    def _ring(self, score, grade: str, verdict: str) -> str:
        pct = 0 if score is None else max(0, min(100, score))
        color = _score_color(score)
        radius = 50
        circumference = 2 * 3.14159265 * radius
        dash = circumference * pct / 100
        display = "N/A" if score is None else str(score)
        return f'''
      <div class="ring">
        <svg width="118" height="118" viewBox="0 0 118 118">
          <circle cx="59" cy="59" r="{radius}" fill="none" stroke="#eef0f3" stroke-width="9"/>
          <circle cx="59" cy="59" r="{radius}" fill="none" stroke="{color}" stroke-width="9"
                  stroke-linecap="round" stroke-dasharray="{dash:.1f} {circumference:.1f}"/>
        </svg>
        <div class="num"><b style="color:{color}">{display}</b><span>{_esc(grade)} 级</span></div>
      </div>'''

    def _verdict_block(self, report: Report) -> str:
        sc, cov = report.score, report.coverage
        p = report.platform
        vendor = " ".join(x for x in (getattr(p, "vendor", ""), getattr(p, "product", ""),
                                      getattr(p, "version", "")) if x)
        model = getattr(p, "facts", {}).get("model", "")

        cov_bar = f'''
        <div style="margin-top:2px">
          <div class="sub">覆盖 {cov.judged}/{cov.applicable} 项（{cov.percent}%）
            {'· ' + str(cov.unknown) + ' 项不可判定' if cov.unknown else ''}
            {'· ' + str(cov.skipped) + ' 项不适用' if cov.skipped else ''}</div>
          <div class="covbar"><span style="width:{cov.percent}%"></span></div>
        </div>'''

        cap = ""
        if sc.capped and sc.cap_reason:
            cap = f'<div class="cap">{_esc(sc.cap_reason)}</div>'

        return f'''
    <div class="card">
      <div class="verdict">
        {self._ring(sc.total, sc.grade, sc.verdict)}
        <div class="facts">
          <div><div class="k">结论</div><div class="v">{_esc(sc.verdict or "—")}</div></div>
          <div><div class="k">置信度</div><div class="v">{sc.confidence:.2f}</div></div>
          <div><div class="k">主机</div><div class="v">{_esc(report.meta.hostname or "—")}</div></div>
          <div><div class="k">平台</div><div class="v">{_esc(vendor or getattr(p, "pretty_name", ""))}</div></div>
          <div><div class="k">型号</div><div class="v">{_esc(model or "—")}</div></div>
          <div><div class="k">场景</div><div class="v">{_esc(report.meta.profile)}</div></div>
        </div>
      </div>
      <div style="margin-top:16px">{cov_bar}</div>
      {cap}
    </div>'''

    def _limitations(self, report: Report) -> str:
        notes: List[str] = list(report.collect_errors)
        p = report.platform
        if getattr(p, "in_container", False):
            notes.insert(0, f"运行在 {p.container_type} 容器内：SMART / RAID / 温度等项目可能不可见")
        if not getattr(p, "is_root", True) and getattr(p, "kind", "") in (
                "linux", "nas_appliance", "nas_software"):
            notes.append("以非 root 运行：SMART / RAID / 部分温度传感器读取受限")
        cov = report.coverage
        if cov.skipped >= cov.judged and cov.skipped:
            notes.append(f"本平台有 {cov.skipped} 项检测不适用（多为 Linux 专属："
                         f"SMART / RAID / 温度 / inode 等），结论仅基于其余 {cov.judged} 项")
        if not notes:
            return ""
        items = "".join(f"<div>· {_esc(n)}</div>" for n in notes)
        return f'<div class="note">{items}</div>'

    def _categories(self, report: Report) -> str:
        cats = [c for c in report.score.categories if c.weight > 0]
        if not cats:
            return ""
        items = []
        for c in cats:
            pct = 0 if c.score is None else c.score
            color = _score_color(c.score)
            label = "未判定" if c.score is None else str(c.score)
            coverage_note = f"{c.judged}/{c.total}"
            if c.judged and c.total and c.judged / c.total < 0.5:
                coverage_note += " 低覆盖"
            items.append(f'''
        <div class="cat-item">
          <div class="row"><span>{_esc(c.name)}
            <span class="sub">{_esc(coverage_note)}</span></span>
            <span class="mono" style="color:{color}">{label}</span></div>
          <div class="bar"><span style="width:{pct}%;background:{color}"></span></div>
        </div>''')
        return f'''
    <div class="card">
      <h1>分项得分</h1>
      <div class="sub" style="margin-bottom:14px">权重按场景「{_esc(report.meta.profile)}」计算，未参与的分类不计入总分</div>
      <div class="cats">{''.join(items)}</div>
    </div>'''

    def _check_row(self, c: CheckResult) -> str:
        cls, glyph, label = _STATUS_STYLE.get(c.status, ("skip", "·", ""))
        extra = ""
        if c.detail:
            extra += f'<div class="detail">{_esc(c.detail)}</div>'
        if c.suggestion and c.status in (Status.WARN, Status.FAIL):
            extra += f'<div class="fix">建议：{_esc(c.suggestion)}</div>'
        if c.error:
            extra += f'<div class="detail" style="color:#db4437">检查器异常：{_esc(c.error)}</div>'
        if c.evidence:
            rows = "".join(
                f"<div>{_esc(e.source)}{' · ' if e.source else ''}{_esc(e.key)} = {_esc(e.value)}"
                + (f" <span style='color:#a5aab1'>({_esc(e.note)})</span>" if e.note else "")
                + "</div>"
                for e in c.evidence[:8]
            )
            extra += f'<details class="ev"><summary>证据（{len(c.evidence)} 条）</summary>{rows}</details>'

        return f'''
        <div class="check">
          <div class="pill {cls}" title="{_esc(label)}">{glyph}</div>
          <div class="body">
            <div class="title">{_esc(c.title)}</div>
            <div class="sum">{_esc(c.summary)}</div>
            {extra}
          </div>
        </div>'''

    def _checks(self, report: Report) -> str:
        grouped = report.by_category()
        blocks = []
        for cat in CATEGORY_ORDER:
            items = grouped.get(cat, [])
            if not items:
                continue
            judged = len([c for c in items if c.status.judged])
            blocks.append(f'''
      <h2>{_esc(CATEGORY_NAMES.get(cat, cat))}<span class="count">{judged}/{len(items)} 已判定</span></h2>
      {''.join(self._check_row(c) for c in items)}''')
        return f'''
    <div class="card">
      <h1>检测明细</h1>
      <div class="sub" style="margin-bottom:6px">
        ✓ 通过　! 告警　✗ 严重　? 不可判定（不扣分，但计入盲区）　· 不适用
      </div>
      {''.join(blocks)}
    </div>'''

    # ── 设备清单 ────────────────────────────────────────────
    def _inventory(self, report: Report) -> str:
        if not report.facts:
            return ""
        d: Dict[str, Any] = report.facts.summary()
        parts = []

        st = d["storage"]
        if st["physical_disks"]:
            rows = "".join(
                f"<tr><td class='mono'>{_esc(x['name'])}</td><td>{_esc(x['model'])}</td>"
                f"<td class='num'>{x['size_gb']}</td>"
                f"<td>{'HDD' if x['rotational'] is True else ('SSD' if x['rotational'] is False else '?')}</td></tr>"
                for x in st["physical_disks"]
            )
            parts.append(f'''<h2>物理磁盘</h2>
        <table><tr><th>设备</th><th>型号</th><th class="num">容量 GB</th><th>类型</th></tr>{rows}</table>''')

        if st["raids"]:
            rows = "".join(
                f"<tr><td>{_esc(r['name'])}</td><td>{_esc(r['level'])}</td>"
                f"<td>{_esc(r['state'])}</td><td class='num'>{r['members_active']}/{r['members_total']}</td>"
                f"<td>{'正常' if r['healthy'] else '异常'}</td></tr>"
                for r in st["raids"]
            )
            parts.append(f'''<h2>阵列</h2>
        <table><tr><th>名称</th><th>级别</th><th>状态</th><th class="num">在线/总数</th><th>结论</th></tr>{rows}</table>''')

        if st["smart"]:
            rows = "".join(
                f"<tr><td class='mono'>{_esc(x['device'])}</td><td>{_esc(x['model'])}</td>"
                f"<td>{'通过' if x['healthy'] else ('失败' if x['healthy'] is False else '无法判定')}</td>"
                f"<td class='num'>{x['temperature_c'] or '-'}</td>"
                f"<td class='num'>{x['power_on_hours'] or '-'}</td>"
                f"<td class='num'>{x['reallocated_sectors']}</td></tr>"
                for x in st["smart"]
            )
            parts.append(f'''<h2>硬盘 SMART</h2>
        <table><tr><th>设备</th><th>型号</th><th>健康</th><th class="num">温度 °C</th>
        <th class="num">通电小时</th><th class="num">重映射</th></tr>{rows}</table>''')

        n = d["network"]
        if n["interfaces"]:
            rows = "".join(
                f"<tr><td>{_esc(i['name'])}</td><td class='mono'>{_esc(i['ip'] or '—')}</td>"
                f"<td class='mono'>{_esc(i['mac'] or '—')}</td>"
                f"<td class='num'>{i['speed_mbps'] or '—'}</td>"
                f"<td>{'无线' if i['is_wireless'] else '有线'}</td>"
                f"<td>{'UP' if i['up'] else 'DOWN'}</td></tr>"
                for i in n["interfaces"]
            )
            parts.append(f'''<h2>网络接口</h2>
        <table><tr><th>名称</th><th>IP</th><th>MAC</th><th class="num">速率 Mbps</th>
        <th>类型</th><th>状态</th></tr>{rows}</table>''')

        sv = d["services"]
        if sv["items"]:
            rows = "".join(
                f"<tr><td class='num'>{i['port']}</td><td>{_esc(i['name'])}</td>"
                f"<td>{_esc(i['category'])}</td><td class='mono'>{_esc(i['bind_address'] or '—')}</td>"
                f"<td>{_esc(i['note'])}</td></tr>"
                for i in sv["items"]
            )
            parts.append(f'''<h2>监听端口</h2>
        <table><tr><th class="num">端口</th><th>服务</th><th>分类</th><th>绑定地址</th><th>说明</th></tr>
        {rows}</table>''')

        if sv["containers"]:
            rows = "".join(
                f"<tr><td>{_esc(c['name'])}</td><td class='mono'>{_esc(c['image'])}</td>"
                f"<td>{_esc(c['status'])}</td></tr>" for c in sv["containers"]
            )
            parts.append(f'''<h2>容器</h2>
        <table><tr><th>名称</th><th>镜像</th><th>状态</th></tr>{rows}</table>''')

        sec = d["security"]
        rows = []
        if sec["ssh"]["found"]:
            rows.append(
                f"<tr><td>SSH 配置</td><td>PermitRootLogin={_esc(sec['ssh']['permit_root_login'] or '默认')}"
                f"　PasswordAuthentication={_esc(sec['ssh']['password_auth'] or '默认')}</td></tr>")
        fw = sec["firewall"]
        rows.append(f"<tr><td>防火墙</td><td>{_esc('、'.join(fw['detected']) or '未检测到')}"
                    f"　{'已启用' if fw['active'] else ('未启用' if fw['active'] is False else '无法判定')}</td></tr>")
        for c in sec["certs"]:
            rows.append(f"<tr><td>证书</td><td class='mono'>{_esc(c['path'])}<br>"
                        f"{_esc(c['subject'])}<br>剩余 {c['days_left'] if c['days_left'] is not None else '?'} 天</td></tr>")
        if rows:
            parts.append(f'''<h2>安全配置</h2>
        <table><tr><th style="width:110px">项目</th><th>内容</th></tr>{''.join(rows)}</table>''')

        if not parts:
            return ""
        return f'''
    <div class="card">
      <h1>设备清单</h1>
      <div class="sub" style="margin-bottom:4px">以下为采集到的原始事实，仅作参考，判定以上方检测明细为准</div>
      {''.join(parts)}
    </div>'''

    # ── 主入口 ──────────────────────────────────────────────
    def build(self, report: Report) -> str:
        meta = report.meta
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>nastool 检测报告 · {_esc(meta.hostname)} · {_esc(meta.generated_at)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="card" style="padding-bottom:16px">
    <h1>nastool 设备检测报告</h1>
    <div class="sub">v{_esc(meta.version)} · 报告格式 v{_esc(meta.report_version)} ·
      {_esc(meta.generated_at)} · 耗时 {meta.duration_s}s</div>
    {self._limitations(report)}
  </div>
  {self._verdict_block(report)}
  {self._categories(report)}
  {self._checks(report)}
  {self._inventory(report)}
  <footer>
    由 nastool 生成 · 设备指纹 {_esc(meta.fingerprint)} ·
    {_esc(meta.platform_summary)} · Python {_esc(meta.python)}<br>
    本报告为只读检测结果，未修改系统任何配置
  </footer>
</div>
</body>
</html>'''

    def save(self, html_text: str, path: str) -> str:
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_text)
        return path
