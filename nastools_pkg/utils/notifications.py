# -*- coding: utf-8 -*-
"""
utils/notifications.py — 统一通知与确认对话框

v1.1 安全底线核心模块。
所有弹框必须通过本模块，禁止直接调用 messagebox。
"""

import tkinter as tk
from tkinter import messagebox
from typing import Optional

# ── 配色（与 theme.py 保持一致）────────────────────────────────────
RED = "#ff4444"
ORANGE = "#ff9933"
YELLOW = "#ffcc00"
BG_DARK = "#0d1117"
TEXT_BRIGHT = "#e6edf3"
PANEL = "#161b22"

# ══════════════════════════════════════════════════════════════════
# 通知类（右下角气泡，不需要用户操作）
# ══════════════════════════════════════════════════════════════════


def notify_success(root: tk.Tk, message: str, duration: int = 2500):
    """操作成功，右下角绿色气泡提示（自动消失）"""
    _toast(root, message, "#2ea043", duration)


def notify_error(root: tk.Tk, message: str, duration: int = 4000):
    """操作失败，右下角红色气泡提示（自动消失）"""
    _toast(root, message, RED, duration)


def notify_warning(root: tk.Tk, message: str, duration: int = 3000):
    """警告提示，右下角橙色气泡（自动消失）"""
    _toast(root, message, ORANGE, duration)


def _toast(root: tk.Tk, message: str, color: str, duration: int):
    """内部气泡实现"""
    win = tk.Toplevel(root)
    win.attributes("-topmost", True)
    win.overrideredirect(True)

    # 定位到右下角
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    ww, wh = 320, 50
    x = sw - ww - 20
    y = sh - wh - 20
    win.geometry(f"{ww}x{wh}+{x}+{y}")

    frame = tk.Frame(win, bg=color, relief="ridge", bd=2)
    frame.pack(fill="both", expand=True)

    label = tk.Label(
        frame,
        text=message,
        bg=color,
        fg="white",
        font=("Microsoft YaHei", 9),
        anchor="w",
        padx=12,
        pady=8,
    )
    label.pack(fill="x")

    def fade_and_close():
        try:
            alpha = 1.0
            while alpha > 0:
                alpha -= 0.1
                win.attributes("-alpha", alpha)
                win.update()
                time.sleep(0.03)
            win.destroy()
        except Exception:
            pass

    # 鼠标点击关闭
    frame.bind("<Button-1>", lambda e: fade_and_close())
    label.bind("<Button-1>", lambda e: fade_and_close())

    win.after(duration, fade_and_close)


# ══════════════════════════════════════════════════════════════════
# confirmDanger — 危险操作确认对话框
# ══════════════════════════════════════════════════════════════════


