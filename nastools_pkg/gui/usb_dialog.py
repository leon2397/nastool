# -*- coding: utf-8 -*-
"""
gui/usb_dialog.py — USB 直连对话框（ADB）
nastools V3.0-alpha

通过 USB / ADB 直连 ARM Linux 设备，无需 IP/密码。
零配置，即插即用。

功能：
  - ADB 环境检测 + 安装引导
  - USB 设备列表
  - 设备快速信息
  - ADB 直连诊断
  - 一键安装 Agent
  - USB 拔插事件监听
"""

import sys
import os
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Dict

# ── 内部模块 ─────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
    apply_theme,
)
from core.adb import (
    USBConnectionManager,
    USBConnectedDevice,
)


# ══════════════════════════════════════════════════════════════════
# USB 连接对话框
# ══════════════════════════════════════════════════════════════════


class USBDialog:
    """
    USB 直连对话框

    Usage:
        root = tk.Tk()
        dlg = USBDialog(root)
        dlg.show()   # 模态对话框
    """

    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.adb = USBConnectionManager()
        self.devices: list[USBConnectedDevice] = []
        self.watch_queue: queue.Queue = queue.Queue()
        self._watch_running = False

        # 创建设置对话框
        self.win = tk.Toplevel(parent)
        self.win.title("USB 直连 — nastools V3.0-alpha")
        self.win.geometry("680x560")
        self.win.minsize(600, 480)
        self.win.configure(bg=BG)
        self.win.transient(parent)  # 绑定父窗口
        self.win.grab_set()  # 模态

        apply_theme(self.win)

        # 窗口关闭时清理监听
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._refresh_devices()

    # ── UI 构建 ──────────────────────────────────────────────────

    def _build_ui(self):
        main = tk.Frame(self.win, bg=BG)
        main.pack(fill="both", expand=True, padx=12, pady=10)

        # ── 标题栏 ─────────────────────────────────────────────
        hdr = tk.Frame(main, bg=BG)
        hdr.pack(fill="x", pady=(0, 6))

        tk.Label(
            hdr, text="USB 直连", font=("Microsoft YaHei", 16, "bold"), fg=ACCENT, bg=BG
        ).pack(side="left")
        tk.Label(
            hdr, text="ADB / 即插即用", font=("Microsoft YaHei", 9), fg=DIM, bg=BG
        ).pack(side="left", padx=8)
        tk.Label(hdr, text="V3.0-alpha", font=("Consolas", 9), fg=BORDER, bg=BG).pack(
            side="left"
        )

        self._sep(main).pack(fill="x", pady=4)

        # ── ADB 状态卡 ──────────────────────────────────────────
        self._build_adb_status(main)
        self._sep(main).pack(fill="x", pady=4)

        # ── 设备列表 ─────────────────────────────────────────────
        self._build_device_list(main)
        self._sep(main).pack(fill="x", pady=4)

        # ── 设备信息卡 ───────────────────────────────────────────
        self._build_info_card(main)
        self._sep(main).pack(fill="x", pady=4)

        # ── 操作按钮 ─────────────────────────────────────────────
        self._build_action_bar(main)

        # ── 日志区 ──────────────────────────────────────────────
        self._build_log(main)

    def _build_adb_status(self, parent):
        """ADB 环境状态卡"""
        card = tk.LabelFrame(
            parent,
            text="ADB 环境",
            font=("Microsoft YaHei", 10, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=12,
            pady=8,
            relief="flat",
            bd=0,
        )
        card.pack(fill="x", pady=(0, 6))

        inner = tk.Frame(card, bg=PANEL)
        inner.pack(fill="x")

        self.adb_status_icon = tk.Label(
            inner, text="⏳", font=("Segoe UI Emoji", 14), fg=DIM, bg=PANEL
        )
        self.adb_status_icon.pack(side="left", padx=(0, 6))

        self.adb_status_label = tk.Label(
            inner, text="检测中...", font=("Microsoft YaHei", 10), fg=DIM, bg=PANEL
        )
        self.adb_status_label.pack(side="left")

        self.adb_install_btn = tk.Button(
            inner,
            text="安装 ADB",
            font=("Microsoft YaHei", 9),
            fg="white",
            bg=RED,
            relief="flat",
            cursor="hand2",
            command=self._show_install_hint,
        )
        self.adb_install_btn.pack(side="right")

        # ADB 版本（第二行）
        self.adb_version_label = tk.Label(
            inner, text="", font=("Consolas", 9), fg=DIM, bg=PANEL
        )
        self.adb_version_label.pack(anchor="w", pady=(4, 0))

    def _build_device_list(self, parent):
        """USB 设备列表"""
        hdr = tk.Frame(parent, bg=BG)
        hdr.pack(fill="x", pady=(0, 4))
        tk.Label(
            hdr, text="USB 设备", font=("Microsoft YaHei", 10, "bold"), fg=TEXT, bg=BG
        ).pack(side="left")
        self.refresh_btn = tk.Button(
            hdr,
            text="🔄 刷新",
            font=("Microsoft YaHei", 9),
            fg=TEXT,
            bg=PANEL2,
            relief="flat",
            cursor="hand2",
            command=self._refresh_devices,
        )
        self.refresh_btn.pack(side="right")

        # 设备树
        tree_frame = tk.Frame(parent, bg=PANEL)
        tree_frame.pack(fill="x", pady=(0, 4))

        cols = ("state", "model", "serial")
        self.dev_tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings", height=3, style="Dark.Treeview"
        )
        self.dev_tree.heading("state", text="状态")
        self.dev_tree.heading("model", text="型号")
        self.dev_tree.heading("serial", text="序列号")
        self.dev_tree.column("state", width=90, anchor="center")
        self.dev_tree.column("model", width=180, anchor="w")
        self.dev_tree.column("serial", width=280, anchor="w")
        self.dev_tree.tag_configure("ready", foreground=GREEN)
        self.dev_tree.tag_configure("unauthorized", foreground=YELLOW)
        self.dev_tree.tag_configure("offline", foreground=RED)
        self.dev_tree.pack(fill="x")
        self.dev_tree.bind("<<TreeviewSelect>>", self._on_device_selected)

        # 无设备提示
        self.no_device_label = tk.Label(
            tree_frame,
            text="未检测到 USB 连接的设备",
            font=("Microsoft YaHei", 9),
            fg=DIM,
            bg=PANEL,
            pady=6,
        )
        self.no_device_label.pack(fill="x")

        # USB 监听开关
        watch_frame = tk.Frame(parent, bg=BG)
        watch_frame.pack(fill="x")
        self.watch_var = tk.BooleanVar(value=False)
        self.watch_toggle = tk.Checkbutton(
            watch_frame,
            text="🔌 监听 USB 拔插事件（自动刷新）",
            variable=self.watch_var,
            font=("Microsoft YaHei", 9),
            fg=DIM,
            bg=BG,
            selectcolor=PANEL,
            activebackground=BG,
            command=self._toggle_watch,
        )
        self.watch_toggle.pack(side="left")

    def _build_info_card(self, parent):
        """选中设备的详细信息"""
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
        self.info_card.pack(fill="x", pady=(0, 6))

        self.info_labels: Dict[str, tk.Label] = {}
        labels = [
            ("hostname", "主机名"),
            ("kernel", "内核"),
            ("os", "系统"),
            ("disk", "磁盘"),
            ("uptime", "运行时间"),
        ]
        for i, (key, title) in enumerate(labels):
            row = tk.Frame(self.info_card, bg=PANEL)
            row.pack(fill="x", pady=1)
            tk.Label(
                row,
                text=title + ":",
                font=("Microsoft YaHei", 9),
                fg=DIM,
                bg=PANEL,
                width=8,
                anchor="e",
            ).pack(side="left")
            lbl = tk.Label(
                row, text="(未选择设备)", font=("Consolas", 9), fg=DIM, bg=PANEL
            )
            lbl.pack(side="left", padx=4)
            self.info_labels[key] = lbl

    def _build_action_bar(self, parent):
        """操作按钮栏"""
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x")

        btns = [
            ("🔍 诊断连接", BLUE, self._run_diagnose),
            ("📋 设备信息", GREEN, self._fetch_info),
            ("📦 安装 Agent", ACCENT, self._install_agent),
            ("❌ 关闭", DIM, self._on_close),
        ]
        for text, color, cmd in btns:
            b = tk.Button(
                bar,
                text=text,
                font=("Microsoft YaHei", 9),
                fg="white",
                bg=color,
                relief="flat",
                cursor="hand2",
                command=cmd,
                padx=10,
                pady=4,
            )
            b.pack(side="left", padx=3)

        self.action_status = tk.Label(
            bar, text="", font=("Microsoft YaHei", 9), fg=DIM, bg=BG
        )
        self.action_status.pack(side="right")

    def _build_log(self, parent):
        """日志输出区"""
        tk.Label(parent, text="日志", font=("Microsoft YaHei", 9), fg=DIM, bg=BG).pack(
            anchor="w"
        )
        self.log_area = scrolledtext.ScrolledText(
            parent,
            font=("Consolas", 8.5),
            fg=DIM,
            bg=PANEL,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            height=5,
            state="disabled",
        )
        self.log_area.pack(fill="both", expand=True, pady=(2, 0))

    def _sep(self, parent):
        s = tk.Frame(parent, height=1, bg=BORDER)
        return s

    # ── 事件处理 ──────────────────────────────────────────────────

    def _on_device_selected(self, event=None):
        """选中设备后自动获取信息"""
        sel = self.dev_tree.selection()
        if sel:
            # 自动获取设备信息（延迟加载）
            self._fetch_info()

    def _toggle_watch(self):
        """切换 USB 监听"""
        if self.watch_var.get():
            self._start_watch()
        else:
            self._stop_watch()

    def _start_watch(self):
        """启动 USB 监听线程"""
        if self._watch_running:
            return
        self._watch_running = True

        def on_plugged(dev: USBConnectedDevice):
            self.watch_queue.put(("plugged", dev))

        def on_unplugged(serial: str):
            self.watch_queue.put(("unplugged", serial))

        self._watch_thread = threading.Thread(
            target=self.adb.start_watching,
            args=(on_plugged, on_unplugged, 2.0),
            daemon=True,
        )
        self._watch_thread.start()
        self._poll_watch_queue()
        self.log("已开启 USB 拔插监听...")

    def _stop_watch(self):
        self._watch_running = False
        self.adb.stop_watching()
        self.log("USB 监听已关闭")

    def _poll_watch_queue(self):
        """处理监听队列中的事件"""
        try:
            while True:
                ev = self.watch_queue.get_nowait()
                kind, data = ev
                if kind == "plugged":
                    dev: USBConnectedDevice = data
                    self.log(f"🔌 设备插入: {dev.label}")
                else:
                    self.log(f"🔌 设备拔出: {data}")
                # 自动刷新设备列表
                self.win.after(100, self._refresh_devices)
        except queue.Empty:
            pass

        if self._watch_running:
            self.win.after(300, self._poll_watch_queue)

    def _show_install_hint(self):
        """显示 ADB 安装提示"""
        hint = self.adb.install_hint()
        win = tk.Toplevel(self.win)
        win.title("安装 ADB")
        win.geometry("520x360")
        win.configure(bg=BG)
        win.transient(self.win)
        win.grab_set()

        tk.Label(
            win,
            text="安装 Android Platform Tools（ADB）",
            font=("Microsoft YaHei", 12, "bold"),
            fg=ACCENT,
            bg=BG,
            pady=12,
        ).pack()
        txt = scrolledtext.ScrolledText(
            win,
            font=("Consolas", 10),
            fg=TEXT,
            bg=PANEL,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            padx=10,
            pady=10,
        )
        txt.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        txt.insert("1.0", hint)
        txt.configure(state="disabled")

        tk.Button(
            win,
            text="知道了",
            font=("Microsoft YaHei", 9),
            fg="white",
            bg=ACCENT,
            relief="flat",
            cursor="hand2",
            command=win.destroy,
            padx=20,
        ).pack(pady=(0, 12))

    def _refresh_devices(self):
        """刷新设备列表"""
        self.devices = self.adb.list_devices()

        # 清空树
        for item in self.dev_tree.get_children():
            self.dev_tree.delete(item)

        if not self.devices:
            self.no_device_label.configure(text="未检测到 USB 连接的设备", fg=YELLOW)
            # 清空信息卡
            for lbl in self.info_labels.values():
                lbl.configure(text="(未选择设备)", fg=DIM)
        else:
            self.no_device_label.configure(
                text=f"检测到 {len(self.devices)} 个设备", fg=GREEN
            )
            for dev in self.devices:
                tag = "ready" if dev.is_ready else dev.state
                item = self.dev_tree.insert(
                    "",
                    "end",
                    values=(
                        self._state_text(dev.state),
                        dev.model or "(未知型号)",
                        dev.serial,
                    ),
                    tags=(tag,),
                )
                # 自动选中第一个
                if dev.is_ready and not self.dev_tree.selection():
                    self.dev_tree.selection_set(item)
                    self.dev_tree.focus(item)

        # 更新 ADB 状态显示
        if self.adb.is_adb_installed():
            self.adb_status_icon.configure(text="✅", fg=GREEN)
            self.adb_status_label.configure(text="ADB 已就绪", fg=GREEN)
            self.adb_version_label.configure(
                text=self.adb.adb_version().splitlines()[0]
                if self.adb.adb_version() != "未知"
                else ""
            )
            self.adb_install_btn.configure(text="查看版本", bg=BLUE)
        else:
            self.adb_status_icon.configure(text="❌", fg=RED)
            self.adb_status_label.configure(text="ADB 未安装", fg=RED)
            self.adb_version_label.configure(text="")
            self.adb_install_btn.configure(text="安装 ADB", bg=RED)

        self.log(f"设备列表已刷新: {len(self.devices)} 个设备")

    @staticmethod
    def _state_text(state: str) -> str:
        """设备状态友好文字"""
        return {
            "device": "✅ 已授权",
            "unauthorized": "⚠️ 未授权",
            "offline": "❌ 离线",
            "bootloader": "🔧 Bootloader",
            "recovery": "🔄 Recovery",
            "no device": "❌ 无设备",
        }.get(state, state)

    # ── 业务操作 ──────────────────────────────────────────────────

    def _get_selected_serial(self) -> str:
        sel = self.dev_tree.selection()
        if not sel:
            messagebox.showwarning("未选择设备", "请先选择一个 USB 设备")
            return ""
        vals = self.dev_tree.item(sel[0], "values")
        return vals[2] if len(vals) >= 3 else ""

    def _run_diagnose(self):
        """诊断 USB 连接"""
        serial = self._get_selected_serial()
        diag = self.adb.diagnose()

        lines = ["━━━ USB 诊断报告 ━━━", ""]
        if diag["issues"]:
            lines.append("❌ 问题:")
            for iss in diag["issues"]:
                lines.append(f"  • {iss}")
            lines.append("")
        if diag["suggestions"]:
            lines.append("💡 建议:")
            for sug in diag["suggestions"]:
                for line in sug.splitlines():
                    lines.append(f"  {line}")
                lines.append("")
        if not diag["issues"]:
            lines.append("✅ 未发现问题")

        msg = "\n".join(lines)
        self.log(msg)
        messagebox.showinfo("USB 诊断", msg)

    def _fetch_info(self):
        """获取选中设备的系统信息"""
        serial = self._get_selected_serial()
        if not serial:
            return

        def worker():
            self.action_status.configure(text="正在获取设备信息...")
            info = self.adb.quick_info(serial)
            for key, lbl in self.info_labels.items():
                val = info.get(key, "(无数据)")
                val = val.splitlines()[0][:60]  # 截断长行
                lbl.configure(text=val, fg=TEXT)
            self.action_status.configure(text="")
            self.log(f"设备信息已更新: {info.get('hostname', serial)[:30]}")

        threading.Thread(target=worker, daemon=True).start()

    def _install_agent(self):
        """通过 ADB 一键安装 Agent"""
        serial = self._get_selected_serial()
        if not serial:
            return

        # 选择 agent 包
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="选择 Agent 安装包",
            filetypes=[("ZIP 压缩包", "*.zip"), ("所有文件", "*.*")],
            initialdir=os.path.join(os.path.dirname(__file__), "..", ".."),
        )
        if not path:
            return

        ok = messagebox.askyesno(
            "确认安装",
            f"即将通过 USB 安装 Agent 到设备:\n\n  序列号: {serial}\n  包路径: {path}\n\n继续？",
        )
        if not ok:
            return

        def worker():
            self.action_status.configure(text="安装中...")
            self.log(f"开始安装 Agent: {path}")

            # 复用 adb.push 逻辑
            ok_push, msg_push = self.adb.push_file(
                serial, path, "/tmp/nastools_agent.zip"
            )
            self.log(msg_push)
            if not ok_push:
                self.action_status.configure(text="安装失败")
                self.win.after(0, lambda: messagebox.showerror("安装失败", msg_push))
                return

            # 解压
            ok2, msg2 = self.adb.run_on_device(
                serial,
                "mkdir -p /opt/nastools && cd /opt/nastools && "
                "unzip -o /tmp/nastools_agent.zip && "
                "rm /tmp/nastools_agent.zip && "
                "chmod +x *.sh *.py 2>/dev/null; echo INSTALLED",
            )
            self.log(msg2)

            if "INSTALLED" in msg2 or ok2:
                self.action_status.configure(text="✅ 已安装")
                self.log("✅ Agent 安装成功")
                self.win.after(
                    0,
                    lambda: messagebox.showinfo(
                        "安装成功",
                        f"Agent 已安装到 /opt/nastools\n设备: {serial[:16]}...",
                    ),
                )
            else:
                self.action_status.configure(text="安装失败")
                self.win.after(0, lambda m=msg2: messagebox.showerror("安装失败", m))

        threading.Thread(target=worker, daemon=True).start()

    # ── 日志 ─────────────────────────────────────────────────────

    def log(self, msg: str):
        """追加日志行"""
        self.log_area.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{ts}] {msg}\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    # ── 生命周期 ─────────────────────────────────────────────────

    def show(self):
        """显示对话框（阻塞直到关闭）"""
        self.win.wait_window()

    def _on_close(self):
        self._stop_watch()
        self.win.destroy()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._on_close()


# ── 入口（独立调试）────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    dlg = USBDialog(root)
    dlg.show()
