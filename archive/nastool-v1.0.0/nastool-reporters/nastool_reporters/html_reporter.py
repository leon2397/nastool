"""
reporters/html_reporter.py -- HTML 可视化报告
生成单文件 HTML，可直接在浏览器打开或发给用户
"""

import datetime
from dataclasses import asdict


# 内嵌 CSS + JS，单文件无需外部依赖
_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NASArm Toolkit 诊断报告</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
         background: #0f1117; color: #e0e0e0; padding: 24px; }}
  .container {{ max-width: 960px; margin: 0 auto; }}

  h1 {{ color: #fff; font-size: 1.4rem; margin-bottom: 8px; }}
  .meta {{ color: #888; font-size: .85rem; margin-bottom: 24px; }}

  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px;
            font-size: .85rem; font-weight: 600; margin-bottom: 20px; }}
  .badge-ok {{ background: #1a4d2e; color: #4ade80; }} 
  .badge-fail {{ background: #4d1a1a; color: #f87171; }}

  .card {{ background: #1a1d27; border-radius: 12px; padding: 20px;
           margin-bottom: 16px; border: 1px solid #2a2d3a; }}
  .card h2 {{ color: #a78bfa; font-size: 1rem; margin-bottom: 16px;
              border-bottom: 1px solid #2a2d3a; padding-bottom: 8px; }}

  .row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }}
  .kv {{ flex: 1 1 45%; }}
  .kv .key {{ color: #888; font-size: .82rem; margin-bottom: 2px; }}
  .kv .val {{ font-size: .95rem; color: #e0e0e0; }}

  .status-ok {{ color: #4ade80; font-weight: 600; }}
  .status-fail {{ color: #f87171; font-weight: 600; }}
  .status-warn {{ color: #fbbf24; font-weight: 600; }}
  .status-skip {{ color: #888; }}

  .bar-wrap {{ background: #2a2d3a; border-radius: 4px; height: 6px;
               margin-top: 4px; overflow: hidden; }}
  .bar {{ height: 100%; border-radius: 4px; transition: width .4s; }}
  .bar-ok {{ background: #4ade80; }}
  .bar-warn {{ background: #fbbf24; }}
  .bar-fail {{ background: #f87171; }}

  table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
  th {{ text-align: left; color: #888; padding: 6px 8px; border-bottom: 1px solid #2a2d3a; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #222; }}
  tr:hover {{ background: #1f2230; }}

  .warn-list {{ margin-top: 12px; }}
  .warn-item {{ background: #2d200a; border-left: 3px solid #fbbf24;
                padding: 8px 12px; border-radius: 4px; margin-bottom: 6px;
                font-size: .85rem; color: #fbbf24; }}

  .footer {{ text-align: center; color: #555; font-size: .8rem; margin-top: 32px; }}
  .tag {{ display: inline-block; background: #2a2d3a; border-radius: 4px;
          padding: 2px 8px; font-size: .78rem; color: #888; margin: 2px; }}
</style>
</head>
<body>
<div class="container">
  <h1>🍓 NASArm Toolkit 诊断报告</h1>
  <div class="meta">{generated_at} · {device_model}</div>
  <div class="badge {badge_class}">{overall}</div>

  <!-- 设备 -->
  <div class="card">
    <h2>💻 设备信息</h2>
    <div class="row">
      <div class="kv"><div class="key">CPU</div><div class="val">{cpu}</div></div>
      <div class="kv"><div class="key">核心数</div><div class="val">{cores}</div></div>
      <div class="kv"><div class="key">架构</div><div class="val">{arch}</div></div>
      <div class="kv"><div class="key">内存</div><div class="val">{memory}</div></div>
      <div class="kv"><div class="key">设备型号</div><div class="val">{board_model}</div></div>
      <div class="kv"><div class="key">内核</div><div class="val">{kernel}</div></div>
    </div>
    {temps_html}
  </div>

  <!-- 存储 -->
  <div class="card">
    <h2>💾 存储</h2>
    <div class="row">
      <div class="kv"><div class="key">目标路径</div>
        <div class="val {path_class}">{path}</div></div>
      <div class="kv"><div class="key">可写</div>
        <div class="val {write_class}">{write}</div></div>
    </div>
    {speed_html}
    {disks_html}
    {warnings_storage}
  </div>

  <!-- 网络 -->
  <div class="card">
    <h2>🌐 网络</h2>
    <table>
      <tr><th>接口</th><th>IP</th><th>速率</th><th>状态</th></tr>
      {ifaces_html}
    </table>
    <div class="row" style="margin-top:12px">
      <div class="kv"><div class="key">NAS 后端</div>
        <div class="val {nas_class}">{nas_backend}</div></div>
      <div class="kv"><div class="key">互联网</div>
        <div class="val">{internet}</div></div>
    </div>
  </div>

  <!-- AI 算力 -->
  <div class="card">
    <h2>🧠 AI 算力</h2>
    <div class="row">
      <div class="kv"><div class="key">芯片类型</div><div class="val">{chip_type}</div></div>
      <div class="kv"><div class="key">推理引擎</div><div class="val">{inference_engine}</div></div>
      <div class="kv"><div class="key">推理测试</div>
        <div class="val {inf_class}">{inference_result}</div></div>
      {config_npu_html}
    </div>
    {devices_html}
  </div>

  <div class="footer">NASArm Toolkit v0.1 · AI-NAS Media Manager</div>
</div>
</body>
</html>"""


class HTMLReporter:
    """生成单文件 HTML 诊断报告"""

    def _cls(self, ok: bool) -> str:
        return "status-ok" if ok else "status-fail"

    def _badge(self, ok: bool) -> str:
        return "badge-ok" if ok else "badge-fail"

    def _overall(self, ok: bool) -> str:
        return "[OK] 全部通过" if ok else "[X] 存在失败项"

    def _bar(self, pct: float) -> str:
        cls = "bar-ok" if pct < 70 else ("bar-warn" if pct < 85 else "bar-fail")
        return f'<div class="bar-wrap"><div class="bar {cls}" style="width:{min(100, pct)}%"></div></div>'

    def build(self, device_rpt, storage_rpt, network_rpt, ai_rpt, adapter_rpt, all_ok: bool) -> str:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # CPU
        cpu = device_rpt.cpu
        mem = device_rpt.memory
        board = device_rpt.board
        arch = cpu.arch or "ARM64"

        # 温度
        temps_html = ""
        if device_rpt.thermals:
            rows = ""
            for t in device_rpt.thermals[:4]:
                cls = (
                    "status-ok"
                    if t.temp_c < 60
                    else ("status-warn" if t.temp_c < 80 else "status-fail")
                )
                rows += (
                    f'<tr><td>{t.zone_type or t.zone}</td><td class="{cls}">{t.temp_c}°C</td></tr>'
                )
            temps_html = f"<table><tr><th>传感器</th><th>温度</th></tr>{rows}</table>"

        # 存储
        path_ok = storage_rpt.target_exists and storage_rpt.is_dir
        path_cls = self._cls(path_ok)
        write_cls = self._cls(storage_rpt.can_write)

        speed_html = ""
        if storage_rpt.speed_test_done:
            speed_html = f'<div class="row">'
            for label, val in [
                ("顺序写", storage_rpt.seq_write_mbps),
                ("顺序读", storage_rpt.seq_read_mbps),
            ]:
                spd_cls = (
                    "status-ok" if val > 30 else ("status-warn" if val > 10 else "status-fail")
                )
                speed_html += f'<div class="kv"><div class="key">{label}</div><div class="val {spd_cls}">{val} MB/s</div></div>'
            speed_html += "</div>"

        disks_html = ""
        if storage_rpt.disks:
            rows = ""
            for d in storage_rpt.disks:
                rows += f"<tr><td>{d.device}</td><td>{d.mountpoint}</td><td>{d.total_gb}GB</td><td>{d.use_percent}%{self._bar(d.use_percent)}</td></tr>"
            disks_html = f"<table><tr><th>设备</th><th>挂载点</th><th>容量</th><th>使用率</th></tr>{rows}</table>"

        warn_storage = ""
        if storage_rpt.errors:
            items = "".join(f'<div class="warn-item">[!] {e}</div>' for e in storage_rpt.errors)
            warn_storage = f'<div class="warn-list">{items}</div>'

        # 网络
        ifaces_html = ""
        for iface in network_rpt.interfaces:
            status = (
                '<span class="status-ok">UP</span>'
                if iface.up
                else '<span class="status-fail">DOWN</span>'
            )
            ifaces_html += f"<tr><td>{iface.name}</td><td>{iface.ip or '--'}</td>"
            ifaces_html += f"<td>{iface.speed_mbps} Mbps</td><td>{status}</td></tr>"

        nas_reachable = network_rpt.nas_backend.reachable
        nas_cls = self._cls(nas_reachable)
        nas_text = f"可达 {network_rpt.nas_backend.rtt_ms}ms" if nas_reachable else "不可达"
        internet_cls = self._cls(network_rpt.internet_reachable)
        internet_text = "可达" if network_rpt.internet_reachable else "不可达"

        # AI
        chip_type = ai_rpt.best_chip_type
        inf_cls = self._cls(ai_rpt.inference_available)
        inf_text = (
            f"通过 ({ai_rpt.inference_engine}, {ai_rpt.inference_test_ms}ms)"
            if ai_rpt.inference_available
            else "失败"
        )

        config_npu_html = ""
        if ai_rpt.config_npu_type:
            config_npu_html = f'<div class="kv"><div class="key">config.yaml npu_type</div><div class="val">{ai_rpt.config_npu_type}</div></div>'

        devices_html = ""
        for dev in ai_rpt.devices:
            dev_cls = "status-ok" if dev.available else "status-fail"
            avail_txt = "可用" if dev.available else "不可用"
            mem_str = f"{dev.memory_total_mb} MB" if dev.memory_total_mb > 0 else ""
            devices_html += (
                f'<div class="kv"><div class="key">{dev.name}</div>'
                f'<div class="val {dev_cls}">{avail_txt} {mem_str}</div></div>'
            )

        return _TEMPLATE.format(
            generated_at=now,
            device_model=board.model,
            badge_class=self._badge(all_ok),
            overall=self._overall(all_ok),
            cpu=cpu.model,
            cores=str(cpu.cores),
            arch=arch,
            memory=f"{mem.total_gb} GB (可用 {mem.available_gb} GB) {self._bar(mem.used_percent)}",
            board_model=board.model,
            kernel=board.kernel,
            temps_html=temps_html,
            path=storage_rpt.target_path,
            path_class=path_cls,
            write="是" if storage_rpt.can_write else "否",
            write_class=write_cls,
            speed_html=speed_html,
            disks_html=disks_html,
            warnings_storage=warn_storage,
            ifaces_html=ifaces_html,
            nas_backend=nas_text,
            nas_cls=nas_cls,
            internet=internet_text,
            chip_type=chip_type,
            inference_engine=ai_rpt.inference_engine or "--",
            inf_class=inf_cls,
            inference_result=inf_text,
            config_npu_html=config_npu_html,
            devices_html=devices_html,
        )

    def save(self, html: str, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
