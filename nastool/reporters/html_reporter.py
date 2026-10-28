"""
reporters/html_reporter.py — 单文件 HTML 报告

零外部依赖（不引 CDN、不引字体），可直接发微信/邮件，也能离线打开和打印。
"""
import datetime
import html as htmllib
from dataclasses import asdict


def esc(value) -> str:
    return htmllib.escape(str(value if value is not None else ""), quote=True)


_SEV_STYLE = {
    "critical": ("#c5221f", "#fce8e6", "严重"),
    "warning": ("#b06000", "#fef7e0", "告警"),
    "info": ("#1a73e8", "#e8f0fe", "提示"),
}

_KIND_LABEL = {
    "nas_appliance": "成品 NAS",
    "nas_software": "NAS 系统",
    "linux": "通用 Linux",
    "windows": "Windows",
    "macos": "macOS",
}


def _bar(pct: float, color: str = "#1a73e8") -> str:
    pct = max(0.0, min(100.0, float(pct or 0)))
    return (f'<span class="bar"><i style="width:{pct}%;background:{color}"></i></span>'
            f'<span class="bar-num">{pct:.0f}%</span>')


def _score_color(score: int) -> str:
    if score >= 90:
        return "#1e8e3e"
    if score >= 80:
        return "#4caf50"
    if score >= 60:
        return "#e8a33d"
    return "#c5221f"


def _ring(score: int, grade: str) -> str:
    color = _score_color(score)
    radius, circumference = 52, 2 * 3.14159 * 52
    dash = circumference * max(0, min(100, score)) / 100
    return f"""
    <div class="ring">
      <svg viewBox="0 0 120 120" width="132" height="132">
        <circle cx="60" cy="60" r="52" fill="none" stroke="#e8eaed" stroke-width="10"/>
        <circle cx="60" cy="60" r="52" fill="none" stroke="{color}" stroke-width="10"
                stroke-linecap="round" stroke-dasharray="{dash:.1f} {circumference:.1f}"
                transform="rotate(-90 60 60)"/>
        <text x="60" y="58" text-anchor="middle" font-size="30" font-weight="700"
              fill="{color}">{score}</text>
        <text x="60" y="78" text-anchor="middle" font-size="12" fill="#5f6368">/ 100</text>
      </svg>
      <div class="grade" style="color:{color}">{esc(grade)} 级</div>
    </div>"""


def _table(headers, rows, empty="—") -> str:
    if not rows:
        return f'<p class="muted">{esc(empty)}</p>'
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = ""
    for row in rows:
        cells = "".join(f"<td>{c}</td>" for c in row)
        body += f"<tr>{cells}</tr>"
    return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _kv_list(pairs) -> str:
    items = "".join(
        f'<div class="kv"><span class="k">{esc(k)}</span><span class="v">{v}</span></div>'
        for k, v in pairs
    )
    return f'<div class="kv-list">{items}</div>'


