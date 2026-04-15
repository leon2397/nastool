# -*- coding: utf-8 -*-
"""
gui/storage_health_dialog.py — 存储健康检测对话框
SMART / 温度 / RAID / 趋势
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional

from core.storage_health import (
    check_storage_health,
    get_trend,
    save_history,
    format_report,
    StorageHealthReport,
    SMARTStatus,
    RAIDStatus,
)


class StorageHealthDialog:
    """存储健康检测对话框"""

    def __init__(self, parent: Optional[tk.Tk] = None, ssh_client=None):
        self.parent = parent or tk.Tk()
        self.ssh_client = ssh_client
        self.report: Optional[StorageHealthReport] = None

        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        """构建 UI"""
        self.parent.title("存储健康检测")
        self.parent.geometry("900x700")

        # 主框架
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ────────────────────────────────────────────────────────────
        # 顶部：健康分数 + 刷新按钮
        # ────────────────────────────────────────────────────────────
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # 健康分数
        score_frame = ttk.LabelFrame(top_frame, text="健康分数", padding="10")
        score_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.score_label = ttk.Label(
            score_frame, text="--/100", font=("Arial", 24, "bold")
        )
        self.score_label.pack(side=tk.LEFT)

        self.status_label = ttk.Label(score_frame, text="检测中...", font=("Arial", 12))
        self.status_label.pack(side=tk.LEFT, padx=20)

        # 刷新按钮
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="🔄 刷新", command=self._refresh).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="📊 趋势", command=self._show_trend).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="💾 导出", command=self._export).pack(
            side=tk.LEFT, padx=5
        )

        # ────────────────────────────────────────────────────────────
        # 中部：Notebook（SMART / RAID / 温度 / 问题）
        # ────────────────────────────────────────────────────────────
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # SMART 页
        smart_frame = ttk.Frame(notebook, padding="10")
        notebook.add(smart_frame, text="📊 SMART")
        self._setup_smart_tab(smart_frame)

        # RAID 页
        raid_frame = ttk.Frame(notebook, padding="10")
        notebook.add(raid_frame, text="💿 RAID")
        self._setup_raid_tab(raid_frame)

        # 温度页
        temp_frame = ttk.Frame(notebook, padding="10")
        notebook.add(temp_frame, text="🌡️ 温度")
        self._setup_temp_tab(temp_frame)

        # 问题页
        issues_frame = ttk.Frame(notebook, padding="10")
        notebook.add(issues_frame, text="⚠️ 问题")
        self._setup_issues_tab(issues_frame)

        # ────────────────────────────────────────────────────────────
        # 底部：状态栏
        # ────────────────────────────────────────────────────────────
        self.time_label = ttk.Label(main_frame, text="", font=("Arial", 9))
        self.time_label.pack(fill=tk.X, pady=(10, 0))

    def _setup_smart_tab(self, parent: ttk.Frame):
        """SMART 信息页"""
        # 表格
        columns = (
            "device",
            "model",
            "status",
            "temp",
            "power_on",
            "reallocated",
            "pending",
        )
        self.smart_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=15
        )

        self.smart_tree.heading("device", text="设备")
        self.smart_tree.heading("model", text="型号")
        self.smart_tree.heading("status", text="状态")
        self.smart_tree.heading("temp", text="温度")
        self.smart_tree.heading("power_on", text="通电时间")
        self.smart_tree.heading("reallocated", text="重分配扇区")
        self.smart_tree.heading("pending", text="待处理扇区")

        self.smart_tree.column("device", width=80)
        self.smart_tree.column("model", width=150)
        self.smart_tree.column("status", width=80)
        self.smart_tree.column("temp", width=60)
        self.smart_tree.column("power_on", width=100)
        self.smart_tree.column("reallocated", width=100)
        self.smart_tree.column("pending", width=100)

        self.smart_tree.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = ttk.Scrollbar(
            parent, orient=tk.VERTICAL, command=self.smart_tree.yview
        )
        self.smart_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _setup_raid_tab(self, parent: ttk.Frame):
        """RAID 信息页"""
        columns = ("device", "level", "status", "size", "used", "members", "progress")
        self.raid_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=10
        )

        self.raid_tree.heading("device", text="设备")
        self.raid_tree.heading("level", text="级别")
        self.raid_tree.heading("status", text="状态")
        self.raid_tree.heading("size", text="容量")
        self.raid_tree.heading("used", text="已用")
        self.raid_tree.heading("members", text="成员")
        self.raid_tree.heading("progress", text="重建进度")

        self.raid_tree.column("device", width=80)
        self.raid_tree.column("level", width=60)
        self.raid_tree.column("status", width=80)
        self.raid_tree.column("size", width=80)
        self.raid_tree.column("used", width=80)
        self.raid_tree.column("members", width=200)
        self.raid_tree.column("progress", width=100)

        self.raid_tree.pack(fill=tk.BOTH, expand=True)

    def _setup_temp_tab(self, parent: ttk.Frame):
        """温度信息页"""
        # 汇总
        summary_frame = ttk.LabelFrame(parent, text="温度汇总", padding="10")
        summary_frame.pack(fill=tk.X, pady=(0, 10))

        self.temp_max_label = ttk.Label(summary_frame, text="最高: --°C")
        self.temp_max_label.pack(side=tk.LEFT, padx=20)

        self.temp_min_label = ttk.Label(summary_frame, text="最低: --°C")
        self.temp_min_label.pack(side=tk.LEFT, padx=20)

        self.temp_avg_label = ttk.Label(summary_frame, text="平均: --°C")
        self.temp_avg_label.pack(side=tk.LEFT, padx=20)

        # 设备温度表格
        columns = ("device", "temp", "status")
        self.temp_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=10
        )

        self.temp_tree.heading("device", text="设备")
        self.temp_tree.heading("temp", text="温度 (°C)")
        self.temp_tree.heading("status", text="状态")

        self.temp_tree.column("device", width=150)
        self.temp_tree.column("temp", width=100)
        self.temp_tree.column("status", width=100)

        self.temp_tree.pack(fill=tk.BOTH, expand=True)

    def _setup_issues_tab(self, parent: ttk.Frame):
        """问题页"""
        # 严重问题
        critical_frame = ttk.LabelFrame(parent, text="❌ 严重问题", padding="10")
        critical_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.issues_text = tk.Text(critical_frame, height=8, wrap=tk.WORD)
        self.issues_text.pack(fill=tk.BOTH, expand=True)

        # 警告
        warning_frame = ttk.LabelFrame(parent, text="⚠️ 警告", padding="10")
        warning_frame.pack(fill=tk.BOTH, expand=True)

        self.warnings_text = tk.Text(warning_frame, height=8, wrap=tk.WORD)
        self.warnings_text.pack(fill=tk.BOTH, expand=True)

    def _refresh(self):
        """刷新数据"""
        self.status_label.config(text="检测中...")

        try:
            # 执行检测
            if self.ssh_client:
                # 远程检测
                self.report = self._remote_check()
            else:
                # 本地检测
                self.report = check_storage_health()

            # 保存历史
            save_history(self.report)

            # 更新 UI
            self._update_ui()

        except Exception as e:
            messagebox.showerror("错误", f"检测失败: {e}")
            self.status_label.config(text="检测失败")

    def _remote_check(self) -> StorageHealthReport:
        """远程检测（通过 SSH）"""
        # TODO: 实现 SSH 远程检测
        # 1. 上传检测脚本
        # 2. 执行
        # 3. 获取结果
        return check_storage_health()

    def _update_ui(self):
        """更新 UI"""
        if not self.report:
            return

        # 健康分数
        score = self.report.health_score
        self.score_label.config(text=f"{score}/100")

        # 分数颜色
        if score >= 80:
            color = "green"
        elif score >= 60:
            color = "orange"
        else:
            color = "red"
        self.score_label.config(foreground=color)

        # 状态
        if self.report.ok:
            self.status_label.config(text="✅ 健康", foreground="green")
        else:
            self.status_label.config(text="❌ 需要维护", foreground="red")

        # 时间
        self.time_label.config(text=f"检测时间: {self.report.timestamp}")

        # SMART 表格
        self.smart_tree.delete(*self.smart_tree.get_children())
        for d in self.report.smart_data:
            status_str = (
                "✅ 正常"
                if d.status == SMARTStatus.PASSED
                else "⚠️ 警告"
                if d.status == SMARTStatus.WARNING
                else "❌ 失败"
                if d.status == SMARTStatus.FAILED
                else "未知"
            )

            power_on_str = (
                f"{d.power_on_hours:,} 小时" if d.power_on_hours > 0 else "--"
            )
            temp_str = f"{d.temperature}°C" if d.temperature > 0 else "--"

            self.smart_tree.insert(
                "",
                tk.END,
                values=(
                    d.device,
                    d.model or "--",
                    status_str,
                    temp_str,
                    power_on_str,
                    str(d.reallocated_sectors),
                    str(d.pending_sectors),
                ),
            )

        # RAID 表格
        self.raid_tree.delete(*self.raid_tree.get_children())
        for r in self.report.raid_data:
            status_str = (
                "✅ 正常"
                if r.status == RAIDStatus.CLEAN
                else "⚠️ 降级"
                if r.status == RAIDStatus.DEGRADED
                else "🔄 重建"
                if r.status == RAIDStatus.REBUILDING
                else "❌ 失败"
                if r.status == RAIDStatus.FAILED
                else "未知"
            )

            members_str = ", ".join([m.device for m in r.members])
            progress_str = (
                f"{r.rebuild_progress:.1f}%" if r.rebuild_progress > 0 else "--"
            )

            self.raid_tree.insert(
                "",
                tk.END,
                values=(
                    r.device,
                    r.level,
                    status_str,
                    f"{r.size_gb:.1f} GB",
                    f"{r.used_gb:.1f} GB",
                    members_str,
                    progress_str,
                ),
            )

        # 温度
        ts = self.report.temperature_summary
        self.temp_max_label.config(text=f"最高: {ts.get('max', 0)}°C")
        self.temp_min_label.config(text=f"最低: {ts.get('min', 0)}°C")
        self.temp_avg_label.config(text=f"平均: {ts.get('avg', 0)}°C")

        self.temp_tree.delete(*self.temp_tree.get_children())
        for dev, temp in ts.get("by_device", {}).items():
            if temp >= 60:
                status = "❌ 过热"
            elif temp >= 50:
                status = "⚠️ 偏热"
            else:
                status = "✅ 正常"

            self.temp_tree.insert("", tk.END, values=(dev, temp, status))

        # 问题
        self.issues_text.delete("1.0", tk.END)
        if self.report.issues:
            self.issues_text.insert("1.0", "\n".join(self.report.issues))
        else:
            self.issues_text.insert("1.0", "无严重问题")

        self.warnings_text.delete("1.0", tk.END)
        if self.report.warnings:
            self.warnings_text.insert("1.0", "\n".join(self.report.warnings))
        else:
            self.warnings_text.insert("1.0", "无警告")

    def _show_trend(self):
        """显示趋势"""
        trend = get_trend(days=7)
        if not trend:
            messagebox.showinfo("趋势", "暂无历史数据")
            return

        # 创建趋势窗口
        trend_win = tk.Toplevel(self.parent)
        trend_win.title("存储健康趋势（7天）")
        trend_win.geometry("600x400")

        # 健康分数趋势
        score_frame = ttk.LabelFrame(trend_win, text="健康分数趋势", padding="10")
        score_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scores = trend.get("health_scores", [])
        if scores:
            score_text = f"最低: {min(scores)}, 最高: {max(scores)}, 平均: {sum(scores) / len(scores):.1f}"
            ttk.Label(score_frame, text=score_text).pack()

            # 简单文本图表
            chart_lines = []
            for i, s in enumerate(scores[-20:]):  # 最近 20 条
                bar_len = int(s / 2)
                bar = "█" * bar_len
                chart_lines.append(f"{i + 1:2d}: {bar} {s}")
            ttk.Label(
                score_frame, text="\n".join(chart_lines), font=("Courier", 8)
            ).pack()

        # 事件统计
        event_frame = ttk.LabelFrame(trend_win, text="事件统计", padding="10")
        event_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(
            event_frame, text=f"SMART 失败事件: {trend.get('smart_failures', 0)}"
        ).pack(anchor=tk.W)
        ttk.Label(
            event_frame, text=f"RAID 降级事件: {trend.get('raid_degraded_events', 0)}"
        ).pack(anchor=tk.W)

    def _export(self):
        """导出报告"""
        if not self.report:
            messagebox.showwarning("警告", "请先执行检测")
            return

        from tkinter import filedialog

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("JSON 文件", "*.json")],
            initialfile=f"storage_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )

        if not filepath:
            return

        try:
            if filepath.endswith(".json"):
                import json
                from dataclasses import asdict

                data = asdict(self.report)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(format_report(self.report, verbose=True))

            messagebox.showinfo("成功", f"报告已保存到: {filepath}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")


def show_storage_health_dialog(parent=None, ssh_client=None):
    """显示存储健康检测对话框"""
    dialog = StorageHealthDialog(parent, ssh_client)
    if not parent:
        dialog.parent.mainloop()
    return dialog


if __name__ == "__main__":
    show_storage_health_dialog()
