# -*- coding: utf-8 -*-
"""
gui/rollback_dialog.py — 回滚对话框

功能：
1. 查询设备上的所有备份文件
2. 显示备份列表（时间、大小、类型）
3. 用户选择后执行回滚
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple, Optional, Callable

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


# 导入 confirm_danger（处理路径冲突）
def _import_confirm_danger():
    import os
    import sys
    import importlib.util

    pkg_root = os.path.dirname(os.path.dirname(__file__))
    notif_path = os.path.join(pkg_root, "utils", "notifications.py")

    spec = importlib.util.spec_from_file_location("notifications", notif_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.confirm_danger


confirm_danger = _import_confirm_danger()


# ══════════════════════════════════════════════════════════════════
# 备份文件信息
# ══════════════════════════════════════════════════════════════════


class BackupInfo:
    """备份文件信息"""

    def __init__(
        self, path: str, filename: str, size: int, mtime: str, backup_type: str
    ):
        self.path = path
        self.filename = filename
        self.size = size
        self.mtime = mtime  # "Apr 13 21:30"
        self.backup_type = backup_type  # "arm_server" / "config" / "dns"

    @property
    def size_str(self) -> str:
        """人类可读的文件大小"""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        else:
            return f"{self.size / 1024 / 1024:.1f} MB"

    @property
    def type_label(self) -> str:
        """备份类型标签"""
        labels = {
            "arm_server": "主程序",
            "config": "配置",
            "dns": "DNS",
            "service": "服务",
            "env": "环境",
        }
        return labels.get(self.backup_type, self.backup_type)


# ══════════════════════════════════════════════════════════════════
# 回滚对话框
# ══════════════════════════════════════════════════════════════════


class RollbackDialog:
    """回滚备份选择对话框"""

    def __init__(
        self, parent: tk.Tk, ssh_client, on_rollback: Optional[Callable] = None
    ):
        """
        Args:
            parent: 父窗口
            ssh_client: SSH 连接对象
            on_rollback: 回滚回调函数 (backup_info) -> None
        """
        self.parent = parent
        self.ssh = ssh_client
        self.on_rollback = on_rollback
        self.backups: List[BackupInfo] = []
        self.selected: Optional[BackupInfo] = None

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("回滚备份版本")
        self.dialog.geometry("700x500")
        self.dialog.configure(bg=BG)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        apply_theme(self.dialog)
        self._build_ui()

        # 加载备份列表
        self.dialog.after(100, self._load_backups)

    def _build_ui(self):
        """构建 UI"""
        main = tk.Frame(self.dialog, bg=BG)
        main.pack(fill="both", expand=True, padx=15, pady=15)

        # 标题
        hdr = tk.Frame(main, bg=BG)
        hdr.pack(fill="x", pady=(0, 10))
        tk.Label(
            hdr,
            text="选择要恢复的备份版本",
            font=("Microsoft YaHei", 12, "bold"),
            fg=TEXT,
            bg=BG,
        ).pack(side="left")

        # 备份类型筛选
        filter_frame = tk.Frame(main, bg=BG)
        filter_frame.pack(fill="x", pady=(0, 8))

        tk.Label(
            filter_frame, text="备份类型:", fg=DIM, bg=BG, font=("Microsoft YaHei", 9)
        ).pack(side="left")

        self.filter_var = tk.StringVar(value="all")
        filters = [
            ("全部", "all"),
            ("主程序", "arm_server"),
            ("配置", "config"),
            ("DNS", "dns"),
        ]
        for text, value in filters:
            rb = tk.Radiobutton(
                filter_frame,
                text=text,
                value=value,
                variable=self.filter_var,
                command=self._apply_filter,
                fg=TEXT,
                bg=BG,
                selectcolor=PANEL,
                activebackground=BG,
                activeforeground=TEXT,
                font=("Microsoft YaHei", 9),
            )
            rb.pack(side="left", padx=8)

        # 刷新按钮
        tk.Button(
            filter_frame,
            text="刷新",
            command=self._load_backups,
            fg=TEXT,
            bg=PANEL,
            relief="flat",
            font=("Microsoft YaHei", 9),
            padx=10,
        ).pack(side="right")

        # 备份列表表格
        list_frame = tk.Frame(main, bg=BG)
        list_frame.pack(fill="both", expand=True, pady=8)

        columns = ("type", "time", "size", "filename")
        self.tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=12
        )

        self.tree.heading("type", text="类型")
        self.tree.heading("time", text="备份时间")
        self.tree.heading("size", text="大小")
        self.tree.heading("filename", text="文件名")

        self.tree.column("type", width=80, anchor="center")
        self.tree.column("time", width=120, anchor="center")
        self.tree.column("size", width=80, anchor="center")
        self.tree.column("filename", width=300, anchor="w")

        # 设置样式
        style = ttk.Style()
        style.configure(
            "Rollback.Treeview",
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            rowheight=28,
        )
        style.configure("Rollback.Treeview.Heading", background=PANEL2, foreground=TEXT)
        self.tree.configure(style="Rollback.Treeview")

        # 滚动条
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 绑定选择事件
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

        # 详情面板
        detail_frame = tk.Frame(main, bg=PANEL, relief="flat")
        detail_frame.pack(fill="x", pady=8)

        tk.Label(
            detail_frame,
            text="备份详情",
            fg=TEXT,
            bg=PANEL,
            font=("Microsoft YaHei", 9, "bold"),
        ).pack(anchor="w", padx=8, pady=4)

        self.detail_text = tk.Text(
            detail_frame,
            height=4,
            bg=PANEL,
            fg=DIM,
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
        )
        self.detail_text.pack(fill="x", padx=8, pady=4)
        self.detail_text.insert("1.0", "选择备份文件查看详情")
        self.detail_text.configure(state="disabled")

        # 按钮区
        btn_frame = tk.Frame(main, bg=BG)
        btn_frame.pack(fill="x", pady=(10, 0))

        tk.Button(
            btn_frame,
            text="取消",
            command=self._on_cancel,
            fg=TEXT,
            bg=PANEL,
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=20,
        ).pack(side="right", padx=4)

        self.rollback_btn = tk.Button(
            btn_frame,
            text="恢复选中版本",
            command=self._on_rollback,
            fg=TEXT,
            bg=GREEN,
            relief="flat",
            font=("Microsoft YaHei", 10, "bold"),
            padx=20,
            state="disabled",
        )
        self.rollback_btn.pack(side="right", padx=4)

        # 状态标签
        self.status_label = tk.Label(
            btn_frame, text="加载中...", fg=DIM, bg=BG, font=("Microsoft YaHei", 9)
        )
        self.status_label.pack(side="left")

    def _load_backups(self):
        """从设备加载备份列表"""
        self.status_label.config(text="正在查询备份...")
        self.tree.delete(*self.tree.get_children())
        self.backups.clear()

        if not self.ssh or not self.ssh.client:
            self.status_label.config(text="未连接设备")
            return

        # 查询备份目录
        query_cmd = """