class HTMLReporter:
    def build(self, result) -> str:
        s = result.score
        p = result.platform
        d = result.device
        st = result.storage
        n = result.network
        sv = result.services
        ai = result.ai
        meta = result.meta
        now = meta.generated_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ── 概览 ──
        platform_rows = [
            ("类型", _KIND_LABEL.get(p.kind, esc(p.kind))),
            ("厂商 / 产品", f"{esc(p.vendor) or '—'} / {esc(p.product) or '—'}"),
            ("系统版本", esc(p.version) or "—"),
            ("架构", f"{esc(p.arch)} · kernel {esc(p.kernel)}"),
            ("运行环境", ("容器 (" + esc(p.container_type) + ")") if p.in_container else "物理机"),
            ("权限", "root" if p.is_root else "普通用户"),
        ]
        if p.data_roots:
            platform_rows.append(("数据盘", esc(", ".join(p.data_roots[:4]))))

        system_rows = [
            ("CPU", esc(d.cpu.model)),
            ("核心", f"{d.cpu.cores} 线程"
                     + (f" / {d.cpu.physical_cores} 核" if d.cpu.physical_cores else "")
                     + (f" @ {d.cpu.freq_mhz} MHz" if d.cpu.freq_mhz else "")),
            ("内存", f'{d.memory.total_gb} GB（可用 {d.memory.available_gb} GB，'
                     f'已用 {d.memory.used_percent}%）'),
            ("设备型号", f"{esc(d.board.manufacturer)} {esc(d.board.model)}"),
            ("序列号", esc(d.board.serial) or "—"),
            ("运行时长", f"{d.board.uptime_hours} 小时"),
            ("虚拟化", esc(d.virtualization) or "—"),
        ]
        if d.thermals:
            system_rows.append(("温度", " · ".join(
                f"{esc(t.zone_type or t.zone)} {t.temp_c}°C" for t in d.thermals[:6])))

        # ── 存储 ──
        storage_rows = [
            ("目标路径", esc(st.target_path)),
            ("可写", "是" if st.can_write else "否"),
            ("容量", f"{st.target_free_gb} GB 可用 / {st.target_total_gb} GB"
                     f"（已用 {st.target_use_percent}%）"),
        ]
        if st.speed_test_done:
            storage_rows.append(("读写速度",
                                 f"写 {st.seq_write_mbps} MB/s · 读 {st.seq_read_mbps} MB/s"))

        disk_rows = [
            [f"<code>{esc(x.name)}</code>", f"{x.size_gb} GB",
             "HDD" if x.rotational else ("SSD" if x.rotational is False else "—"),
             esc(x.model)]
            for x in st.physical_disks
        ]
        raid_rows = []
        for r in st.raids:
            badge = ('<span class="pill ok">正常</span>' if r.healthy
                     else '<span class="pill bad">异常</span>')
            extra = f" 重建 {r.rebuild_percent}%" if r.state == "rebuilding" else ""
            raid_rows.append([f"<code>{esc(r.name)}</code>",
                              f"{esc(r.kind)}/{esc(r.level)}",
                              f"{esc(r.state)}{extra}",
                              f"{r.members_active}/{r.members_total}", badge])
        smart_rows = []
        for sm in st.smart:
            if sm.healthy is True:
                badge = '<span class="pill ok">正常</span>'
            elif sm.healthy is False:
                badge = '<span class="pill bad">异常</span>'
            else:
                badge = '<span class="pill">未知</span>'
            smart_rows.append([f"<code>{esc(sm.device)}</code>", badge,
                               f"{sm.temperature_c}°C" if sm.temperature_c else "—",
                               f"{sm.power_on_hours} h" if sm.power_on_hours else "—",
                               esc(sm.message)])
        mount_rows = [
            [f"<code>{esc(x.mountpoint)}</code>", esc(x.fstype),
             f"{x.total_gb} GB", f"{x.free_gb} GB",
             _bar(x.use_percent, _score_color(100 - int(x.use_percent)))]
            for x in st.disks[:12]
        ]

        # ── 网络 ──
        iface_rows = [
            [f"<b>{esc(i.name)}</b>", esc(i.ip) or "—",
             f"{i.speed_mbps} Mbps" if i.speed_mbps else "—",
             esc(i.duplex) or "—", esc(i.mac) or "—",
             '<span class="pill ok">UP</span>' if i.up else '<span class="pill">DOWN</span>']
            for i in n.interfaces
        ]
        conn_rows = [
            ["网关", esc(n.gateway) or "—",
             '<span class="pill ok">可达</span>' if n.gateway_reachable else '<span class="pill warn">不可达</span>'],
            ["DNS", esc(n.dns_server) or "—",
             '<span class="pill ok">正常</span>' if n.dns_ok else '<span class="pill warn">失败</span>'],
            ["外网", "—",
             '<span class="pill ok">可达</span>' if n.internet_reachable else '<span class="pill">不可达</span>'],
        ]
        for peer in n.peers:
            conn_rows.append([f"对端 {esc(peer.label)}",
                              f"{peer.rtt_ms} ms" if peer.reachable else esc(peer.error),
                              '<span class="pill ok">可达</span>' if peer.reachable
                              else '<span class="pill bad">不可达</span>'])

        # ── 服务 ──
        service_rows = []
        for item in sv.items:
            if item.category == "其他":
                continue
            service_rows.append([f"<b>{esc(item.name)}</b>", str(item.port),
                                 esc(item.category), esc(item.bind_address) or "—",
                                 esc(item.process) or "—"])
        container_rows = [[f"<b>{esc(c.name)}</b>", esc(c.image), esc(c.status), esc(c.ports)]
                          for c in sv.containers]

        # ── AI ──
        ai_rows = []
        for dev in ai.devices:
            ai_rows.append([
                f"<b>{esc(dev.name)}</b>", esc(dev.chip_type), esc(dev.vendor),
                f"{dev.memory_total_mb} MB" if dev.memory_total_mb else "—",
                esc(dev.runtime_version or dev.driver_version) or "—",
                '<span class="pill ok">可用</span>' if dev.available else '<span class="pill">不可用</span>',
            ])

        # ── 问题清单 ──
        findings_html = ""
        if s.findings:
            for f in s.findings:
                color, bg, label = _SEV_STYLE.get(f.level, _SEV_STYLE["info"])
                suggestion = (f'<div class="sug">→ {esc(f.suggestion)}</div>'
                              if f.suggestion else "")
                findings_html += f"""
                <div class="finding" style="border-left-color:{color};background:{bg}">
                  <span class="tag" style="color:{color}">{label}</span>
                  <span class="cat">{esc(f.category)}</span>
                  <span class="msg">{esc(f.message)}</span>
                  {suggestion}
                </div>"""
        else:
            findings_html = '<p class="ok-text">✅ 未发现任何问题</p>'

        # ── 分项得分 ──
        cat_html = ""
        for cat in s.categories:
            full = int(cat.weight) or 1
            pct = cat.score / full * 100
            cat_html += f"""
            <div class="cat">
              <div class="cat-head"><span>{esc(cat.name)}</span>
                <span class="cat-score">{cat.score}<i>/{full}</i></span></div>
              {_bar(pct, _score_color(int(pct)))}
            </div>"""

        status_cls = "ok" if result.overall_ok else "bad"
        status_text = "设备状态正常" if result.overall_ok else "存在需要处理的问题"

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>nastool 检测报告 · {esc(meta.hostname)}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#f5f6f8; color:#202124;
         font:14px/1.65 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:28px 20px 60px; }}
  header {{ background:#fff; border-radius:16px; padding:24px 28px;
            box-shadow:0 1px 3px rgba(0,0,0,.08); display:flex; gap:28px; align-items:center; }}
  .ring {{ text-align:center; flex:0 0 auto; }}
  .grade {{ font-weight:700; font-size:15px; margin-top:4px; }}
  .head-main h1 {{ margin:0 0 6px; font-size:22px; }}
  .head-main .sub {{ color:#5f6368; font-size:13px; }}
  .badge {{ display:inline-block; margin-top:12px; padding:5px 14px; border-radius:999px;
            font-weight:600; font-size:13px; }}
  .badge.ok {{ background:#e6f4ea; color:#1e8e3e; }}
  .badge.bad {{ background:#fce8e6; color:#c5221f; }}
  section {{ background:#fff; border-radius:16px; padding:22px 26px; margin-top:18px;
             box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  h2 {{ font-size:16px; margin:0 0 14px; padding-bottom:10px; border-bottom:1px solid #eef0f2; }}
  h3 {{ font-size:13px; color:#5f6368; margin:18px 0 8px; font-weight:600; }}
  .kv-list {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:6px 26px; }}
  .kv {{ display:flex; gap:10px; font-size:13.5px; }}
  .kv .k {{ color:#5f6368; min-width:82px; flex:0 0 auto; }}
  .kv .v {{ flex:1; word-break:break-all; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; color:#5f6368; font-weight:600; padding:8px 10px;
        border-bottom:1px solid #eef0f2; white-space:nowrap; }}
  td {{ padding:8px 10px; border-bottom:1px solid #f4f5f7; vertical-align:middle; }}
  tr:last-child td {{ border-bottom:none; }}
  code {{ background:#f1f3f4; padding:1px 6px; border-radius:5px; font-size:12.5px; }}
  .bar {{ display:inline-block; width:90px; min-width:90px; height:7px; background:#dfe3e8;
          border-radius:4px; overflow:hidden; vertical-align:middle; }}
  .bar i {{ display:block; height:100%; border-radius:4px; }}
  .bar-num {{ font-size:12px; color:#5f6368; margin-left:6px; }}
  .pill {{ display:inline-block; padding:1px 9px; border-radius:999px; font-size:12px;
           background:#f1f3f4; color:#5f6368; }}
  .pill.ok {{ background:#e6f4ea; color:#1e8e3e; }}
  .pill.bad {{ background:#fce8e6; color:#c5221f; }}
  .pill.warn {{ background:#fef7e0; color:#b06000; }}
  .cat {{ margin-bottom:12px; }}
  .cat-head {{ display:flex; justify-content:space-between; font-size:13px; margin-bottom:4px; }}
  .cat-score {{ font-weight:700; }}
  .cat-score i {{ font-style:normal; color:#9aa0a6; font-weight:400; font-size:12px; }}
  .finding {{ border-left:4px solid; border-radius:8px; padding:9px 14px; margin-bottom:8px;
              font-size:13.5px; }}
  .finding .tag {{ font-weight:700; margin-right:8px; }}
  .finding .cat {{ color:#5f6368; margin-right:8px; }}
  .finding .sug {{ color:#5f6368; font-size:12.5px; margin-top:3px; }}
  .muted {{ color:#9aa0a6; font-size:13px; }}
  .ok-text {{ color:#1e8e3e; font-weight:600; margin:0; }}
  footer {{ text-align:center; color:#9aa0a6; font-size:12px; margin-top:26px; }}
  @media print {{ body {{ background:#fff; }} section, header {{ box-shadow:none; border:1px solid #eef0f2; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    {_ring(s.total, s.grade)}
    <div class="head-main">
      <h1>{esc(meta.hostname) or "NAS 设备"}</h1>
      <div class="sub">
        {esc(p.pretty_name) or esc(meta.platform_summary)} ·
        {_KIND_LABEL.get(p.kind, esc(p.kind))} ·
        {esc(p.arch)}
      </div>
      <div class="sub">检测时间 {esc(now)} · 耗时 {meta.duration_s}s · nastool v{esc(meta.version)}</div>
      <div class="badge {status_cls}">{esc(status_text)} · {esc(s.verdict)}</div>
    </div>
  </header>

  <section>
    <h2>健康评分</h2>
    {cat_html}
    <div class="cat-head" style="margin-top:16px">
      <span style="color:#5f6368">AI 算力（不计入总分）</span>
      <span class="cat-score">{s.ai_score if s.ai_score else "—"}</span>
    </div>
    <p class="muted" style="margin:2px 0 0">{esc(s.ai_note)}</p>
  </section>

  <section>
    <h2>问题清单（{len(s.findings)} 项）</h2>
    {findings_html}
  </section>

  <section>
    <h2>平台与系统</h2>
    {_kv_list(platform_rows)}
    <h3>系统信息</h3>
    {_kv_list(system_rows)}
  </section>

  <section>
    <h2>存储</h2>
    {_kv_list(storage_rows)}
    <h3>物理磁盘（{len(st.physical_disks)} 块）</h3>
    {_table(["设备", "容量", "类型", "型号"], disk_rows, "未探测到物理磁盘（容器/虚拟机中常见）")}
    <h3>阵列</h3>
    {_table(["名称", "类型", "状态", "在线盘", "健康"], raid_rows, "未检测到 RAID / ZFS / Btrfs 阵列")}
    <h3>SMART</h3>
    {_table(["设备", "健康", "温度", "通电时长", "备注"], smart_rows,
            "未检查（需 smartctl 与 root 权限）")}
    <h3>挂载点</h3>
    {_table(["挂载点", "文件系统", "容量", "可用", "使用率"], mount_rows)}
  </section>

  <section>
    <h2>网络</h2>
    {_table(["接口", "IP", "速率", "双工", "MAC", "状态"], iface_rows, "未探测到网络接口")}
    <h3>连通性</h3>
    {_table(["目标", "详情", "状态"], conn_rows)}
  </section>

  <section>
    <h2>服务（{sv.total_listening} 个端口监听）</h2>
    {_table(["服务", "端口", "分类", "监听地址", "进程"], service_rows,
            "未探测到已知服务（可能权限受限）")}
    <h3>Docker 容器（{len(sv.containers)} 个运行中）</h3>
    {_table(["名称", "镜像", "状态", "端口映射"], container_rows,
            "未检测到 Docker 或没有运行中的容器")}
  </section>

  <section>
    <h2>AI 算力</h2>
    {_table(["设备", "类型", "厂商", "显存", "Runtime/驱动", "状态"], ai_rows)}
    <p class="muted">
      推理引擎：{esc(ai.inference_engine) or "无"}
      {"· 推理耗时 " + str(ai.inference_test_ms) + " ms" if ai.inference_test_ms else ""}
    </p>
  </section>

  <footer>nastool v{esc(meta.version)} · 通用 NAS 设备检测工具 · 报告生成于 {esc(now)}</footer>
</div>
</body>
</html>"""

    def save(self, html: str, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
