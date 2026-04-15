# -*- coding: utf-8 -*-
"""
gui/app.py — nastools 主窗口

本文件只负责 GUI 逻辑（~430行），
不包含任何检测脚本（由 integration/remote.py 提供）。
"""

import sys
import os
import time
import queue
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ── 内部模块 ─────────────────────────────────────────────────────
from config.theme import (
    BG,
    PANEL,
    PANEL2,
    BORDER,
    TEXT,
    DIM,
    GREEN,
    YELLOW,
    RED,
    BLUE,
    ACCENT,
    SEV_COLORS,
    SEV_ICONS,
    CHECK_DEFS,
    apply_theme,
)
from core.ssh import SSHConnection

from integration.remote import RemoteExecutor
from scripts.deploy import (
    NAS_DEPLOY_SCRIPT,
    NAS_ROLLBACK_SCRIPT,
    NAS_UNINSTALL_SCRIPT,
    BACKUP_DIR,
    INSTALL_DIR,
)
from utils.notifications import confirm_danger


# ══════════════════════════════════════════════════════════════════
# 主程序
# ══════════════════════════════════════════════════════════════════


class NastoolsApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("nastools - ARM NAS 诊断与部署工具 v1.1 [USB V3.0-alpha]")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.ssh = SSHConnection()
        self.executor = RemoteExecutor(ssh=self.ssh)
        self.results: list = []
        self.detecting = False
        self.deploying = False
        self.log_queue: queue.Queue = queue.Queue()
        self.threads: list = []

        apply_theme(root)
        self._build_ui()

        t = threading.Thread(target=self._log_consumer, daemon=True)
        t.start()
        self.threads.append(t)

        self.log("=" * 50)
        self.log(" nastools ARM NAS 诊断工具 v1.2 (V3.0-alpha USB)")
        self.log(" 输入设备 IP、用户名、密码后点击「连接」")
        self.log("=" * 50)

    # ── 日志 ───────────────────────────────────────────────────────

    def log(self, msg: str):
        """添加日志到显示区域（线程安全）"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {msg}")

    def _log_consumer(self):
        """后台线程：消费日志队列并显示"""
        while True:
            try:
                msg = self.log_queue.get(timeout=0.5)
                self.root.after(0, self._append_log, msg)
            except queue.Empty:
                continue

    def _append_log(self, msg: str):
        """在日志区域追加文本"""
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    # ── UI 布局 ───────────────────────────────────────────────────

    def _build_ui(self):
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # 标题栏
        hdr = tk.Frame(main, bg=BG)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(
            hdr, text="nastools", font=("Consolas", 18, "bold"), fg=ACCENT, bg=BG
        ).pack(side="left")
        tk.Label(
            hdr,
            text="ARM NAS 一键诊断与部署",
            font=("Microsoft YaHei", 10),
            fg=DIM,
            bg=BG,
        ).pack(side="left", padx=8)
        tk.Label(hdr, text="v1.2 (USB)", font=("Consolas", 9), fg=BORDER, bg=BG).pack(
            side="left"
        )
        self.status_label = tk.Label(
            hdr, text="未连接", font=("Microsoft YaHei", 9), fg=DIM, bg=BG
        )
        self.status_label.pack(side="right")

        self._sep(main).pack(fill="x", pady=5)

        # 连接面板
        self._build_connection_panel(main)
        self._sep(main).pack(fill="x", pady=5)

        # 设备信息卡
        self._build_device_card(main)
        self._sep(main).pack(fill="x", pady=5)

        # 操作按钮
        self._build_action_buttons(main)
        self._sep(main).pack(fill="x", pady=5)

        # 结果表格
        tk.Label(
            main, text="检测结果", fg=TEXT, bg=BG, font=("Microsoft YaHei", 10, "bold")
        ).pack(anchor="w")
        self._build_results_tree(main)
        self._sep(main).pack(fill="x", pady=5)

        # 日志区
        tk.Label(
            main, text="运行日志", fg=DIM, bg=BG, font=("Microsoft YaHei", 9)
        ).pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(
            main,
            font=("Consolas", 9),
            fg=DIM,
            bg=BG,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            height=6,
            state="disabled",
        )
        self.log_area.pack(fill="both", expand=False, pady=(2, 0))

    def _build_connection_panel(self, parent):
        conn = tk.LabelFrame(
            parent,
            text="连接设备",
            font=("Microsoft YaHei", 10, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=12,
            pady=10,
            relief="flat",
            bd=0,
        )
        conn.pack(fill="x", pady=(0, 8))

        row1 = tk.Frame(conn, bg=PANEL)
        row1.pack(fill="x", pady=2)
        tk.Label(
            row1,
            text="IP / 主机名",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=12,
            anchor="e",
        ).pack(side="left")
        self.host_var = tk.StringVar(value="")
        tk.Entry(
            row1,
            textvariable=self.host_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 10),
            relief="flat",
            width=22,
            bd=0,
        ).pack(side="left", padx=4)
        tk.Label(
            row1,
            text="端口",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=6,
            anchor="e",
        ).pack(side="left")
        self.port_var = tk.StringVar(value="22")
        tk.Entry(
            row1,
            textvariable=self.port_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 10),
            relief="flat",
            width=7,
            bd=0,
        ).pack(side="left")

        row2 = tk.Frame(conn, bg=PANEL)
        row2.pack(fill="x", pady=2)
        tk.Label(
            row2,
            text="用户名",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=12,
            anchor="e",
        ).pack(side="left")
        self.user_var = tk.StringVar(value="root")
        tk.Entry(
            row2,
            textvariable=self.user_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 10),
            relief="flat",
            width=16,
            bd=0,
        ).pack(side="left", padx=4)
        tk.Label(
            row2,
            text="密码",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=6,
            anchor="e",
        ).pack(side="left")
        self.pass_var = tk.StringVar(value="")
        tk.Entry(
            row2,
            textvariable=self.pass_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 10),
            relief="flat",
            width=16,
            bd=0,
            show="●",
        ).pack(side="left")

        row3 = tk.Frame(conn, bg=PANEL)
        row3.pack(fill="x", pady=(6, 0))
        self.connect_btn = tk.Button(
            row3,
            text="连接设备",
            font=("Microsoft YaHei", 10, "bold"),
            fg=BG,
            bg=GREEN,
            activebackground=GREEN,
            relief="flat",
            bd=0,
            padx=16,
            pady=4,
            cursor="hand2",
            command=self._on_connect,
        )
        self.connect_btn.pack(side="left")
        self.disconnect_btn = tk.Button(
            row3,
            text="断开",
            font=("Microsoft YaHei", 9),
            fg=TEXT,
            bg=BORDER,
            activebackground=BORDER,
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            state="disabled",
            command=self._on_disconnect,
        )
        self.disconnect_btn.pack(side="left", padx=4)

        # 本地备份按钮
        self.backup_btn = tk.Button(
            row3,
            text="本地备份",
            font=("Microsoft YaHei", 9),
            fg=TEXT,
            bg=BLUE,
            activebackground=BLUE,
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._on_local_backup,
        )
        self.backup_btn.pack(side="left", padx=8)

    def _build_device_card(self, parent):
        self.info_card = tk.LabelFrame(
            parent,
            text="设备信息",
            font=("Microsoft YaHei", 10, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=12,
            pady=8,
            relief="flat",
            bd=0,
        )
        self.info_card.pack(fill="x", pady=(0, 8))
        self.info_card.pack_forget()
        self.info_labels: list = []
        for txt in ["系统: ", "架构: ", "Python: "]:
            r = tk.Frame(self.info_card, bg=PANEL)
            r.pack(fill="x")
            tk.Label(
                r,
                text=txt,
                fg=DIM,
                bg=PANEL,
                font=("Microsoft YaHei", 9),
                width=10,
                anchor="e",
            ).pack(side="left")
            lbl = tk.Label(r, text="—", fg=TEXT, bg=PANEL, font=("Consolas", 9))
            lbl.pack(side="left")
            self.info_labels.append(lbl)

    def _build_action_buttons(self, parent):
        btn_row = tk.Frame(parent, bg=BG)
        btn_row.pack(fill="x", pady=(0, 5))
        self.detect_btn = tk.Button(
            btn_row,
            text="开始检测",
            font=("Microsoft YaHei", 11, "bold"),
            fg=BG,
            bg=GREEN,
            activebackground=GREEN,
            relief="flat",
            bd=0,
            padx=18,
            pady=5,
            cursor="hand2",
            state="disabled",
            command=self._on_detect,
        )
        self.detect_btn.pack(side="left")
        self.fix_btn = tk.Button(
            btn_row,
            text="修复选中项",
            font=("Microsoft YaHei", 10, "bold"),
            fg=BG,
            bg=YELLOW,
            activebackground=YELLOW,
            relief="flat",
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            state="disabled",
            command=self._on_fix,
        )
        self.fix_btn.pack(side="left", padx=6)
        self.deploy_btn = tk.Button(
            btn_row,
            text="部署 NAS",
            font=("Microsoft YaHei", 10, "bold"),
            fg=BG,
            bg=GREEN,
            activebackground=GREEN,
            relief="flat",
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            state="disabled",
            command=self._on_deploy,
        )
        self.deploy_btn.pack(side="left")
        tk.Label(btn_row, text="  ", fg=DIM, bg=BG, font=("", 6)).pack(side="left")
        self.rollback_btn = tk.Button(
            btn_row,
            text="回滚",
            font=("Microsoft YaHei", 10),
            fg=BLUE,
            bg=PANEL2,
            activebackground=PANEL2,
            activeforeground=BLUE,
            relief="flat",
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            state="disabled",
            command=self._on_rollback,
        )
        self.rollback_btn.pack(side="left")
        self.history_btn = tk.Button(
            btn_row,
            text="历史",
            font=("Microsoft YaHei", 10),
            fg=TEXT,
            bg=PANEL2,
            activebackground=PANEL2,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            command=self._on_history,
        )
        self.history_btn.pack(side="left", padx=4)
        self.uninstall_btn = tk.Button(
            btn_row,
            text="卸载",
            font=("Microsoft YaHei", 10),
            fg=RED,
            bg=PANEL2,
            activebackground=PANEL2,
            activeforeground=RED,
            relief="flat",
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            state="disabled",
            command=self._on_uninstall,
        )
        self.uninstall_btn.pack(side="left", padx=4)
        # Relay Server 远程管理
        self.relay_btn = tk.Button(
            btn_row,
            text="Relay",
            font=("Microsoft YaHei", 10),
            fg=ACCENT,
            bg=PANEL2,
            activebackground=PANEL2,
            activeforeground=ACCENT,
            relief="flat",
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            command=self._on_relay,
        )
        self.relay_btn.pack(side="left", padx=4)
        # USB 直连（V3.0-alpha）
        self.usb_btn = tk.Button(
            btn_row,
            text="USB",
            font=("Microsoft YaHei", 10),
            fg=ACCENT,
            bg=PANEL2,
            activebackground=PANEL2,
            activeforeground=ACCENT,
            relief="flat",
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            command=self._on_usb,
        )
        self.usb_btn.pack(side="left", padx=4)
        tk.Label(btn_row, text="", fg=DIM, bg=BG, font=("", 6)).pack(
            side="left", fill="x", expand=True
        )
        self.sel_label = tk.Label(
            btn_row, text="已选择 0 项", fg=DIM, bg=BG, font=("Microsoft YaHei", 9)
        )
        self.sel_label.pack(side="right")

    def _build_results_tree(self, parent):
        cols = ("#", "状态", "检测项", "结果", "可修复")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings", height=10)
        self.tree.heading("#", text="#")
        self.tree.heading("状态", text="状态")
        self.tree.heading("检测项", text="检测项")
        self.tree.heading("结果", text="结果")
        self.tree.heading("可修复", text="可修复")
        self.tree.column("#", width=30, anchor="center")
        self.tree.column("状态", width=50, anchor="center")
        self.tree.column("检测项", width=110, anchor="w")
        self.tree.column("结果", width=320, anchor="w")
        self.tree.column("可修复", width=70, anchor="center")
        for tag, color in SEV_COLORS.items():
            self.tree.tag_configure(tag, foreground=color)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        sb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        f_tree = tk.Frame(parent, bg=BG)
        f_tree.pack(fill="both", expand=True, pady=(2, 5))
        self.tree.pack(in_=f_tree, side="left", fill="both", expand=True)
        sb.pack(in_=f_tree, side="right", fill="y")

    def _sep(self, parent):
        f = tk.Frame(parent, bg=BORDER, height=1)
        return f

    # ── 连接事件 ─────────────────────────────────────────────────

    def _on_connect(self):
        host = self.host_var.get().strip()
        port = self.port_var.get().strip() or "22"
        user = self.user_var.get().strip()
        password = self.pass_var.get()

        if not host:
            messagebox.showwarning("提示", "请输入设备 IP 地址", parent=self.root)
            return
        if not user:
            messagebox.showwarning("提示", "请输入用户名", parent=self.root)
            return
        if not password:
            messagebox.showwarning("提示", "请输入密码", parent=self.root)
            return

        self._set_conn_buttons(connecting=True)
        self.log(f"正在连接 {host}:{port}...")
        self.log(f"用户名: {user}")

        def do_connect():
            ok, msg = self.ssh.connect(host, int(port), user, password)
            self.log_queue.put(("conn_done", ok, msg))

        threading.Thread(target=do_connect, daemon=True).start()
        self.root.after(200, self._check_conn_queue)

    def _check_conn_queue(self):
        try:
            while True:
                kind, ok, msg = self.log_queue.get_nowait()
                if kind == "conn_done":
                    self._handle_conn_done(ok, msg)
                    break
                elif kind == "log":
                    self.log(msg)
                else:
                    self.log_queue.put((kind, ok, msg))
                    break
        except queue.Empty:
            pass
        if self.detecting or self.deploying:
            self.root.after(200, self._check_conn_queue)

    def _handle_conn_done(self, ok, msg):
        self._set_conn_buttons(connecting=False)
        if ok:
            self.log(f"连接成功")
            self.status_label.config(text="已连接", fg=GREEN)
            self.detect_btn.config(state="normal")
            self.deploy_btn.config(state="normal")
            self.rollback_btn.config(state="normal")
            self.uninstall_btn.config(state="normal")
            threading.Thread(target=self._fetch_device_info, daemon=True).start()
        else:
            self.log(f"连接失败: {msg}")
            self.rollback_btn.config(state="disabled")
            self.uninstall_btn.config(state="disabled")
            messagebox.showerror("连接失败", msg, parent=self.root)

    def _fetch_device_info(self):
        ec, os_ver, _ = self.ssh.exec(
            "uname -a 2>&1 || cat /etc/os-release 2>&1 | head -3"
        )
        ec2, arch, _ = self.ssh.exec("uname -m 2>&1")
        ec3, py_ver, _ = self.ssh.exec(
            "python3 --version 2>&1 || python --version 2>&1"
        )
        self.log_queue.put(("log", f"设备: {os_ver[:60]}"))
        self.log_queue.put(("device_info", os_ver[:80], arch.strip(), py_ver.strip()))

    def _set_conn_buttons(self, connecting: bool):
        if connecting:
            self.connect_btn.config(state="disabled", text="连接中...")
            self.disconnect_btn.config(state="disabled")
        else:
            self.connect_btn.config(state="normal", text="连接设备")
            self.disconnect_btn.config(state="normal")

    def _on_disconnect(self):
        self.ssh.close()
        self.log("已断开连接")
        self.status_label.config(text="未连接", fg=DIM)
        self.detect_btn.config(state="disabled")
        self.fix_btn.config(state="disabled")
        self.deploy_btn.config(state="disabled")
        self.rollback_btn.config(state="disabled")
        self.connect_btn.config(state="normal")
        self.info_card.pack_forget()
        self._clear_tree()

    # ── 检测事件 ─────────────────────────────────────────────────

    def _on_detect(self):
        if self.detecting:
            return
        self.detecting = True
        self.detect_btn.config(state="disabled", text="检测中...")
        self.fix_btn.config(state="disabled")
        self._clear_tree()
        self.log(f"\n{'=' * 50}")
        self.log("开始检测（调用 nastool 库）...")

        def do_detect():
            # 自动检测最优模式（SSH已连接由remote.py检测nastool是否在设备上）
            self.log_queue.put(("log", "正在检测设备环境，请稍候..."))
            results = self.executor.run()  # remote_mode=None → 自动检测
            self.log_queue.put(("detect_done", True, results))

        t = threading.Thread(target=do_detect, daemon=True)
        t.start()
        # 兜底：30s强制结束，防止任何遗留阻塞
        timer = threading.Timer(
            30.0,
            lambda: (
                t.is_alive()
                and self.log_queue.put(
                    (
                        "detect_done",
                        False,
                        [
                            {
                                "name": "timeout",
                                "severity": "critical",
                                "message": "检测超时（30s），请检查网络或设备连接",
                                "fix_id": "",
                            }
                        ],
                    )
                )
            ),
        )
        timer.start()
        self.root.after(200, self._check_detect_queue)

    def _check_detect_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    self.log(item[1])
                elif kind == "conn_done":
                    pass
                elif kind == "device_info":
                    self._show_device_info(item[1], item[2], item[3])
                elif kind == "detect_done":
                    self._handle_detect_done(item[2])
                    break
                else:
                    self.log_queue.put(item)
                    break
        except queue.Empty:
            pass
        if self.detecting:
            self.root.after(200, self._check_detect_queue)

    def _handle_detect_done(self, results: list):
        self.detecting = False
        self.detect_btn.config(state="normal", text="开始检测")
        if not results:
            self.log("未获取到检测结果")
            return

        self.results = results
        for i, r in enumerate(results, 1):
            sev = r.get("severity", "info")
            name = r.get("name", "?")
            msg = r.get("message", "")
            fix_id = r.get("fix_id", "")
            has_fix = bool(fix_id)
            icon = SEV_ICONS.get(sev, "?")
            title = CHECK_DEFS.get(name, {}).get("title", name)
            vals = (str(i), icon, title, msg[:80], "可修复" if has_fix else "")
            self.tree.insert("", "end", values=vals, tags=(sev,))

        passed = sum(1 for r in results if r.get("severity") == "passed")
        warn = sum(1 for r in results if r.get("severity") in ("warning", "warn"))
        crit = sum(1 for r in results if r.get("severity") == "critical")
        fixable = sum(1 for r in results if r.get("fix_id", ""))
        self.log(
            f"检测完成: 通过 {passed}  警告 {warn}  严重 {crit}  |  可修复 {fixable} 项"
        )
        self.sel_label.config(text=f"可修复 {fixable} 项")
        self.fix_btn.config(state="normal" if fixable else "disabled")

        # 保存检测历史
        self._save_detect_history(results)

        if crit > 0:
            messagebox.showwarning(
                "检测完成", f"发现 {crit} 个严重问题，建议优先修复", parent=self.root
            )

    def _show_device_info(self, os_ver, arch, py_ver):
        try:
            self.info_card.pack(fill="x", pady=(0, 8))
            for lbl in self.info_labels:
                lbl.config(text="—")
            lines = os_ver.split("\n")
            if lines:
                self.info_labels[0].config(text=lines[0][:80])
            self.info_labels[1].config(text=arch or "—")
            self.info_labels[2].config(text=py_ver or "—")
        except Exception:
            pass

    def _on_tree_select(self, event):
        pass

    # ── 修复事件 ─────────────────────────────────────────────────

    # ── 修复 ────────────────────────────────────────────────────────────────

    def _on_fix(self):
        # 收集选中的可修复项
        selected = []
        for item in self.tree.selection():
            vals = self.tree.item(item, "values")
            if vals and vals[4] == "可修复":
                idx = int(vals[0]) - 1
                if 0 <= idx < len(self.results):
                    r = self.results[idx]
                    if r.get("fix_id"):
                        selected.append(r)
        if not selected:
            messagebox.showinfo(
                "无可修复项", "当前没有可自动修复的项目", parent=self.root
            )
            return

        # 按最高风险分级
        RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
        highest = max(
            (r.get("fix_risk", "low") for r in selected),
            key=lambda x: RISK_ORDER.get(x, 0),
        )
        risk = highest  # "high" / "medium" / "low"

        items = "\n".join(
            f"  - {r.get('fix_title', r.get('name'))}（{r.get('fix_warn', '')}）"
            for r in selected
        )

        ok = confirm_danger(
            parent=self.root,
            title=f"修复 {len(selected)} 项",
            risk=risk,
            message=f"将修复以下 {len(selected)} 项：\n{items}",
            details=f"风险等级：{highest.upper()}（{len(selected)} 项中最高）",
        )
        if not ok:
            return

        self.log(f"\n{'=' * 50}")
        self.log(f"开始修复 {len(selected)} 项...")

        def do_fix():
            for i, r in enumerate(selected, 1):
                fid = r.get("fix_id")
                title = r.get("fix_title") or r.get("name")
                self.log_queue.put(("log", f"[{i}/{len(selected)}] {title}..."))
                ok2, out2 = self.executor.execute_fix(fid)
                if ok2:
                    self.log_queue.put(("log", f"  OK {title}: {out2[:80]}"))
                else:
                    self.log_queue.put(("log", f"  FAIL {title}: {out2[:80]}"))
            self.log_queue.put(("log", "修复流程结束，建议重新检测确认"))
            self.log_queue.put(("fix_done", None, None))

        threading.Thread(target=do_fix, daemon=True).start()
        self.root.after(200, self._check_fix_queue)

    def _check_fix_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    self.log(item[1])
                elif kind == "fix_done":
                    return
                else:
                    self.log_queue.put(item)
                    break
        except queue.Empty:
            pass
        self.root.after(300, self._check_fix_queue)

    # ── 部署 ────────────────────────────────────────────────────────────────

    def _on_deploy(self):
        """部署按钮：先检测版本，再执行部署"""
        if not self.ssh or not self.ssh.client:
            messagebox.showwarning("未连接", "请先连接 ARM 设备", parent=self.root)
            return

        self.log(f"\n{'=' * 50}")
        self.log("nastools v1.1 - 部署前环境检测")
        self.log("")

        # ── 步骤 1：版本检测 ───────────────────────────────────────
        def do_deploy():
            try:
                # 导入版本检测模块
                import sys
                import os

                nastool_path = os.path.abspath(
                    os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "nastool",
                    )
                )
                if nastool_path not in sys.path:
                    sys.path.insert(0, nastool_path)
                from fixes.system.check_versions import get_remote_deployment_readiness

                self.log_queue.put(("log", "[1/3] 检测设备环境版本..."))

                # 执行远程版本检测
                readiness = get_remote_deployment_readiness(self.ssh)
                versions = readiness.get("versions", {})

                # 输出版本信息
                py = versions.get("python", {})
                dk = versions.get("docker", {})
                cu = versions.get("cuda", {})

                self.log_queue.put(("log", f"  Python: {py.get('message', '未知')}"))
                self.log_queue.put(("log", f"  Docker: {dk.get('message', '未知')}"))
                if cu.get("installed"):
                    self.log_queue.put(
                        ("log", f"  CUDA:   {cu.get('message', '未知')}")
                    )

                # 检查是否就绪
                if not readiness.get("ready"):
                    issues = readiness.get("issues", [])
                    suggestions = readiness.get("suggestions", [])
                    self.log_queue.put(("log", ""))
                    self.log_queue.put(("log", "✗ 环境不满足部署要求："))
                    for issue in issues:
                        self.log_queue.put(("log", f"  - {issue}"))
                    self.log_queue.put(("log", ""))
                    self.log_queue.put(("log", "建议："))
                    for sug in suggestions:
                        self.log_queue.put(("log", f"  - {sug}"))
                    self.log_queue.put(("deploy_done", False, "环境不满足要求"))
                    return

                self.log_queue.put(("log", "✓ 环境检测通过"))

                # ── 步骤 2：确认部署 ─────────────────────────────────────
                self.log_queue.put(("log", ""))
                self.log_queue.put(("log", "[2/3] 准备部署 AI-NAS 系统..."))
                self.log_queue.put(("confirm_deploy", None, None))

            except Exception as e:
                self.log_queue.put(("log", f"版本检测出错: {e}"))
                self.log_queue.put(("deploy_done", False, str(e)))

        threading.Thread(target=do_deploy, daemon=True).start()
        self.root.after(200, self._check_deploy_queue)

    def _check_deploy_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    self.log(item[1])
                elif kind == "confirm_deploy":
                    # 弹出确认框
                    ok = confirm_danger(
                        parent=self.root,
                        title="部署 NAS 系统",
                        risk="high",
                        message="将在设备上部署 AI-NAS 系统",
                        details=(
                            "部署路径: /opt/ai-nas\n服务端口: 8000\n数据目录: /nas"
                        ),
                        warnings=[
                            "部署前会自动备份现有版本",
                            "部署后可通过「回滚」恢复",
                            "服务将自动启动",
                        ],
                    )
                    if ok:
                        self.log("用户确认部署")
                        threading.Thread(
                            target=self._do_deploy_exec, daemon=True
                        ).start()
                    else:
                        self.log("用户取消部署")
                    return
                elif kind == "deploy_done":
                    ok, msg = item[1], item[2]
                    if ok:
                        self.log(f"\n{'=' * 50}")
                        self.log("✓ 部署成功!")
                        messagebox.showinfo("部署完成", msg, parent=self.root)
                    else:
                        self.log(f"\n{'=' * 50}")
                        self.log(f"✗ 部署失败: {msg}")
                        messagebox.showerror("部署失败", msg, parent=self.root)
                    return
                elif kind == "verify_failed":
                    msg, retry_count = item[1], item[2]
                    self.log(f"\n{'=' * 50}")
                    self.log(f"⚠ 部署完成但验证失败: {msg}")

                    # 询问是否重试
                    if retry_count < 2:
                        resp = messagebox.askyesno(
                            "验证失败",
                            f"部署完成但验证失败:\n{msg}\n\n是否重试验证？",
                            parent=self.root,
                        )
                        if resp:
                            self._on_verify_retry(retry_count)
                        else:
                            messagebox.showwarning(
                                "请手动检查",
                                "部署已完成，请手动检查服务状态:\n"
                                "  systemctl status ai-nas-arm\n"
                                "  curl http://localhost:8000/health",
                                parent=self.root,
                            )
                    else:
                        messagebox.showerror(
                            "验证失败",
                            f"验证失败:\n{msg}\n\n请手动检查服务状态",
                            parent=self.root,
                        )
                    return
                else:
                    self.log_queue.put(item)
                    break
        except queue.Empty:
            pass
        self.root.after(300, self._check_deploy_queue)

    def _do_deploy_exec(self):
        """执行实际部署（在确认后调用）"""
        try:
            self.log_queue.put(("log", "[3/4] 执行部署脚本..."))

            # 执行部署脚本
            from scripts.deploy import NAS_DEPLOY_SCRIPT

            ec, out, _ = self.ssh.exec(NAS_DEPLOY_SCRIPT, timeout=300)

            if ec == 0:
                self.log_queue.put(("log", f"  {out[:500]}"))

                # 部署后验证
                self.log_queue.put(("log", "\n[4/4] 部署后验证..."))
                self._do_verify_deploy()
            else:
                self.log_queue.put(("log", f"  部署脚本执行失败: {out[:500]}"))
                self.log_queue.put(("deploy_done", False, out[:200]))
        except Exception as e:
            self.log_queue.put(("deploy_done", False, str(e)))

    def _do_verify_deploy(self, retry_count: int = 0):
        """部署后验证"""
        try:
            from scripts.verify import (
                get_quick_verify_script,
                parse_quick_verify_output,
            )

            # 执行验证脚本
            script = get_quick_verify_script(port=8000)
            ec, out, _ = self.ssh.exec(script, timeout=30)

            if ec == 0:
                ok, msg = parse_quick_verify_output(out)
                if ok:
                    self.log_queue.put(("log", f"  ✓ {msg}"))
                    self.log_queue.put(
                        ("deploy_done", True, "AI-NAS 系统已部署并验证通过")
                    )
                else:
                    self.log_queue.put(("log", f"  ✗ {msg}"))
                    self.log_queue.put(("verify_failed", msg, retry_count))
            else:
                self.log_queue.put(("log", f"  验证脚本执行失败: {out[:200]}"))
                self.log_queue.put(("verify_failed", "验证脚本执行失败", retry_count))

        except Exception as e:
            self.log_queue.put(("log", f"  验证异常: {str(e)[:100]}"))
            self.log_queue.put(("verify_failed", str(e), retry_count))

    def _on_verify_retry(self, retry_count: int):
        """重试验证"""
        if retry_count >= 2:  # 最多 3 次（0, 1, 2）
            messagebox.showerror(
                "验证失败", "验证重试 3 次仍失败，请手动检查服务状态", parent=self.root
            )
            return

        self.log(f"\n重试验证 ({retry_count + 2}/3)...")
        self.root.after(5000, lambda: self._do_verify_deploy(retry_count + 1))

    # ── 本地备份 ───────────────────────────────────────────────────────────

    def _on_local_backup(self):
        """本地备份按钮：打开本地备份管理对话框"""
        from gui.local_backup_dialog import show_local_backup_dialog

        show_local_backup_dialog(self.root)

    # ── 回滚 ────────────────────────────────────────────────────────────────

    def _on_rollback(self):
        """回滚按钮：打开备份选择对话框"""
        if not self.ssh or not self.ssh.client:
            messagebox.showwarning("未连接", "请先连接 ARM 设备", parent=self.root)
            return

        # 导入并显示回滚对话框
        from gui.rollback_dialog import show_rollback_dialog

        def on_rollback_done(backup_info):
            """回滚完成回调"""
            self.log(f"\n{'=' * 50}")
            self.log(f"OK 已恢复备份: {backup_info.filename}")
            self.log(f"   类型: {backup_info.type_label}")
            self.log(f"   时间: {backup_info.mtime}")

        show_rollback_dialog(self.root, self.ssh, on_rollback=on_rollback_done)

    # ── 历史 ────────────────────────────────────────────────────────────────

    def _on_history(self):
        """历史按钮：打开历史查看对话框"""
        # 获取当前设备 IP
        current_ip = self.host_var.get().strip()

        # 导入并显示历史对话框
        from gui.history_dialog import show_history_dialog

        show_history_dialog(self.root, current_device=current_ip)

    def _save_detect_history(self, results: list):
        """保存检测历史到本地"""
        if not results:
            return

        # 获取设备 IP
        device_ip = self.host_var.get().strip()
        if not device_ip:
            return

        try:
            # 导入历史管理器
            import os
            import sys
            import importlib.util

            pkg_root = os.path.dirname(os.path.dirname(__file__))
            hist_path = os.path.join(pkg_root, "utils", "detect_history.py")

            spec = importlib.util.spec_from_file_location("detect_history", hist_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # 保存历史
            history = mod.save_detect_history(device_ip, results)
            self.log(f"已保存检测历史 (ID: {history.id[:20]}...)")

        except Exception as e:
            # 历史保存失败不影响主流程
            self.log(f"保存历史失败: {str(e)[:50]}")

    # ── Relay Server ─────────────────────────────────────────────────────────

    def _on_relay(self):
        """Relay 按钮：打开 Relay Server 连接对话框"""
        try:
            from gui.relay_dialog import show_relay_dialog

            # 创建新窗口
            relay_window = tk.Toplevel(self.root)
            show_relay_dialog(relay_window)
        except ImportError as e:
            messagebox.showerror(
                "缺少依赖", f"无法加载 Relay 模块:\n{e}", parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "错误", f"打开 Relay 对话框失败:\n{e}", parent=self.root
            )

    def _on_usb(self):
        """USB 按钮：打开 USB 直连对话框（ADB / V3.0-alpha）"""
        try:
            from gui.usb_dialog import USBDialog

            dlg = USBDialog(self.root)
            dlg.show()
        except ImportError as e:
            messagebox.showerror(
                "缺少依赖", f"无法加载 USB 模块:\n{e}", parent=self.root
            )
        except Exception as e:
            messagebox.showerror("错误", f"打开 USB 对话框失败:\n{e}", parent=self.root)

    # ── 卸载 ────────────────────────────────────────────────────────────────

    def _on_uninstall(self):
        """卸载按钮：打开卸载对话框"""
        if not self.ssh or not self.ssh.client:
            messagebox.showwarning("未连接", "请先连接 ARM 设备", parent=self.root)
            return

        # 导入并显示卸载对话框
        from gui.uninstall_dialog import show_uninstall_dialog

        def on_uninstall_done(success: bool):
            """卸载完成回调"""
            if success:
                self.log(f"\n{'=' * 50}")
                self.log("✓ 卸载成功")
                # 禁用相关按钮
                self.rollback_btn.config(state="disabled")
                self.uninstall_btn.config(state="disabled")
            else:
                self.log(f"\n{'=' * 50}")
                self.log("✗ 卸载失败")

        show_uninstall_dialog(self.root, self.ssh, on_complete=on_uninstall_done)
