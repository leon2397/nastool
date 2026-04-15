# -*- coding: utf-8 -*-
"""
gui/history_dialog.py — 检测历史查看对话框

功能：
1. 显示所有设备列表
2. 查看指定设备的历史记录
3. 查看单次检测详情
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, List, Dict

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


# ══════════════════════════════════════════════════════════════════
# 历史查看对话框
# ══════════════════════════════════════════════════════════════════


class HistoryDialog:
    """检测历史查看对话框"""

    def __init__(
        self,
        parent: tk.Tk,
        current_device: str = "",
        on_select: Optional[Callable] = None,
    ):
        """
        Args:
            parent: 父窗口
            current_device: 当前连接的设备 IP
            on_select: 选择历史记录回调
        """
        self.parent = parent
        self.current_device = current_device
        self.on_select = on_select
        self.selected_record = None

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("检测历史")
        self.dialog.geometry("900x600")
        self.dialog.configure(bg=BG)
        self.dialog.transient(parent)

        apply_theme(self.dialog)
        self._build_ui()

        # 加载数据
        self.dialog.after(100, self._load_devices)

    def _build_ui(self):
        """构建 UI"""
        main = tk.Frame(self.dialog, bg=BG)
        main.pack(fill="both", expand=True, padx=15, pady=15)

        # 标题
        hdr = tk.Frame(main, bg=BG)
        hdr.pack(fill="x", pady=(0, 10))
        tk.Label(
            hdr,
            text="检测历史记录",
            font=("Microsoft YaHei", 12, "bold"),
            fg=TEXT,
            bg=BG,
        ).pack(side="left")

        # 左侧：设备列表
        left_frame = tk.Frame(main, bg=BG)
        left_frame.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(
            left_frame,
            text="设备列表",
            fg=TEXT,
            bg=BG,
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(anchor="w", pady=(0, 5))

        # 设备列表
        dev_frame = tk.Frame(left_frame, bg=PANEL)
        dev_frame.pack(fill="both", expand=True)

        self.dev_tree = ttk.Treeview(
            dev_frame,
            columns=("ip", "last", "total"),
            show="headings",
            height=15,
            width=280,
        )
        self.dev_tree.heading("ip", text="IP 地址")
        self.dev_tree.heading("last", text="最近检测")
        self.dev_tree.heading("total", text="记录数")

        self.dev_tree.column("ip", width=120, anchor="w")
        self.dev_tree.column("last", width=100, anchor="center")
        self.dev_tree.column("total", width=50, anchor="center")

        style = ttk.Style()
        style.configure(
            "History.Treeview",
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            rowheight=24,
        )
        self.dev_tree.configure(style="History.Treeview")

        dev_sb = ttk.Scrollbar(
            dev_frame, orient="vertical", command=self.dev_tree.yview
        )
        self.dev_tree.configure(yscrollcommand=dev_sb.set)

        self.dev_tree.pack(side="left", fill="both", expand=True)
        dev_sb.pack(side="right", fill="y")

        self.dev_tree.bind("<<TreeviewSelect>>", self._on_device_select)

        # 右侧：历史记录列表 + 详情
        right_frame = tk.Frame(main, bg=BG)
        right_frame.pack(side="left", fill="both", expand=True)

        # 历史记录列表
        tk.Label(
            right_frame,
            text="历史记录",
            fg=TEXT,
            bg=BG,
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(anchor="w", pady=(0, 5))

        hist_frame = tk.Frame(right_frame, bg=PANEL)
        hist_frame.pack(fill="x", pady=(0, 10))

        self.hist_tree = ttk.Treeview(
            hist_frame,
            columns=("time", "passed", "warn", "crit", "fixable"),
            show="headings",
            height=8,
        )
        self.hist_tree.heading("time", text="检测时间")
        self.hist_tree.heading("passed", text="通过")
        self.hist_tree.heading("warn", text="警告")
        self.hist_tree.heading("crit", text="严重")
        self.hist_tree.heading("fixable", text="可修复")

        self.hist_tree.column("time", width=150, anchor="center")
        self.hist_tree.column("passed", width=50, anchor="center")
        self.hist_tree.column("warn", width=50, anchor="center")
        self.hist_tree.column("crit", width=50, anchor="center")
        self.hist_tree.column("fixable", width=60, anchor="center")

        self.hist_tree.configure(style="History.Treeview")

        hist_sb = ttk.Scrollbar(
            hist_frame, orient="vertical", command=self.hist_tree.yview
        )
        self.hist_tree.configure(yscrollcommand=hist_sb.set)

        self.hist_tree.pack(side="left", fill="both", expand=True)
        hist_sb.pack(side="right", fill="y")

        self.hist_tree.bind("<<TreeviewSelect>>", self._on_history_select)

        # 详情面板
        tk.Label(
            right_frame,
            text="检测详情",
            fg=TEXT,
            bg=BG,
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(anchor="w", pady=(10, 5))

        detail_frame = tk.Frame(right_frame, bg=PANEL)
        detail_frame.pack(fill="both", expand=True)

        self.detail_text = tk.Text(
            detail_frame,
            bg=PANEL,
            fg=TEXT,
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
        )
        detail_sb = ttk.Scrollbar(
            detail_frame, orient="vertical", command=self.detail_text.yview
        )
        self.detail_text.configure(yscrollcommand=detail_sb.set)

        self.detail_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        detail_sb.pack(side="right", fill="y")

        # 按钮区
        btn_frame = tk.Frame(right_frame, bg=BG)
        btn_frame.pack(fill="x", pady=(10, 0))

        tk.Button(
            btn_frame,
            text="关闭",
            command=self._on_close,
            fg=TEXT,
            bg=PANEL,
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=20,
        ).pack(side="right", padx=4)

        self.delete_btn = tk.Button(
            btn_frame,
            text="删除选中记录",
            command=self._on_delete,
            fg=TEXT,
            bg=PANEL,
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=15,
            state="disabled",
        )
        self.delete_btn.pack(side="right", padx=4)

        self.clear_btn = tk.Button(
            btn_frame,
            text="清空设备历史",
            command=self._on_clear_device,
            fg=TEXT,
            bg=PANEL,
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=15,
            state="disabled",
        )
        self.clear_btn.pack(side="right", padx=4)

        # 状态标签
        self.status_label = tk.Label(
            btn_frame, text="", fg=DIM, bg=BG, font=("Microsoft YaHei", 9)
        )
        self.status_label.pack(side="left")

        # 数据存储
        self.devices_data: List[Dict] = []
        self.current_device_ip = ""
        self.history_data: List = []

    def _load_devices(self):
        """加载设备列表"""
        self.status_label.config(text="加载中...")

        # 导入历史管理器
        import os, sys, importlib.util

        pkg_root = os.path.dirname(os.path.dirname(__file__))
        hist_path = os.path.join(pkg_root, "utils", "detect_history.py")
        spec = importlib.util.spec_from_file_location("detect_history", hist_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        try:
            devices = mod.get_all_devices()
            self.devices_data = devices

            self.dev_tree.delete(*self.dev_tree.get_children())

            if not devices:
                self.status_label.config(text="暂无历史记录")
                return

            for dev in devices:
                ip = dev["ip"]
                last = dev["last_detect"].split()[0] if dev["last_detect"] else "-"
                total = dev["total_records"]

                # 高亮当前设备
                tags = ("current",) if ip == self.current_device else ()
                self.dev_tree.insert("", "end", values=(ip, last, total), tags=tags)

            self.dev_tree.tag_configure("current", foreground=GREEN)

            # 如果有当前设备，自动选中
            if self.current_device:
                for item in self.dev_tree.get_children():
                    if self.dev_tree.item(item)["values"][0] == self.current_device:
                        self.dev_tree.selection_set(item)
                        break

            self.status_label.config(text=f"共 {len(devices)} 台设备")

        except Exception as e:
            self.status_label.config(text=f"加载失败: {str(e)[:30]}")

    def _on_device_select(self, event):
        """选择设备"""
        selection = self.dev_tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.dev_tree.item(item)["values"]
        self.current_device_ip = values[0]

        self.clear_btn.config(state="normal")
        self._load_device_history()

    def _load_device_history(self):
        """加载设备历史记录"""
        if not self.current_device_ip:
            return

        self.status_label.config(text="加载历史...")

        # 导入历史管理器
        import os, sys, importlib.util

        pkg_root = os.path.dirname(os.path.dirname(__file__))
        hist_path = os.path.join(pkg_root, "utils", "detect_history.py")
        spec = importlib.util.spec_from_file_location("detect_history", hist_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        try:
            history = mod.get_device_history(self.current_device_ip, limit=20)
            self.history_data = history

            self.hist_tree.delete(*self.hist_tree.get_children())

            if not history:
                self.status_label.config(text="该设备无历史记录")
                return

            for h in history:
                summary = h.summary
                self.hist_tree.insert(
                    "",
                    "end",
                    values=(
                        h.datetime_str,
                        summary["passed"],
                        summary["warning"],
                        summary["critical"],
                        summary["fixable"],
                    ),
                    iid=h.id,
                )

            self.status_label.config(text=f"共 {len(history)} 条记录")

        except Exception as e:
            self.status_label.config(text=f"加载失败: {str(e)[:30]}")

    def _on_history_select(self, event):
        """选择历史记录"""
        selection = self.hist_tree.selection()
        if not selection:
            self.delete_btn.config(state="disabled")
            return

        record_id = selection[0]

        # 查找对应记录
        for h in self.history_data:
            if h.id == record_id:
                self.selected_record = h
                self._show_detail(h)
                self.delete_btn.config(state="normal")
                break

    def _show_detail(self, history):
        """显示检测详情"""
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")

        # 标题
        self.detail_text.insert("end", f"检测时间: {history.datetime_str}\n")
        self.detail_text.insert("end", f"设备 IP: {history.device_ip}\n")
        self.detail_text.insert("end", f"检测项数: {len(history.results)}\n")
        self.detail_text.insert("end", "\n" + "=" * 50 + "\n\n")

        # 结果列表
        for i, r in enumerate(history.results, 1):
            sev = r.get("severity", "info")
            name = r.get("name", "?")
            msg = r.get("message", "")

            # 状态图标
            icon = {
                "passed": "[OK]",
                "warning": "[!!]",
                "warn": "[!!]",
                "critical": "[XX]",
                "info": "[--]",
            }.get(sev, "[--]")

            self.detail_text.insert("end", f"{i}. {icon} {name}\n")
            self.detail_text.insert("end", f"   {msg[:100]}\n\n")

        self.detail_text.configure(state="disabled")

    def _on_delete(self):
        """删除选中记录"""
        if not self.selected_record:
            return

        ok = messagebox.askyesno(
            "确认删除",
            f"确定要删除这条记录吗？\n\n时间: {self.selected_record.datetime_str}",
            parent=self.dialog,
        )

        if not ok:
            return

        # TODO: 实现删除逻辑
        messagebox.showinfo("已删除", "记录已删除", parent=self.dialog)
        self._load_device_history()

    def _on_clear_device(self):
        """清空设备历史"""
        if not self.current_device_ip:
            return

        ok = messagebox.askyesno(
            "确认清空",
            f"确定要清空设备 {self.current_device_ip} 的所有历史记录吗？\n\n此操作不可恢复！",
            parent=self.dialog,
        )

        if not ok:
            return

        # 导入历史管理器
        import os, sys, importlib.util

        pkg_root = os.path.dirname(os.path.dirname(__file__))
        hist_path = os.path.join(pkg_root, "utils", "detect_history.py")
        spec = importlib.util.spec_from_file_location("detect_history", hist_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        try:
            mod.get_history_manager().delete_device_history(self.current_device_ip)
            messagebox.showinfo("已清空", "历史记录已清空", parent=self.dialog)
            self._load_devices()
        except Exception as e:
            messagebox.showerror("错误", str(e), parent=self.dialog)

    def _on_close(self):
        """关闭对话框"""
        self.dialog.destroy()


# ══════════════════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════════════════


def show_history_dialog(
    parent: tk.Tk, current_device: str = "", on_select: Optional[Callable] = None
):
    """显示历史对话框"""
    return HistoryDialog(parent, current_device, on_select)
