# -*- coding: utf-8 -*-
"""
gui/local_backup_dialog.py — 本地备份管理对话框

功能：
1. 显示本地备份列表
2. 创建新备份
3. 恢复备份
4. 删除备份
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import List, Optional, Callable

# 导入备份管理器
import sys
import os
import importlib.util

pkg_root = os.path.dirname(os.path.dirname(__file__))
safety_path = os.path.join(pkg_root, "core", "safety.py")
spec = importlib.util.spec_from_file_location("safety", safety_path)
safety_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safety_mod)

BackupManager = safety_mod.BackupManager

# 主题
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


class LocalBackupDialog:
    """本地备份管理对话框"""

    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.backup_manager = BackupManager()

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("本地备份管理")
        self.dialog.geometry("600x450")
        self.dialog.configure(bg=BG)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        apply_theme(self.dialog)
        self._build_ui()
        self._refresh_backups()

    def _build_ui(self):
        """构建 UI"""
        main = tk.Frame(self.dialog, bg=BG)
        main.pack(fill="both", expand=True, padx=15, pady=15)

        # 标题栏
        hdr = tk.Frame(main, bg=BG)
        hdr.pack(fill="x", pady=(0, 10))
        tk.Label(
            hdr,
            text="本地备份管理",
            font=("Microsoft YaHei", 12, "bold"),
            fg=TEXT,
            bg=BG,
        ).pack(side="left")

        # 说明
        tk.Label(
            hdr,
            text="备份本地配置文件，必要时可恢复",
            font=("Microsoft YaHei", 9),
            fg=DIM,
            bg=BG,
        ).pack(side="left", padx=10)

        # 按钮栏
        btn_frame = tk.Frame(main, bg=BG)
        btn_frame.pack(fill="x", pady=(0, 10))

        tk.Button(
            btn_frame,
            text="刷新",
            command=self._refresh_backups,
            fg=TEXT,
            bg=PANEL,
            relief="flat",
            font=("Microsoft YaHei", 9),
            padx=12,
        ).pack(side="left", padx=2)

        tk.Button(
            btn_frame,
            text="创建备份",
            command=self._create_backup,
            fg=BG,
            bg=BLUE,
            relief="flat",
            font=("Microsoft YaHei", 9, "bold"),
            padx=12,
        ).pack(side="left", padx=2)

        tk.Button(
            btn_frame,
            text="恢复",
            command=self._restore_backup,
            fg=BG,
            bg=GREEN,
            relief="flat",
            font=("Microsoft YaHei", 9, "bold"),
            padx=12,
        ).pack(side="left", padx=2)

        tk.Button(
            btn_frame,
            text="删除",
            command=self._delete_backup,
            fg="white",
            bg=RED,
            relief="flat",
            font=("Microsoft YaHei", 9),
            padx=12,
        ).pack(side="left", padx=2)

        # 备份列表
        list_frame = tk.Frame(main, bg=BG)
        list_frame.pack(fill="both", expand=True)

        columns = ("filename", "time", "size")
        self.tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=12
        )

        self.tree.heading("filename", text="文件名")
        self.tree.heading("time", text="备份时间")
        self.tree.heading("size", text="大小")

        self.tree.column("filename", width=300)
        self.tree.column("time", width=150)
        self.tree.column("size", width=80, anchor="e")

        # 滚动条
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # 双击恢复
        self.tree.bind("<Double-Button-1>", lambda e: self._restore_backup())

        # 提示
        tip = tk.Label(
            main,
            text="💡 双击行可快速恢复备份",
            font=("Microsoft YaHei", 9),
            fg=DIM,
            bg=BG,
        )
        tip.pack(pady=(8, 0))

    def _refresh_backups(self):
        """刷新备份列表"""
        # 清空
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 扫描备份目录
        backup_dir = self.backup_manager.backup_dir

        if not backup_dir.exists():
            tk.Label(
                self.dialog, text=f"备份目录不存在: {backup_dir}", fg=YELLOW, bg=BG
            ).pack()
            return

        # 获取所有备份文件
        backups = sorted(
            backup_dir.glob("*.bak.*"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        for bp in backups:
            try:
                mtime = bp.stat().st_mtime
                import time

                time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                size = bp.stat().st_size

                # 格式化大小
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / 1024 / 1024:.1f} MB"

                self.tree.insert(
                    "", "end", values=(bp.name, time_str, size_str), tags=(str(bp),)
                )
            except Exception as e:
                print(f"Error reading backup {bp}: {e}")

        if not backups:
            self.tree.insert("", "end", values=("暂无备份", "", ""))

    def _create_backup(self):
        """创建备份：备份关键配置文件"""
        # 需要备份的文件
        files_to_backup = []

        # 检测历史
        hist_dir = Path(pkg_root).parent / "data" / "history"
        if hist_dir.exists():
            files_to_backup.extend(hist_dir.glob("*.json"))

        # 配置文件
        cfg_dir = Path(pkg_root).parent / "data" / "config"
        if cfg_dir.exists():
            files_to_backup.extend(cfg_dir.glob("*.json"))
            files_to_backup.extend(cfg_dir.glob("*.yaml"))

        if not files_to_backup:
            messagebox.showinfo("提示", "没有需要备份的文件", parent=self.dialog)
            return

        # 创建备份
        backup_count = 0
        for f in files_to_backup:
            result = self.backup_manager.backup(f)
            if result:
                backup_count += 1

        if backup_count > 0:
            messagebox.showinfo(
                "完成", f"已创建 {backup_count} 个备份", parent=self.dialog
            )
            self._refresh_backups()
        else:
            messagebox.showwarning("警告", "备份失败", parent=self.dialog)

    def _get_selected_backup(self) -> Optional[Path]:
        """获取选中的备份"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("请选择", "请先选择要恢复的备份", parent=self.dialog)
            return None

        item = selection[0]
        values = self.tree.item(item, "values")
        filename = values[0]

        if filename == "暂无备份":
            return None

        backup_path = self.backup_manager.backup_dir / filename
        return backup_path if backup_path.exists() else None

    def _restore_backup(self):
        """恢复备份"""
        backup_path = self._get_selected_backup()
        if not backup_path:
            return

        # 确认
        if not messagebox.askyesno(
            "确认恢复",
            f"确定要恢复备份吗？\n{backup_path.name}\n\n当前文件将被覆盖。",
            parent=self.dialog,
        ):
            return

        # 解析原始文件名
        # 格式: filename.ext.bak.1234567890
        parts = backup_path.name.rsplit(".bak.", 1)
        if len(parts) != 2:
            messagebox.showerror("错误", "备份文件名格式不正确", parent=self.dialog)
            return

        original_name = parts[0]

        # 尝试找到目标路径
        # 在原始位置查找
        search_dirs = [
            Path(pkg_root).parent / "data" / "history",
            Path(pkg_root).parent / "data" / "config",
            Path(pkg_root).parent / "data",
        ]

        target_path = None
        for d in search_dirs:
            if d.exists():
                candidates = list(d.glob(original_name))
                if candidates:
                    target_path = candidates[0]
                    break

        if not target_path:
            # 默认恢复到 data 目录
            target_path = Path(pkg_root).parent / "data" / original_name

        # 执行恢复
        success = self.backup_manager.restore(backup_path, target_path)

        if success:
            messagebox.showinfo(
                "完成", f"已恢复: {target_path.name}", parent=self.dialog
            )
        else:
            messagebox.showerror("错误", "恢复失败", parent=self.dialog)

    def _delete_backup(self):
        """删除备份"""
        backup_path = self._get_selected_backup()
        if not backup_path:
            return

        if not messagebox.askyesno(
            "确认删除",
            f"确定要删除这个备份吗？\n{backup_path.name}",
            parent=self.dialog,
        ):
            return

        try:
            backup_path.unlink()
            messagebox.showinfo("完成", "备份已删除", parent=self.dialog)
            self._refresh_backups()
        except Exception as e:
            messagebox.showerror("错误", f"删除失败: {e}", parent=self.dialog)


def show_local_backup_dialog(parent: tk.Tk):
    """显示本地备份对话框"""
    LocalBackupDialog(parent)