class DangerDialog:
    """
    危险操作确认框。

    参数：
        parent    父窗口
        title     窗口标题
        risk      风险等级："high" / "medium" / "low"
        message   操作说明（一句话）
        details   详细说明（可多行）
        warnings  警告事项列表

    返回：True = 用户确认，False = 用户取消
    """

    RISK_COLORS = {
        "high": ("#c0392b", "#ff4444"),  # 深红背景 / 亮红标题
        "medium": ("#d35400", "#ff9933"),  # 深橙背景 / 橙色标题
        "low": ("#1a5276", "#4aa3df"),  # 深蓝背景 / 蓝色标题
    }
    RISK_LABELS = {
        "high": "🔴  极高风险  ",
        "medium": "🟠  高风险    ",
        "low": "🟡  中风险    ",
    }

    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        risk: str,
        message: str,
        details: str = "",
        warnings: list = None,
    ):
        self.result = False
        warnings = warnings or []

        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.grab_set()  # 模态：禁止操作父窗口

        # 深色背景
        self.win.configure(bg=BG_DARK)

        # 窗口居中
        ww, wh = 480, 380
        self.win.update_idletasks()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f"{ww}x{wh}+{(sw - ww) // 2}+{(sh - wh) // 2}")

        bg, accent = self.RISK_COLORS[risk]

        # ── 标题栏 ───────────────────────────────────────────────
        title_bar = tk.Frame(self.win, bg=accent, height=44)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        tk.Label(
            title_bar,
            text=self.RISK_LABELS[risk] + title,
            bg=accent,
            fg="white",
            font=("Microsoft YaHei", 12, "bold"),
            anchor="w",
            padx=14,
        ).pack(fill="x")

        # ── 内容区 ───────────────────────────────────────────────
        body = tk.Frame(self.win, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # 操作说明
        tk.Label(
            body,
            text=message,
            bg=BG_DARK,
            fg=TEXT_BRIGHT,
            font=("Microsoft YaHei", 11),
            anchor="w",
            justify="left",
            wraplength=440,
        ).pack(anchor="w")

        # 详细说明（如果有）
        if details:
            detail_frame = tk.Frame(body, bg="#1c2128", relief="solid", bd=1)
            detail_frame.pack(fill="x", pady=(10, 0))
            tk.Label(
                detail_frame,
                text=details,
                bg="#1c2128",
                fg="#8b949e",
                font=("Consolas", 8),
                anchor="w",
                justify="left",
                wraplength=420,
                padx=10,
                pady=8,
            ).pack(fill="x")

        # 警告事项
        if warnings:
            warn_title = tk.Label(
                body,
                text="⚠  风险提示",
                bg=BG_DARK,
                fg=YELLOW,
                font=("Microsoft YaHei", 9, "bold"),
                anchor="w",
                pady=(12, 4),
            )
            warn_title.pack(anchor="w")
            for w in warnings:
                tk.Label(
                    body,
                    text=f"• {w}",
                    bg=BG_DARK,
                    fg="#ffaa44",
                    font=("Microsoft YaHei", 9),
                    anchor="w",
                    wraplength=440,
                ).pack(anchor="w", padx=8)

        # ── 极高风险：必须输入"确认"才能解锁 ─────────────────────
        confirm_input = None
        if risk == "high":
            confirm_label = tk.Label(
                body,
                text="为确认您已充分了解风险，请在上方输入「确认」：",
                bg=BG_DARK,
                fg="#ff8888",
                font=("Microsoft YaHei", 9),
                anchor="w",
                pady=(12, 4),
            )
            confirm_label.pack(anchor="w")

            confirm_input = tk.Entry(
                body,
                bg="#1c2128",
                fg=TEXT_BRIGHT,
                font=("Microsoft YaHei", 11),
                justify="center",
                insertbackground=TEXT_BRIGHT,
                relief="solid",
                bd=1,
                width=20,
            )
            confirm_input.pack(anchor="w", padx=8)
            confirm_input.focus_set()

        # ── 按钮区 ───────────────────────────────────────────────
        btn_bar = tk.Frame(self.win, bg="#1c2128")
        btn_bar.pack(fill="x", padx=20, pady=(0, 16))

        def on_ok():
            if risk == "high":
                val = confirm_input.get().strip()
                if val != "确认":
                    tk.Label(
                        body,
                        text="请输入「确认」方可继续",
                        bg=BG_DARK,
                        fg=RED,
                        font=("Microsoft YaHei", 9),
                    ).pack(anchor="w")
                    return
            self.result = True
            self.win.destroy()

        def on_cancel():
            self.win.destroy()

        # 取消按钮（始终可用）
        tk.Button(
            btn_bar,
            text="取消",
            command=on_cancel,
            bg="#21262d",
            fg="#8b949e",
            font=("Microsoft YaHei", 10),
            activebackground="#30363d",
            activeforeground=TEXT_BRIGHT,
            relief="flat",
            padx=16,
            pady=6,
        ).pack(side="right", padx=(8, 0))

        # 确认按钮（根据风险等级着色）
        ok_colors = {
            "high": ("#8b0000", "#ff4444"),
            "medium": ("#7d3c00", "#ff9933"),
            "low": ("#0d4a6e", "#4aa3df"),
        }
        bg_btn, fg_btn = ok_colors[risk]
        ok_btn = tk.Button(
            btn_bar,
            text="我已知悉风险，执行操作",
            command=on_ok,
            bg=bg_btn,
            fg="white",
            font=("Microsoft YaHei", 10, "bold"),
            activebackground=fg_btn,
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=6,
            state="disabled",
        )
        ok_btn.pack(side="right")

        # 极高风险：输入"确认"后解锁按钮
        if risk == "high":

            def on_type(*args):
                ok_btn.config(
                    state="normal"
                    if confirm_input.get().strip() == "确认"
                    else "disabled"
                )

            confirm_input.bind("<KeyRelease>", on_type)
        else:
            ok_btn.config(state="normal")

        # ESC 键取消
        self.win.bind("<Escape>", lambda e: on_cancel())

    def show(self) -> bool:
        self.win.wait_window()
        return self.result


# ══════════════════════════════════════════════════════════════════
# 便捷函数（单向入口，供 app.py 调用）
# ══════════════════════════════════════════════════════════════════


def confirm_danger(
    parent: tk.Tk,
    title: str,
    risk: str,
    message: str,
    details: str = "",
    warnings: list = None,
) -> bool:
    """
    显示危险操作确认框。

    用法：
        ok = confirm_danger(
            parent=app.root,
            title="部署 NAS 系统",
            risk="high",
            message="将在 ARM 设备上部署 NAS 管理系统",
            details="将覆盖 /opt/ai-nas/arm_server.py\n将重启 ai-nas-arm 服务",
            warnings=[
                "部署过程将重启 NAS 服务（约 10 秒中断）",
                "现有数据目录不会被删除",
                "回滚命令：sudo bash /opt/ai-nas/nastools-rollback.sh",
            ]
        )
        if not ok:
            return
        # 执行危险操作...
    """
    dlg = DangerDialog(parent, title, risk, message, details, warnings)
    return dlg.show()


def notify_done(root: tk.Tk, operation: str, ok: bool, detail: str = ""):
    """操作完成后弹出提示（兼容所有操作）"""
    if ok:
        notify_success(root, f"✅ {operation} 完成")
    else:
        notify_error(root, f"❌ {operation} 失败：{detail}")


import time  # for _toast fade animation
