# -*- coding: utf-8 -*-
"""
gui/nas_health_dialog.py — NAS 健康检测对话框
DSM 版本 / 账号 / 共享 / UPS / cron / 日志
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, List

from core.nas_health import check_nas_health, format_report, NASHealthReport, UPSStatus


class NASHealthDialog:
    """NAS 健康检测对话框"""

    def __init__(self, parent: Optional[tk.Tk] = None, ssh_client=None):
        self.parent = parent or tk.Tk()
        self.ssh_client = ssh_client
        self.report: Optional[NASHealthReport] = None

        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        """构建 UI"""
        self.parent.title("NAS 健康检测")
        self.parent.geometry("950x750")

        # 主框架
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ────────────────────────────────────────────────────────────
        # 顶部：健康分数 + 操作按钮
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

        # 按钮
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="🔄 刷新", command=self._refresh).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="💾 导出", command=self._export).pack(
            side=tk.LEFT, padx=5
        )

        # ────────────────────────────────────────────────────────────
        # 中部：Notebook（DSM / 账号 / 共享 / UPS / Cron / 日志 / 问题）
        # ────────────────────────────────────────────────────────────
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # DSM 页
        dsm_frame = ttk.Frame(notebook, padding="10")
        notebook.add(dsm_frame, text="🖥️ DSM")
        self._setup_dsm_tab(dsm_frame)

        # 账号页
        account_frame = ttk.Frame(notebook, padding="10")
        notebook.add(account_frame, text="👥 账号")
        self._setup_account_tab(account_frame)

        # 共享页
        share_frame = ttk.Frame(notebook, padding="10")
        notebook.add(share_frame, text="📁 共享")
        self._setup_share_tab(share_frame)

        # UPS 页
        ups_frame = ttk.Frame(notebook, padding="10")
        notebook.add(ups_frame, text="🔋 UPS")
        self._setup_ups_tab(ups_frame)

        # Cron 页
        cron_frame = ttk.Frame(notebook, padding="10")
        notebook.add(cron_frame, text="⏰ Cron")
        self._setup_cron_tab(cron_frame)

        # 日志页
        log_frame = ttk.Frame(notebook, padding="10")
        notebook.add(log_frame, text="📋 日志")
        self._setup_log_tab(log_frame)

        # 问题页
        issues_frame = ttk.Frame(notebook, padding="10")
        notebook.add(issues_frame, text="⚠️ 问题")
        self._setup_issues_tab(issues_frame)

        # ────────────────────────────────────────────────────────────
        # 底部：状态栏
        # ────────────────────────────────────────────────────────────
        self.time_label = ttk.Label(main_frame, text="", font=("Arial", 9))
        self.time_label.pack(fill=tk.X, pady=(10, 0))

    def _setup_dsm_tab(self, parent: ttk.Frame):
        """DSM 系统信息页"""
        # 基本信息
        info_frame = ttk.LabelFrame(parent, text="系统信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.dsm_version_label = ttk.Label(info_frame, text="版本: --")
        self.dsm_version_label.pack(anchor=tk.W)

        self.dsm_build_label = ttk.Label(info_frame, text="Build: --")
        self.dsm_build_label.pack(anchor=tk.W)

        self.dsm_model_label = ttk.Label(info_frame, text="型号: --")
        self.dsm_model_label.pack(anchor=tk.W)

        self.dsm_serial_label = ttk.Label(info_frame, text="序列号: --")
        self.dsm_serial_label.pack(anchor=tk.W)

        self.dsm_uptime_label = ttk.Label(info_frame, text="运行时间: --")
        self.dsm_uptime_label.pack(anchor=tk.W)

        # 资源使用
        usage_frame = ttk.LabelFrame(parent, text="资源使用", padding="10")
        usage_frame.pack(fill=tk.X, pady=(0, 10))

        # CPU
        cpu_frame = ttk.Frame(usage_frame)
        cpu_frame.pack(fill=tk.X, pady=5)

        ttk.Label(cpu_frame, text="CPU:").pack(side=tk.LEFT)
        self.dsm_cpu_label = ttk.Label(
            cpu_frame, text="--%", font=("Arial", 14, "bold")
        )
        self.dsm_cpu_label.pack(side=tk.LEFT, padx=10)

        self.dsm_cpu_bar = ttk.Progressbar(
            cpu_frame, length=200, mode="determinate", maximum=100
        )
        self.dsm_cpu_bar.pack(side=tk.LEFT, padx=10)

        # 内存
        mem_frame = ttk.Frame(usage_frame)
        mem_frame.pack(fill=tk.X, pady=5)

        ttk.Label(mem_frame, text="内存:").pack(side=tk.LEFT)
        self.dsm_mem_label = ttk.Label(
            mem_frame, text="--%", font=("Arial", 14, "bold")
        )
        self.dsm_mem_label.pack(side=tk.LEFT, padx=10)

        self.dsm_mem_bar = ttk.Progressbar(
            mem_frame, length=200, mode="determinate", maximum=100
        )
        self.dsm_mem_bar.pack(side=tk.LEFT, padx=10)

        # 温度
        temp_frame = ttk.Frame(usage_frame)
        temp_frame.pack(fill=tk.X, pady=5)

        ttk.Label(temp_frame, text="温度:").pack(side=tk.LEFT)
        self.dsm_temp_label = ttk.Label(
            temp_frame, text="--°C", font=("Arial", 14, "bold")
        )
        self.dsm_temp_label.pack(side=tk.LEFT, padx=10)

    def _setup_account_tab(self, parent: ttk.Frame):
        """账号页"""
        columns = ("username", "uid", "groups", "admin")
        self.account_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=15
        )

        self.account_tree.heading("username", text="用户名")
        self.account_tree.heading("uid", text="UID")
        self.account_tree.heading("groups", text="用户组")
        self.account_tree.heading("admin", text="管理员")

        self.account_tree.column("username", width=150)
        self.account_tree.column("uid", width=80)
        self.account_tree.column("groups", width=300)
        self.account_tree.column("admin", width=80)

        self.account_tree.pack(fill=tk.BOTH, expand=True)

    def _setup_share_tab(self, parent: ttk.Frame):
        """共享文件夹页"""
        columns = ("name", "path", "size", "used", "usage")
        self.share_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=12
        )

        self.share_tree.heading("name", text="名称")
        self.share_tree.heading("path", text="路径")
        self.share_tree.heading("size", text="容量")
        self.share_tree.heading("used", text="已用")
        self.share_tree.heading("usage", text="使用率")

        self.share_tree.column("name", width=100)
        self.share_tree.column("path", width=200)
        self.share_tree.column("size", width=80)
        self.share_tree.column("used", width=80)
        self.share_tree.column("usage", width=80)

        self.share_tree.pack(fill=tk.BOTH, expand=True)

    def _setup_ups_tab(self, parent: ttk.Frame):
        """UPS 页"""
        # 状态
        status_frame = ttk.LabelFrame(parent, text="UPS 状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.ups_status_label = ttk.Label(
            status_frame, text="状态: --", font=("Arial", 14)
        )
        self.ups_status_label.pack(anchor=tk.W)

        self.ups_model_label = ttk.Label(status_frame, text="型号: --")
        self.ups_model_label.pack(anchor=tk.W)

        # 电量
        battery_frame = ttk.LabelFrame(parent, text="电池", padding="10")
        battery_frame.pack(fill=tk.X, pady=(0, 10))

        self.ups_charge_label = ttk.Label(battery_frame, text="电量: --%")
        self.ups_charge_label.pack(anchor=tk.W)

        self.ups_runtime_label = ttk.Label(battery_frame, text="续航: -- 分钟")
        self.ups_runtime_label.pack(anchor=tk.W)

        # 负载
        load_frame = ttk.LabelFrame(parent, text="负载", padding="10")
        load_frame.pack(fill=tk.X, pady=(0, 10))

        self.ups_load_label = ttk.Label(load_frame, text="负载: --%")
        self.ups_load_label.pack(anchor=tk.W)

        self.ups_input_label = ttk.Label(load_frame, text="输入电压: -- V")
        self.ups_input_label.pack(anchor=tk.W)

        self.ups_output_label = ttk.Label(load_frame, text="输出电压: -- V")
        self.ups_output_label.pack(anchor=tk.W)

    def _setup_cron_tab(self, parent: ttk.Frame):
        """Cron 任务页"""
        columns = ("schedule", "user", "command")
        self.cron_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=15
        )

        self.cron_tree.heading("schedule", text="计划")
        self.cron_tree.heading("user", text="用户")
        self.cron_tree.heading("command", text="命令")

        self.cron_tree.column("schedule", width=150)
        self.cron_tree.column("user", width=80)
        self.cron_tree.column("command", width=400)

        self.cron_tree.pack(fill=tk.BOTH, expand=True)

    def _setup_log_tab(self, parent: ttk.Frame):
        """日志页"""
        # 统计
        stats_frame = ttk.LabelFrame(
            parent, text="日志统计（最近 1 小时）", padding="10"
        )
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.log_error_label = ttk.Label(stats_frame, text="错误: --")
        self.log_error_label.pack(side=tk.LEFT, padx=20)

        self.log_warning_label = ttk.Label(stats_frame, text="警告: --")
        self.log_warning_label.pack(side=tk.LEFT, padx=20)

        self.log_info_label = ttk.Label(stats_frame, text="信息: --")
        self.log_info_label.pack(side=tk.LEFT, padx=20)

        # 日志表格
        columns = ("timestamp", "level", "source", "message")
        self.log_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=12
        )

        self.log_tree.heading("timestamp", text="时间")
        self.log_tree.heading("level", text="级别")
        self.log_tree.heading("source", text="来源")
        self.log_tree.heading("message", text="消息")

        self.log_tree.column("timestamp", width=150)
        self.log_tree.column("level", width=60)
        self.log_tree.column("source", width=100)
        self.log_tree.column("message", width=300)

        self.log_tree.pack(fill=tk.BOTH, expand=True)

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
                self.report = self._remote_check()
            else:
                self.report = check_nas_health()

            # 更新 UI
            self._update_ui()

        except Exception as e:
            messagebox.showerror("错误", f"检测失败: {e}")
            self.status_label.config(text="检测失败")

    def _remote_check(self) -> NASHealthReport:
        """远程检测"""
        return check_nas_health()

    def _update_ui(self):
        """更新 UI"""
        if not self.report:
            return

        # 健康分数
        score = self.report.health_score
        self.score_label.config(text=f"{score}/100")

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

        # DSM
        dsm = self.report.dsm
        self.dsm_version_label.config(text=f"版本: DSM {dsm.version}")
        self.dsm_build_label.config(text=f"Build: {dsm.build}")
        self.dsm_model_label.config(text=f"型号: {dsm.model}")
        self.dsm_serial_label.config(text=f"序列号: {dsm.serial}")
        self.dsm_uptime_label.config(text=f"运行时间: {dsm.uptime}")

        # CPU
        self.dsm_cpu_label.config(text=f"{dsm.cpu_usage:.1f}%")
        self.dsm_cpu_bar["value"] = dsm.cpu_usage
        if dsm.cpu_usage > 80:
            self.dsm_cpu_label.config(foreground="red")
        elif dsm.cpu_usage > 60:
            self.dsm_cpu_label.config(foreground="orange")
        else:
            self.dsm_cpu_label.config(foreground="green")

        # 内存
        self.dsm_mem_label.config(text=f"{dsm.memory_usage:.1f}%")
        self.dsm_mem_bar["value"] = dsm.memory_usage
        if dsm.memory_usage > 85:
            self.dsm_mem_label.config(foreground="red")
        elif dsm.memory_usage > 70:
            self.dsm_mem_label.config(foreground="orange")
        else:
            self.dsm_mem_label.config(foreground="green")

        # 温度
        if dsm.temperature > 0:
            self.dsm_temp_label.config(text=f"{dsm.temperature:.1f}°C")
            if dsm.temperature > 70:
                self.dsm_temp_label.config(foreground="red")
            elif dsm.temperature > 60:
                self.dsm_temp_label.config(foreground="orange")
            else:
                self.dsm_temp_label.config(foreground="green")
        else:
            self.dsm_temp_label.config(text="--°C")

        # 账号
        self.account_tree.delete(*self.account_tree.get_children())
        for account in self.report.accounts:
            admin_str = "✅" if account.is_admin else ""
            groups_str = ", ".join(account.groups[:3]) if account.groups else ""
            self.account_tree.insert(
                "",
                tk.END,
                values=(account.username, account.uid, groups_str, admin_str),
            )

        # 共享
        self.share_tree.delete(*self.share_tree.get_children())
        for share in self.report.shares:
            usage_str = (
                f"{share.usage_percent:.1f}%" if share.usage_percent > 0 else "--"
            )
            self.share_tree.insert(
                "",
                tk.END,
                values=(
                    share.name,
                    share.path,
                    f"{share.size_gb:.1f} GB",
                    f"{share.used_gb:.1f} GB",
                    usage_str,
                ),
            )

        # UPS
        ups = self.report.ups
        if ups.status == UPSStatus.ONLINE:
            self.ups_status_label.config(text="状态: ✅ 市电正常", foreground="green")
        elif ups.status == UPSStatus.ON_BATTERY:
            self.ups_status_label.config(text="状态: ⚠️ 使用电池", foreground="orange")
        elif ups.status == UPSStatus.LOW_BATTERY:
            self.ups_status_label.config(text="状态: ❌ 低电量", foreground="red")
        else:
            self.ups_status_label.config(text="状态: 未检测到", foreground="gray")

        self.ups_model_label.config(text=f"型号: {ups.model or '未知'}")
        self.ups_charge_label.config(text=f"电量: {ups.battery_charge}%")
        self.ups_runtime_label.config(text=f"续航: {ups.battery_runtime // 60} 分钟")
        self.ups_load_label.config(text=f"负载: {ups.load_percent}%")
        self.ups_input_label.config(text=f"输入电压: {ups.input_voltage} V")
        self.ups_output_label.config(text=f"输出电压: {ups.output_voltage} V")

        # Cron
        self.cron_tree.delete(*self.cron_tree.get_children())
        for job in self.report.cron_jobs:
            self.cron_tree.insert(
                "", tk.END, values=(job.schedule, job.user, job.command[:80])
            )

        # 日志
        self.log_tree.delete(*self.log_tree.get_children())
        error_count = 0
        warning_count = 0
        info_count = 0

        for log in self.report.recent_logs:
            self.log_tree.insert(
                "",
                tk.END,
                values=(
                    log.timestamp,
                    log.level.upper(),
                    log.source,
                    log.message[:100],
                ),
            )

            if log.level == "error":
                error_count += 1
            elif log.level == "warning":
                warning_count += 1
            else:
                info_count += 1

        self.log_error_label.config(text=f"错误: {error_count}")
        self.log_warning_label.config(text=f"警告: {warning_count}")
        self.log_info_label.config(text=f"信息: {info_count}")

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

    def _export(self):
        """导出报告"""
        if not self.report:
            messagebox.showwarning("警告", "请先执行检测")
            return

        from tkinter import filedialog

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("JSON 文件", "*.json")],
            initialfile=f"nas_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
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


def show_nas_health_dialog(parent=None, ssh_client=None):
    """显示 NAS 健康检测对话框"""
    dialog = NASHealthDialog(parent, ssh_client)
    if not parent:
        dialog.parent.mainloop()
    return dialog


if __name__ == "__main__":
    show_nas_health_dialog()