BACKUP_DIR="/opt/ai-nas/backups"
if [ -d "$BACKUP_DIR" ]; then
    find "$BACKUP_DIR" -name "*.bak.*" -type f -exec stat -c "%n %s %y" {} \\; 2>/dev/null
else
    echo "NO_BACKUP_DIR"
fi
"""
        try:
            ec, out, _ = self.ssh.exec(query_cmd, timeout=15)

            if ec != 0 or not out.strip():
                self.status_label.config(text="无备份文件")
                return

            if "NO_BACKUP_DIR" in out:
                self.status_label.config(text="备份目录不存在")
                return

            # 解析输出
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    path = parts[0]
                    size = int(parts[1]) if parts[1].isdigit() else 0
                    # 时间格式: 2026-04-13 21:30:45.000000000
                    mtime_raw = (
                        parts[2] + " " + parts[3][:5] if len(parts) > 3 else parts[2]
                    )

                    # 提取文件名
                    filename = path.split("/")[-1]

                    # 判断备份类型
                    backup_type = "unknown"
                    if "arm_server" in filename:
                        backup_type = "arm_server"
                    elif "config" in filename:
                        backup_type = "config"
                    elif "resolv" in filename:
                        backup_type = "dns"
                    elif "service" in filename:
                        backup_type = "service"
                    elif "env" in filename:
                        backup_type = "env"

                    info = BackupInfo(path, filename, size, mtime_raw, backup_type)
                    self.backups.append(info)

            # 按时间倒序排列
            self.backups.sort(key=lambda x: x.mtime, reverse=True)

            self._apply_filter()
            self.status_label.config(text=f"共 {len(self.backups)} 个备份")

        except Exception as e:
            self.status_label.config(text=f"查询失败: {str(e)[:30]}")

    def _apply_filter(self):
        """应用筛选条件"""
        self.tree.delete(*self.tree.get_children())
        filter_type = self.filter_var.get()

        for info in self.backups:
            if filter_type != "all" and info.backup_type != filter_type:
                continue

            self.tree.insert(
                "",
                "end",
                values=(
                    info.type_label,
                    info.mtime,
                    info.size_str,
                    info.filename,
                ),
                tags=(info.backup_type,),
            )

    def _on_select(self, event):
        """选择备份文件"""
        selection = self.tree.selection()
        if not selection:
            self.selected = None
            self.rollback_btn.config(state="disabled")
            return

        item = selection[0]
        idx = self.tree.index(item)

        # 根据筛选找到对应的备份
        filter_type = self.filter_var.get()
        filtered = [
            b
            for b in self.backups
            if filter_type == "all" or b.backup_type == filter_type
        ]

        if idx < len(filtered):
            self.selected = filtered[idx]
            self._update_detail()
            self.rollback_btn.config(state="normal")

    def _update_detail(self):
        """更新详情面板"""
        if not self.selected:
            return

        detail = f"路径: {self.selected.path}\n"
        detail += f"大小: {self.selected.size_str}\n"
        detail += f"时间: {self.selected.mtime}\n"
        detail += f"类型: {self.selected.type_label}"

        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", detail)
        self.detail_text.configure(state="disabled")

    def _on_double_click(self, event):
        """双击执行回滚"""
        if self.selected:
            self._on_rollback()

    def _on_rollback(self):
        """执行回滚"""
        if not self.selected:
            return

        # 确认对话框
        ok = confirm_danger(
            parent=self.dialog,
            title=f"恢复 {self.selected.type_label} 备份",
            risk="high",
            message=f"将恢复备份文件:\n{self.selected.filename}",
            details=(
                f"备份时间: {self.selected.mtime}\n"
                f"文件大小: {self.selected.size_str}\n"
                f"恢复路径: {self._get_restore_path()}"
            ),
            warnings=[
                "恢复后当前版本将被覆盖",
                "服务将自动重启",
                "建议先备份当前版本",
            ],
        )

        if not ok:
            return

        # 执行回滚
        self._execute_rollback()

    def _get_restore_path(self) -> str:
        """获取恢复目标路径"""
        if self.selected.backup_type == "arm_server":
            return "/opt/ai-nas/arm_server.py"
        elif self.selected.backup_type == "config":
            return "/opt/ai-nas/config.yaml"
        elif self.selected.backup_type == "dns":
            return "/etc/resolv.conf"
        elif self.selected.backup_type == "service":
            return "/etc/systemd/system/ai-nas-arm.service"
        elif self.selected.backup_type == "env":
            return "/opt/ai-nas/ai-nas-arm.env"
        else:
            return "/opt/ai-nas/"

    def _execute_rollback(self):
        """执行回滚命令"""
        if not self.ssh or not self.ssh.client:
            messagebox.showerror("错误", "SSH 未连接", parent=self.dialog)
            return

        restore_path = self._get_restore_path()

        # 构建回滚命令
        if self.selected.backup_type == "arm_server":
            # 主程序需要重启服务
            cmd = f'''
cp "{self.selected.path}" "{restore_path}" && \
systemctl restart ai-nas-arm && \
echo "OK: 已恢复并重启服务"
'''
        elif self.selected.backup_type == "dns":
            # DNS 需要特殊处理
            cmd = f'''
cp "{self.selected.path}" /etc/resolv.conf && \
echo "OK: DNS 已恢复"
'''
        else:
            # 其他文件直接复制
            cmd = f'cp "{self.selected.path}" "{restore_path}" && echo "OK: 已恢复"'

        try:
            self.status_label.config(text="正在恢复...")
            self.rollback_btn.config(state="disabled")

            ec, out, _ = self.ssh.exec(cmd, timeout=30)

            if ec == 0 and "OK" in out:
                self.status_label.config(text="恢复成功")
                messagebox.showinfo(
                    "恢复完成",
                    f"已恢复备份: {self.selected.filename}\n\n{out}",
                    parent=self.dialog,
                )

                # 回调
                if self.on_rollback:
                    self.on_rollback(self.selected)

                # 关闭对话框
                self.dialog.destroy()
            else:
                self.status_label.config(text="恢复失败")
                messagebox.showerror(
                    "恢复失败", f"命令执行失败:\n{out[:500]}", parent=self.dialog
                )
                self.rollback_btn.config(state="normal")

        except Exception as e:
            self.status_label.config(text="恢复出错")
            messagebox.showerror("错误", str(e), parent=self.dialog)
            self.rollback_btn.config(state="normal")

    def _on_cancel(self):
        """取消"""
        self.dialog.destroy()


# ══════════════════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════════════════


def show_rollback_dialog(
    parent: tk.Tk, ssh_client, on_rollback: Optional[Callable] = None
):
    """显示回滚对话框"""
    return RollbackDialog(parent, ssh_client, on_rollback)
