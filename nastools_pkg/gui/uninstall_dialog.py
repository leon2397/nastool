# -*- coding: utf-8 -*-
"""
gui/uninstall_dialog.py — 卸载确认对话框

功能：
1. 卸载前预览（显示将被删除的内容）
2. 安全/完全卸载模式选择
3. 卸载进度显示
4. 卸载后验证
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
from typing import Optional, Callable

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
# 卸载对话框
# ══════════════════════════════════════════════════════════════════


class UninstallDialog:
    """卸载确认对话框"""

    def __init__(self, parent: tk.Tk, ssh, on_complete: Optional[Callable] = None):
        """
        Args:
            parent: 父窗口
            ssh: SSH 连接对象
            on_complete: 卸载完成回调
        """
        self.parent = parent
        self.ssh = ssh
        self.on_complete = on_complete

        self.log_queue = queue.Queue()
        self.preview = None
        self.mode = tk.StringVar(value="safe")

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("卸载 AI-NAS")
        self.dialog.geometry("600x500")
        self.dialog.configure(bg=BG)
        self.dialog.transient(parent)

        apply_theme(self.dialog)
        self._build_ui()

        # 加载预览
        self.dialog.after(100, self._load_preview)

    def _build_ui(self):
        """构建 UI"""
        main = tk.Frame(self.dialog, bg=BG)
        main.pack(fill="both", expand=True, padx=15, pady=15)

        # 标题
        tk.Label(
            main,
            text="卸载 AI-NAS 系统",
            font=("Microsoft YaHei", 14, "bold"),
            fg=TEXT,
            bg=BG,
        ).pack(anchor="w", pady=(0, 10))

        # 预览区域
        preview_frame = tk.LabelFrame(
            main,
            text="卸载预览",
            font=("Microsoft YaHei", 10, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=10,
            pady=8,
        )
        preview_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.preview_text = tk.Text(
            preview_frame,
            bg=PANEL,
            fg=TEXT,
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
            height=12,
        )
        preview_sb = ttk.Scrollbar(
            preview_frame, orient="vertical", command=self.preview_text.yview
        )
        self.preview_text.configure(yscrollcommand=preview_sb.set)

        self.preview_text.pack(side="left", fill="both", expand=True)
        preview_sb.pack(side="right", fill="y")

        # 模式选择
        mode_frame = tk.Frame(main, bg=BG)
        mode_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            mode_frame, text="卸载模式:", fg=TEXT, bg=BG, font=("Microsoft YaHei", 10)
        ).pack(side="left")

        safe_rb = tk.Radiobutton(
            mode_frame,
            text="安全卸载（保留数据）",
            variable=self.mode,
            value="safe",
            fg=TEXT,
            bg=BG,
            selectcolor=PANEL,
            activebackground=BG,
            font=("Microsoft YaHei", 9),
        )
        safe_rb.pack(side="left", padx=(10, 5))

        full_rb = tk.Radiobutton(
            mode_frame,
            text="完全卸载（删除所有）",
            variable=self.mode,
            value="full",
            fg=RED,
            bg=BG,
            selectcolor=PANEL,
            activebackground=BG,
            font=("Microsoft YaHei", 9),
        )
        full_rb.pack(side="left", padx=5)

        # 警告标签
        self.warn_label = tk.Label(
            mode_frame, text="", fg=DIM, bg=BG, font=("Microsoft YaHei", 9)
        )
        self.warn_label.pack(side="right")

        self.mode.trace("w", self._on_mode_change)

        # 按钮区
        btn_frame = tk.Frame(main, bg=BG)
        btn_frame.pack(fill="x")

        self.cancel_btn = tk.Button(
            btn_frame,
            text="取消",
            command=self._on_cancel,
            fg=TEXT,
            bg=PANEL,
            relief="flat",
            font=("Microsoft YaHei", 10),
            padx=20,
        )
        self.cancel_btn.pack(side="right", padx=4)

        self.uninstall_btn = tk.Button(
            btn_frame,
            text="开始卸载",
            command=self._on_uninstall,
            fg=BG,
            bg=RED,
            relief="flat",
            font=("Microsoft YaHei", 10, "bold"),
            padx=20,
            state="disabled",
        )
        self.uninstall_btn.pack(side="right", padx=4)

        # 状态标签
        self.status_label = tk.Label(
            btn_frame, text="加载预览中...", fg=DIM, bg=BG, font=("Microsoft YaHei", 9)
        )
        self.status_label.pack(side="left")

    def _on_mode_change(self, *args):
        """模式切换"""
        if self.mode.get() == "full":
            self.warn_label.config(text="⚠ 将删除所有数据，不可恢复！", fg=RED)
        else:
            self.warn_label.config(text="保留配置和数据", fg=GREEN)

    def _load_preview(self):
        """加载卸载预览"""
        self.status_label.config(text="获取卸载信息...")

        def do_load():
            try:
                from scripts.uninstall import get_preview_script, parse_preview_output

                script = get_preview_script()
                ec, out, _ = self.ssh.exec(script, timeout=30)

                if ec == 0:
                    self.preview = parse_preview_output(out)
                    self.log_queue.put(("preview_done", self.preview))
                else:
                    self.log_queue.put(("error", f"预览失败: {out[:100]}"))

            except Exception as e:
                self.log_queue.put(("error", str(e)))

        threading.Thread(target=do_load, daemon=True).start()
        self.dialog.after(200, self._check_queue)

    def _check_queue(self):
        """检查队列"""
        try:
            while True:
                item = self.log_queue.get_nowait()
                kind = item[0]

                if kind == "preview_done":
                    self._show_preview(item[1])
                    break
                elif kind == "error":
                    self.status_label.config(text=item[1])
                    break
                elif kind == "uninstall_done":
                    self._on_uninstall_complete(item[1], item[2])
                    break

        except queue.Empty:
            pass

        if self.dialog.winfo_exists():
            self.dialog.after(200, self._check_queue)

    def _show_preview(self, preview):
        """显示预览信息"""
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")

        # 服务状态
        self.preview_text.insert("end", "【服务状态】\n")
        if preview.service_installed:
            status = "运行中" if preview.service_active else "已停止"
            self.preview_text.insert("end", f"  • systemd 服务: 已安装（{status}）\n")
        else:
            self.preview_text.insert("end", "  • systemd 服务: 未安装\n")

        # 安装目录
        self.preview_text.insert("end", "\n【安装目录】\n")
        if preview.install_dir_exists:
            self.preview_text.insert("end", f"  • /opt/ai-nas: 存在\n")
            for f in preview.files_to_remove[:5]:
                self.preview_text.insert("end", f"    - {f}\n")
        else:
            self.preview_text.insert("end", "  • /opt/ai-nas: 不存在\n")

        # 备份
        self.preview_text.insert("end", "\n【备份文件】\n")
        self.preview_text.insert("end", f"  • 备份数量: {preview.backup_count}\n")

        # 数据目录
        self.preview_text.insert("end", "\n【数据目录】\n")
        if preview.data_dir_exists:
            self.preview_text.insert("end", f"  • 数据大小: {preview.data_size}\n")
            for d in preview.dirs_to_remove:
                self.preview_text.insert("end", f"    - {d}\n")
        else:
            self.preview_text.insert("end", "  • 无数据目录\n")

        # 配置
        self.preview_text.insert("end", "\n【配置文件】\n")
        self.preview_text.insert(
            "end", f"  • config.yaml: {'存在' if preview.config_exists else '不存在'}\n"
        )

        self.preview_text.configure(state="disabled")

        # 更新状态
        if preview.has_content:
            self.status_label.config(text="预览加载完成")
            self.uninstall_btn.config(state="normal")
        else:
            self.status_label.config(text="未检测到已安装内容")

    def _on_uninstall(self):
        """开始卸载"""
        mode = self.mode.get()

        # 确认对话框
        if mode == "full":
            msg = "⚠ 完全卸载将删除所有内容，包括数据！\n\n此操作不可恢复，确定继续吗？"
            if not messagebox.askyesno("确认完全卸载", msg, parent=self.dialog):
                return
        else:
            msg = "确定执行安全卸载吗？\n\n将停止服务并删除程序文件，保留数据和配置。"
            if not messagebox.askyesno("确认卸载", msg, parent=self.dialog):
                return

        # 禁用按钮
        self.uninstall_btn.config(state="disabled", text="卸载中...")
        self.cancel_btn.config(state="disabled")
        self.status_label.config(text="执行卸载...")

        def do_uninstall():
            try:
                from scripts.uninstall import get_uninstall_script
                from scripts.verify import (
                    get_verify_uninstall_script,
                    parse_verify_uninstall_output,
                )

                # 执行卸载脚本
                script = get_uninstall_script(mode=mode)
                ec, out, _ = self.ssh.exec(script, timeout=120)

                if ec == 0:
                    # 验证卸载
                    verify_script = get_verify_uninstall_script()
                    vec, vout, _ = self.ssh.exec(verify_script, timeout=30)

                    if vec == 0:
                        success, issues = parse_verify_uninstall_output(vout)
                        self.log_queue.put(("uninstall_done", success, out))
                    else:
                        self.log_queue.put(("uninstall_done", False, out))
                else:
                    self.log_queue.put(("uninstall_done", False, out))

            except Exception as e:
                self.log_queue.put(("uninstall_done", False, str(e)))

        threading.Thread(target=do_uninstall, daemon=True).start()

    def _on_uninstall_complete(self, success: bool, output: str):
        """卸载完成"""
        self.uninstall_btn.config(state="normal", text="开始卸载")
        self.cancel_btn.config(state="normal")

        if success:
            self.status_label.config(text="卸载成功", fg=GREEN)

            # 显示结果
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("end", "卸载成功！\n\n")
            self.preview_text.insert(
                "end", output[-500:] if len(output) > 500 else output
            )
            self.preview_text.configure(state="disabled")

            # 回调
            if self.on_complete:
                self.on_complete(True)

            # 延迟关闭
            self.dialog.after(2000, self.dialog.destroy)

        else:
            self.status_label.config(text="卸载失败", fg=RED)
            messagebox.showerror(
                "卸载失败", f"卸载过程中出错:\n{output[:200]}", parent=self.dialog
            )

    def _on_cancel(self):
        """取消"""
        self.dialog.destroy()


# ══════════════════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════════════════


def show_uninstall_dialog(parent: tk.Tk, ssh, on_complete: Optional[Callable] = None):
    """显示卸载对话框"""
    return UninstallDialog(parent, ssh, on_complete)
