# -*- coding: utf-8 -*-
"""
gui/app.py - NASTool GUI 主窗口

基于 nastool_modules (nastool-core/adapters/reporters/fixes) 的 customtkinter GUI。
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Optional

# ── GUI 框架 ─────────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ── 主题色（复用旧版深色科技风）───────────────────────────────────
BG = "#0d1117"
PANEL = "#161b22"
PANEL2 = "#1c2128"
BORDER = "#30363d"
TEXT = "#e6edf3"
DIM = "#8b949e"
GREEN = "#3fb950"
YELLOW = "#d29922"
RED = "#f85149"
BLUE = "#58a6ff"

SEV_COLORS = {
    "passed": GREEN,
    "warning": YELLOW,
    "critical": RED,
    "info": BLUE,
}
SEV_ICONS = {
    "passed": "[PASS]",
    "warning": "[WARN]",
    "critical": "[FAIL]",
    "info": "[INFO]",
}

# ── 业务层 ───────────────────────────────────────────────────────
from .integration import DiagnosisEngine


# ══════════════════════════════════════════════════════════════════
# 主窗口
# ══════════════════════════════════════════════════════════════════

class NastoolsGUI:
    VERSION = "1.0.0"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"NASTool - ARM NAS 诊断工具 v{NastoolsGUI.VERSION}")
        self.root.geometry("900x720")
        self.root.minsize(800, 600)
        self.root.configure(bg=BG)

        self.engine = DiagnosisEngine()
        self.results: list = []
        self.score: int = 0
        self.detecting = False
        self.log_queue: queue.Queue = queue.Queue()

        self._apply_theme()
        self._build_ui()

        t = threading.Thread(target=self._log_consumer, daemon=True)
        t.start()

        self.log("=" * 52)
        self.log(" NASTool GUI 诊断工具 v1.0")
        self.log(" 选择模式后点击 [开始诊断]")
        self.log("=" * 52)

    # ── 主题 ────────────────────────────────────────────────────

    def _apply_theme(self):
        self.root.configure(bg=BG)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, fieldbackground=PANEL2)
        style.configure("TFrame", background=PANEL)
        style.configure("Card.TFrame", background=PANEL, relief="flat", borderwidth=0)
        style.configure("TLabelframe", background=PANEL, foreground=TEXT, borderwidth=0)
        style.configure("TLabelframe.Label", background=PANEL, foreground=TEXT)
        style.configure("TLabel", background=PANEL, foreground=TEXT)
        style.configure("TButton", background=PANEL2, foreground=TEXT, borderwidth=1)
        style.configure("Green.TButton", background=GREEN, foreground=BG,
                        font=("Microsoft YaHei", 10, "bold"))
        style.configure("Red.TButton", background=RED, foreground=BG,
                        font=("Microsoft YaHei", 10, "bold"))
        style.configure("Yellow.TButton", background=YELLOW, foreground=BG,
                        font=("Microsoft YaHei", 10))
        style.configure("Blue.TButton", background=BLUE, foreground=BG,
                        font=("Microsoft YaHei", 10))
        style.configure("Treeview", background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, borderwidth=0, rowheight=22)
        style.configure("Treeview.Heading", background=PANEL2, foreground=DIM,
                        borderwidth=0)
        style.map("Treeview", background=[("selected", PANEL2)])

    # ── 日志 ────────────────────────────────────────────────────

    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{ts}] {msg}")

    def _log_consumer(self):
        while True:
            try:
                msg = self.log_queue.get(timeout=0.5)
                self.root.after(0, self._append_log, msg)
            except queue.Empty:
                continue

    def _append_log(self, msg: str):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    # ── UI 布局 ─────────────────────────────────────────────────

    def _build_ui(self):
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # 标题栏
        self._build_header(main)
        self._sep(main).pack(fill="x", pady=5)

        # 连接/模式选择面板
        self._build_mode_panel(main)
        self._sep(main).pack(fill="x", pady=5)

        # 设备信息 + 评分卡
        self._build_info_bar(main)
        self._sep(main).pack(fill="x", pady=5)

        # 操作按钮
        self._build_action_bar(main)
        self._sep(main).pack(fill="x", pady=5)

        # 结果表格
        self._build_results_tree(main)
        self._sep(main).pack(fill="x", pady=5)

        # 日志区
        self._build_log_area(main)

    def _build_header(self, parent):
        hdr = tk.Frame(parent, bg=BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="NASTool", font=("Consolas", 20, "bold"),
                 fg=GREEN, bg=BG).pack(side="left")
        tk.Label(hdr, text="ARM NAS 一键诊断工具",
                 font=("Microsoft YaHei", 10), fg=DIM, bg=BG).pack(side="left", padx=10)
        self.status_lbl = tk.Label(hdr, text="就绪",
                                   font=("Microsoft YaHei", 9), fg=DIM, bg=BG)
        self.status_lbl.pack(side="right")

    def _build_mode_panel(self, parent):
        pane = tk.LabelFrame(parent, text="诊断模式",
                             font=("Microsoft YaHei", 10, "bold"),
                             fg=TEXT, bg=PANEL, padx=12, pady=8,
                             relief="flat", bd=0)
        pane.pack(fill="x")

        self.mode_var = tk.StringVar(value="mock")
        modes = [
            ("mock", "模拟数据（无需设备，推荐测试）"),
            ("ssh", "SSH 远程连接（需真实NAS）"),
            ("http", "HTTP API 连接（需真实NAS）"),
        ]
        for val, desc in modes:
            rb = ttk.Radiobutton(pane, text=desc, variable=self.mode_var,
                                 value=val, command=self._on_mode_change)
            rb.pack(anchor="w")

        # SSH 参数（默认隐藏）
        self.ssh_frame = tk.Frame(pane, bg=PANEL)
        self.ssh_frame.pack(fill="x", pady=(5, 0))
        self._ssh_row(self.ssh_frame, "IP:", "ssh_host", "192.168.1.100")
        self._ssh_row(self.ssh_frame, "端口:", "ssh_port", "22")
        self._ssh_row(self.ssh_frame, "用户名:", "ssh_user", "admin")
        self._ssh_row(self.ssh_frame, "密码:", "ssh_pass", "")
        self.ssh_frame.pack_forget()
        
        # HTTP 参数（默认隐藏）
        self.http_frame = tk.Frame(pane, bg=PANEL)
        self.http_frame.pack(fill="x", pady=(5, 0))
        self._http_row(self.http_frame, "URL:", "http_url", "http://192.168.1.123:8000")
        self._http_row(self.http_frame, "API Key:", "http_api_key", "")
        self.http_frame.pack_forget()
        
        self._on_mode_change()

    def _ssh_row(self, parent, label, key, default=""):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, width=6, anchor="e",
                 font=("Microsoft YaHei", 9), fg=DIM, bg=PANEL).pack(side="left")
        ent = ttk.Entry(row, font=("Consolas", 9), width=30)
        ent.insert(0, default)
        if key == "ssh_pass":
            ent.configure(show="*")
        ent.pack(side="left", padx=(0, 5))
        setattr(self, f"ent_{key}", ent)
        
    def _http_row(self, parent, label, key, default=""):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, width=6, anchor="e",
                 font=("Microsoft YaHei", 9), fg=DIM, bg=PANEL).pack(side="left")
        ent = ttk.Entry(row, font=("Consolas", 9), width=40)
        ent.insert(0, default)
        if key == "http_api_key":
            ent.configure(show="*")
        ent.pack(side="left", padx=(0, 5))
        setattr(self, f"ent_{key}", ent)

    def _on_mode_change(self):
        if self.mode_var.get() == "ssh":
            self.ssh_frame.pack(fill="x", pady=(5, 0))
            self.http_frame.pack_forget()
        elif self.mode_var.get() == "http":
            self.http_frame.pack(fill="x", pady=(5, 0))
            self.ssh_frame.pack_forget()
        else:
            self.ssh_frame.pack_forget()
            self.http_frame.pack_forget()

    def _build_info_bar(self, parent):
        bar = tk.Frame(parent, bg=PANEL)
        bar.pack(fill="x")

        # 评分卡
        score_frm = tk.Frame(bar, bg=PANEL)
        score_frm.pack(side="left", padx=(0, 20))
        tk.Label(score_frm, text="健康评分", font=("Microsoft YaHei", 9),
                 fg=DIM, bg=PANEL).pack(anchor="w")
        self.score_lbl = tk.Label(score_frm, text="--/100",
                                  font=("Arial", 22, "bold"), fg=DIM, bg=PANEL)
        self.score_lbl.pack()

        # 统计卡
        stats = [("passed", "通过", GREEN), ("warning", "警告", YELLOW),
                 ("critical", "失败", RED), ("info", "提示", BLUE)]
        self.stat_lbls = {}
        for sev, lbl_txt, color in stats:
            frm = tk.Frame(bar, bg=PANEL)
            frm.pack(side="left", padx=(0, 15))
            self.stat_lbls[sev] = tk.Label(frm, text="0",
                                            font=("Arial", 16, "bold"),
                                            fg=color, bg=PANEL)
            self.stat_lbls[sev].pack()
            tk.Label(frm, text=lbl_txt, font=("Microsoft YaHei", 8), fg=DIM,
                     bg=PANEL).pack()

        # 总计
        frm = tk.Frame(bar, bg=PANEL)
        frm.pack(side="right")
        tk.Label(frm, text="检测项", font=("Microsoft YaHei", 9),
                 fg=DIM, bg=PANEL).pack(anchor="e")
        self.total_lbl = tk.Label(frm, text="0 项",
                                   font=("Arial", 16, "bold"), fg=TEXT, bg=PANEL)
        self.total_lbl.pack()

    def _build_action_bar(self, parent):
        bar = tk.Frame(parent, bg=PANEL)
        bar.pack(fill="x")

        self.btn_quick = ttk.Button(bar, text="快速诊断（90项）",
                                     command=lambda: self._do_run(full=False))
        self.btn_quick.pack(side="left", padx=(0, 8))

        self.btn_full = ttk.Button(bar, text="完整检测（93项）",
                                    command=lambda: self._do_run(full=True))
        self.btn_full.pack(side="left", padx=(0, 8))

        self.btn_stop = ttk.Button(bar, text="停止", state="disabled",
                                    command=self._do_stop)
        self.btn_stop.pack(side="left", padx=(0, 8))

        self.btn_export = ttk.Button(bar, text="导出报告",
                                      state="disabled", command=self._do_export)
        self.btn_export.pack(side="right")

        # Mock profile
        self.profile_var = tk.StringVar(value="healthy")
        profiles = [("healthy", "健康"), ("degraded", "亚健康"),
                    ("critical", "故障"), ("mixed", "混合")]
        for val, desc in profiles:
            ttk.Radiobutton(bar, text=desc, variable=self.profile_var,
                            value=val).pack(side="left", padx=4)

    def _build_results_tree(self, parent):
        lbl = tk.Label(parent, text="检测结果",
                       font=("Microsoft YaHei", 10, "bold"), fg=TEXT, bg=BG)
        lbl.pack(anchor="w")

        tree_frm = tk.Frame(parent, bg=PANEL)
        tree_frm.pack(fill="both", expand=True)

        cols = ("状态", "检查项", "分类", "当前值", "期望值", "建议")
        self.tree = ttk.Treeview(tree_frm, columns=cols, show="headings",
                                 height=12, selectmode="extended")

        col_widths = (65, 180, 70, 160, 160, 200)
        for col, w in zip(cols, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")

        scroll_y = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        self.tree.tag_configure("passed", foreground=GREEN)
        self.tree.tag_configure("warning", foreground=YELLOW)
        self.tree.tag_configure("critical", foreground=RED)
        self.tree.tag_configure("info", foreground=BLUE)

        self.tree.bind("<Double-Button-1>", self._on_result_doubleclick)

    def _build_log_area(self, parent):
        tk.Label(parent, text="运行日志", font=("Microsoft YaHei", 9),
                 fg=DIM, bg=BG).pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(
            parent, font=("Consolas", 9), fg=DIM, bg=BG,
            insertbackground=TEXT, relief="flat", bd=0, height=6,
            state="disabled", wrap="word")
        self.log_text.pack(fill="x", pady=(2, 0))

    def _sep(self, parent):
        sep = tk.Frame(parent, bg=BORDER, height=1)
        return sep

    # ── 诊断执行 ────────────────────────────────────────────────

    def _do_run(self, full: bool):
        if self.detecting:
            return
        mode = self.mode_var.get()
        profile = self.profile_var.get()
        self.log(f"开始诊断: mode={mode}, full={full}, profile={profile}")

        self._set_running(True)
        self._clear_results()

        # 构建 adapter 参数
        adapter_type = ""
        adapter_kwargs = {}
        if mode == "ssh":
            adapter_type = "ssh"
            adapter_kwargs = {
                "host": self.ent_ssh_host.get().strip(),
                "port": int(self.ent_ssh_port.get().strip() or "22"),
                "username": self.ent_ssh_user.get().strip(),
                "password": self.ent_ssh_pass.get().strip(),
            }
            self.log(f"SSH 目标: {adapter_kwargs['host']}:{adapter_kwargs['port']}"
                     f"@{adapter_kwargs['username']}")
        elif mode == "http":
            adapter_type = "http"
            adapter_kwargs = {
                "target_url": self.ent_http_url.get().strip(),
                "api_key": self.ent_http_api_key.get().strip() or None,
            }
            self.log(f"HTTP 目标: {adapter_kwargs['target_url']}")

        def worker():
            try:
                results, score = self.engine.run(
                    mock=(mode == "mock"),
                    profile=profile,
                    full_mode=full,
                    progress_callback=self._on_progress,
                    adapter_type=adapter_type,
                    adapter_kwargs=adapter_kwargs or None,
                )
                self.results = results
                self.score = score
                self.root.after(0, self._on_done, results, score)
            except Exception as e:
                self.root.after(0, self._on_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_progress(self, current: int, total: int, check_id: str):
        self.root.after(0, self._update_progress, current, total, check_id)

    def _update_progress(self, current: int, total: int, check_id: str):
        self.status_lbl.config(text=f"检测中 {current}/{total}")
        self.log(f"  [{current}/{total}] {check_id}")

    def _on_done(self, results: list, score: int):
        self._set_running(False)
        self.btn_export.config(state="normal")
        self._populate_tree(results)
        self._update_stats(results, score)
        self.log(f"诊断完成: {len(results)} 项, 评分 {score}/100")
        if score >= 80:
            self.log("[PASS] 系统健康，继续保持！")
        elif score >= 60:
            self.log("[WARN] 系统有改进空间，建议关注警告项。")
        else:
            self.log("[FAIL] 系统存在严重问题，建议立即处理。")

    def _on_error(self, msg: str):
        self._set_running(False)
        self.log(f"[ERROR] {msg}")
        messagebox.showerror("诊断错误", msg)

    def _do_stop(self):
        self.log("用户中断诊断")

    def _set_running(self, running: bool):
        self.detecting = running
        state = "disabled" if running else "normal"
        self.btn_quick.config(state=state)
        self.btn_full.config(state=state)
        self.btn_stop.config(state="normal" if running else "disabled")
        self.status_lbl.config(text="诊断中..." if running else "就绪")

    def _clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.score_lbl.config(text="--/100", fg=DIM)
        self.total_lbl.config(text="0 项")
        for key in self.stat_lbls:
            self.stat_lbls[key].config(text="0")

    def _populate_tree(self, results: list):
        for r in results:
            values = (r.title, r.category, r.current, r.expected,
                      r.fix_title if r.fix_available else "-")
            icon = SEV_ICONS.get(r.severity, "[?]")
            item_id = self.tree.insert("", "end", values=(
                f"{icon} {r.severity.upper()}",
                r.title,
                r.category,
                r.current,
                r.expected,
                r.fix_title if r.fix_available else "-",
            ), tags=(r.severity,))
            if not r.passed:
                self.tree.item(item_id, open=False)

    def _update_stats(self, results: list, score: int):
        self.total_lbl.config(text=f"{len(results)} 项")
        self.score_lbl.config(text=f"{score}/100",
                               fg=GREEN if score >= 80 else YELLOW if score >= 60 else RED)
        counts = {"passed": 0, "warning": 0, "critical": 0, "info": 0}
        for r in results:
            sev = r.severity
            if sev in counts:
                counts[sev] += 1
        for key, lbl in self.stat_lbls.items():
            lbl.config(text=str(counts.get(key, 0)))

    def _on_result_doubleclick(self, event):
        item = self.tree.selection()
        if not item:
            return
        idx = self.tree.index(item[0])
        if idx < len(self.results):
            r = self.results[idx]
            self._show_detail(r)

    def _show_detail(self, r):
        lines = [
            f"检查项: {r.title}",
            f"ID: {r.check_id}",
            f"分类: {r.category}",
            f"状态: {r.severity.upper()} ({'通过' if r.passed else '失败'})",
            f"当前值: {r.current}",
            f"期望值: {r.expected}",
            f"详情: {r.message}",
        ]
        if r.fix_available:
            lines.append(f"修复建议: {r.fix_title}")
            lines.append(f"风险等级: {r.fix_risk.upper()}")
        messagebox.showinfo(r.title, "\n".join(lines))

    def _do_export(self):
        if not self.results:
            return
        import json, os
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("文本文件", "*.txt")],
        )
        if not path:
            return
        if path.endswith(".json"):
            data = [{
                "check_id": r.check_id, "title": r.title, "category": r.category,
                "severity": r.severity, "passed": r.passed,
                "current": r.current, "expected": r.expected,
                "message": r.message, "fix_available": r.fix_available,
                "fix_title": r.fix_title,
            } for r in self.results]
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"score": self.score, "results": data}, f, ensure_ascii=False, indent=2)
        else:
            lines = [f"NASTool 诊断报告 (评分: {self.score}/100)", "=" * 50, ""]
            for r in self.results:
                icon = SEV_ICONS.get(r.severity, "?")
                lines.append(f"{icon} {r.title} [{r.category}]")
                lines.append(f"   当前: {r.current}  |  期望: {r.expected}")
                if r.message:
                    lines.append(f"   {r.message}")
                if r.fix_available:
                    lines.append(f"   修复: {r.fix_title}")
                lines.append("")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        self.log(f"报告已导出: {path}")
        messagebox.showinfo("导出成功", f"报告已保存至:\n{path}")


# ══════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    app = NastoolsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
