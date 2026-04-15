# -*- coding: utf-8 -*-
"""
gui/system_health_dialog.py — 系统健康检测对话框
CPU 温度 / 启动时间 / 趋势 / Docker
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, List

from core.system_health import (
    check_system_health,
    get_trend,
    format_report,
    SystemHealthReport,
    ServiceStatus,
)


class SystemHealthDialog:
    """系统健康检测对话框"""

    def __init__(self, parent: Optional[tk.Tk] = None, ssh_client=None):
        self.parent = parent or tk.Tk()
        self.ssh_client = ssh_client
        self.report: Optional[SystemHealthReport] = None

        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        """构建 UI"""
        self.parent.title("系统健康检测")
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

        ttk.Button(btn_frame, text="📊 趋势", command=self._show_trend).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="💾 导出", command=self._export).pack(
            side=tk.LEFT, padx=5
        )

        # ────────────────────────────────────────────────────────────
        # 中部：Notebook（CPU / 内存 / 磁盘 / Docker / 服务 / 问题）
        # ────────────────────────────────────────────────────────────
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # CPU 页
        cpu_frame = ttk.Frame(notebook, padding="10")
        notebook.add(cpu_frame, text="🖥️ CPU")
        self._setup_cpu_tab(cpu_frame)

        # 内存页
        mem_frame = ttk.Frame(notebook, padding="10")
        notebook.add(mem_frame, text="💾 内存")
        self._setup_memory_tab(mem_frame)

        # 磁盘页
        disk_frame = ttk.Frame(notebook, padding="10")
        notebook.add(disk_frame, text="💿 磁盘")
        self._setup_disk_tab(disk_frame)

        # Docker 页
        docker_frame = ttk.Frame(notebook, padding="10")
        notebook.add(docker_frame, text="🐳 Docker")
        self._setup_docker_tab(docker_frame)

        # 服务页
        service_frame = ttk.Frame(notebook, padding="10")
        notebook.add(service_frame, text="⚙️ 服务")
        self._setup_service_tab(service_frame)

        # 问题页
        issues_frame = ttk.Frame(notebook, padding="10")
        notebook.add(issues_frame, text="⚠️ 问题")
        self._setup_issues_tab(issues_frame)

        # ────────────────────────────────────────────────────────────
        # 底部：状态栏
        # ────────────────────────────────────────────────────────────
        self.time_label = ttk.Label(main_frame, text="", font=("Arial", 9))
        self.time_label.pack(fill=tk.X, pady=(10, 0))

    def _setup_cpu_tab(self, parent: ttk.Frame):
        """CPU 信息页"""
        # 基本信息
        info_frame = ttk.LabelFrame(parent, text="CPU 信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.cpu_model_label = ttk.Label(info_frame, text="型号: --")
        self.cpu_model_label.pack(anchor=tk.W)

        self.cpu_cores_label = ttk.Label(info_frame, text="核心: --")
        self.cpu_cores_label.pack(anchor=tk.W)

        self.cpu_freq_label = ttk.Label(info_frame, text="频率: --")
        self.cpu_freq_label.pack(anchor=tk.W)

        # 温度和使用率
        usage_frame = ttk.LabelFrame(parent, text="温度与使用率", padding="10")
        usage_frame.pack(fill=tk.X, pady=(0, 10))

        # 温度
        temp_frame = ttk.Frame(usage_frame)
        temp_frame.pack(fill=tk.X, pady=5)

        ttk.Label(temp_frame, text="温度:").pack(side=tk.LEFT)
        self.cpu_temp_label = ttk.Label(
            temp_frame, text="--°C", font=("Arial", 14, "bold")
        )
        self.cpu_temp_label.pack(side=tk.LEFT, padx=10)

        self.cpu_temp_bar = ttk.Progressbar(
            temp_frame, length=200, mode="determinate", maximum=100
        )
        self.cpu_temp_bar.pack(side=tk.LEFT, padx=10)

        # 使用率
        usage_inner = ttk.Frame(usage_frame)
        usage_inner.pack(fill=tk.X, pady=5)

        ttk.Label(usage_inner, text="使用率:").pack(side=tk.LEFT)
        self.cpu_usage_label = ttk.Label(
            usage_inner, text="--%", font=("Arial", 14, "bold")
        )
        self.cpu_usage_label.pack(side=tk.LEFT, padx=10)

        self.cpu_usage_bar = ttk.Progressbar(
            usage_inner, length=200, mode="determinate", maximum=100
        )
        self.cpu_usage_bar.pack(side=tk.LEFT, padx=10)

        # 负载
        load_frame = ttk.LabelFrame(parent, text="系统负载", padding="10")
        load_frame.pack(fill=tk.X)

        self.load_1_label = ttk.Label(load_frame, text="1 分钟: --")
        self.load_1_label.pack(side=tk.LEFT, padx=20)

        self.load_5_label = ttk.Label(load_frame, text="5 分钟: --")
        self.load_5_label.pack(side=tk.LEFT, padx=20)

        self.load_15_label = ttk.Label(load_frame, text="15 分钟: --")
        self.load_15_label.pack(side=tk.LEFT, padx=20)

    def _setup_memory_tab(self, parent: ttk.Frame):
        """内存信息页"""
        # 使用率
        usage_frame = ttk.LabelFrame(parent, text="内存使用率", padding="10")
        usage_frame.pack(fill=tk.X, pady=(0, 10))

        mem_inner = ttk.Frame(usage_frame)
        mem_inner.pack(fill=tk.X, pady=5)

        ttk.Label(mem_inner, text="使用率:").pack(side=tk.LEFT)
        self.mem_usage_label = ttk.Label(
            mem_inner, text="--%", font=("Arial", 14, "bold")
        )
        self.mem_usage_label.pack(side=tk.LEFT, padx=10)

        self.mem_usage_bar = ttk.Progressbar(
            mem_inner, length=300, mode="determinate", maximum=100
        )
        self.mem_usage_bar.pack(side=tk.LEFT, padx=10)

        # 详细信息
        detail_frame = ttk.LabelFrame(parent, text="详细信息", padding="10")
        detail_frame.pack(fill=tk.X)

        self.mem_total_label = ttk.Label(detail_frame, text="总量: -- MB")
        self.mem_total_label.pack(anchor=tk.W)

        self.mem_used_label = ttk.Label(detail_frame, text="已用: -- MB")
        self.mem_used_label.pack(anchor=tk.W)

        self.mem_free_label = ttk.Label(detail_frame, text="可用: -- MB")
        self.mem_free_label.pack(anchor=tk.W)

        self.mem_cached_label = ttk.Label(detail_frame, text="缓存: -- MB")
        self.mem_cached_label.pack(anchor=tk.W)

        # Swap
        swap_frame = ttk.LabelFrame(parent, text="Swap", padding="10")
        swap_frame.pack(fill=tk.X, pady=(10, 0))

        self.swap_total_label = ttk.Label(swap_frame, text="总量: -- MB")
        self.swap_total_label.pack(anchor=tk.W)

        self.swap_used_label = ttk.Label(swap_frame, text="已用: -- MB")
        self.swap_used_label.pack(anchor=tk.W)

    def _setup_disk_tab(self, parent: ttk.Frame):
        """磁盘信息页"""
        columns = ("device", "mount", "total", "used", "free", "usage")
        self.disk_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=12
        )

        self.disk_tree.heading("device", text="设备")
        self.disk_tree.heading("mount", text="挂载点")
        self.disk_tree.heading("total", text="总量")
        self.disk_tree.heading("used", text="已用")
        self.disk_tree.heading("free", text="可用")
        self.disk_tree.heading("usage", text="使用率")

        self.disk_tree.column("device", width=100)
        self.disk_tree.column("mount", width=150)
        self.disk_tree.column("total", width=80)
        self.disk_tree.column("used", width=80)
        self.disk_tree.column("free", width=80)
        self.disk_tree.column("usage", width=80)

        self.disk_tree.pack(fill=tk.BOTH, expand=True)

    def _setup_docker_tab(self, parent: ttk.Frame):
        """Docker 信息页"""
        # 基本信息
        info_frame = ttk.LabelFrame(parent, text="Docker 信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.docker_version_label = ttk.Label(info_frame, text="版本: --")
        self.docker_version_label.pack(anchor=tk.W)

        self.docker_status_label = ttk.Label(info_frame, text="状态: --")
        self.docker_status_label.pack(anchor=tk.W)

        # 容器信息
        container_frame = ttk.LabelFrame(parent, text="容器", padding="10")
        container_frame.pack(fill=tk.X, pady=(0, 10))

        self.docker_containers_label = ttk.Label(container_frame, text="总数: --")
        self.docker_containers_label.pack(anchor=tk.W)

        self.docker_running_label = ttk.Label(container_frame, text="运行: --")
        self.docker_running_label.pack(anchor=tk.W)

        self.docker_stopped_label = ttk.Label(container_frame, text="停止: --")
        self.docker_stopped_label.pack(anchor=tk.W)

        # 镜像
        image_frame = ttk.LabelFrame(parent, text="镜像", padding="10")
        image_frame.pack(fill=tk.X)

        self.docker_images_label = ttk.Label(image_frame, text="数量: --")
        self.docker_images_label.pack(anchor=tk.W)

        self.docker_disk_label = ttk.Label(image_frame, text="磁盘占用: --")
        self.docker_disk_label.pack(anchor=tk.W)

    def _setup_service_tab(self, parent: ttk.Frame):
        """服务信息页"""
        # 输入框
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="服务名称（逗号分隔）:").pack(side=tk.LEFT)
        self.service_entry = ttk.Entry(input_frame, width=50)
        self.service_entry.insert(0, "docker,nginx,sshd,systemd-timesyncd")
        self.service_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(input_frame, text="检查", command=self._check_services).pack(
            side=tk.LEFT, padx=5
        )

        # 结果表格
        columns = ("name", "status", "enabled", "pid")
        self.service_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=12
        )

        self.service_tree.heading("name", text="服务")
        self.service_tree.heading("status", text="状态")
        self.service_tree.heading("enabled", text="开机启动")
        self.service_tree.heading("pid", text="PID")

        self.service_tree.column("name", width=150)
        self.service_tree.column("status", width=100)
        self.service_tree.column("enabled", width=100)
        self.service_tree.column("pid", width=80)

        self.service_tree.pack(fill=tk.BOTH, expand=True)

    def _setup_issues_tab(self, parent: ttk.Frame):
        """问题页"""
        # 系统信息
        sys_frame = ttk.LabelFrame(parent, text="系统信息", padding="10")
        sys_frame.pack(fill=tk.X, pady=(0, 10))

        self.hostname_label = ttk.Label(sys_frame, text="主机名: --")
        self.hostname_label.pack(anchor=tk.W)

        self.uptime_label = ttk.Label(sys_frame, text="运行时间: --")
        self.uptime_label.pack(anchor=tk.W)

        # 严重问题
        critical_frame = ttk.LabelFrame(parent, text="❌ 严重问题", padding="10")
        critical_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.issues_text = tk.Text(critical_frame, height=6, wrap=tk.WORD)
        self.issues_text.pack(fill=tk.BOTH, expand=True)

        # 警告
        warning_frame = ttk.LabelFrame(parent, text="⚠️ 警告", padding="10")
        warning_frame.pack(fill=tk.BOTH, expand=True)

        self.warnings_text = tk.Text(warning_frame, height=6, wrap=tk.WORD)
        self.warnings_text.pack(fill=tk.BOTH, expand=True)

    def _refresh(self):
        """刷新数据"""
        self.status_label.config(text="检测中...")

        try:
            # 执行检测
            if self.ssh_client:
                self.report = self._remote_check()
            else:
                self.report = check_system_health(check_docker=True)

            # 更新 UI
            self._update_ui()

        except Exception as e:
            messagebox.showerror("错误", f"检测失败: {e}")
            self.status_label.config(text="检测失败")

    def _remote_check(self) -> SystemHealthReport:
        """远程检测"""
        return check_system_health()

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

        # CPU
        cpu = self.report.cpu
        self.cpu_model_label.config(text=f"型号: {cpu.model or '未知'}")
        self.cpu_cores_label.config(text=f"核心: {cpu.cores}")
        self.cpu_freq_label.config(
            text=f"频率: {cpu.frequency_mhz:.0f} MHz"
            if cpu.frequency_mhz > 0
            else "频率: --"
        )

        # 温度
        if cpu.temperature_c > 0:
            self.cpu_temp_label.config(text=f"{cpu.temperature_c:.1f}°C")
            self.cpu_temp_bar["value"] = min(cpu.temperature_c, 100)
            if cpu.temperature_c > 70:
                self.cpu_temp_label.config(foreground="red")
            elif cpu.temperature_c > 60:
                self.cpu_temp_label.config(foreground="orange")
            else:
                self.cpu_temp_label.config(foreground="green")
        else:
            self.cpu_temp_label.config(text="--°C")

        # 使用率
        self.cpu_usage_label.config(text=f"{cpu.usage_percent:.1f}%")
        self.cpu_usage_bar["value"] = cpu.usage_percent
        if cpu.usage_percent > 80:
            self.cpu_usage_label.config(foreground="red")
        elif cpu.usage_percent > 60:
            self.cpu_usage_label.config(foreground="orange")
        else:
            self.cpu_usage_label.config(foreground="green")

        # 负载
        self.load_1_label.config(text=f"1 分钟: {cpu.load_avg_1:.2f}")
        self.load_5_label.config(text=f"5 分钟: {cpu.load_avg_5:.2f}")
        self.load_15_label.config(text=f"15 分钟: {cpu.load_avg_15:.2f}")

        # 内存
        mem = self.report.memory
        self.mem_usage_label.config(text=f"{mem.usage_percent:.1f}%")
        self.mem_usage_bar["value"] = mem.usage_percent
        if mem.usage_percent > 85:
            self.mem_usage_label.config(foreground="red")
        elif mem.usage_percent > 70:
            self.mem_usage_label.config(foreground="orange")
        else:
            self.mem_usage_label.config(foreground="green")

        self.mem_total_label.config(text=f"总量: {mem.total_mb:,} MB")
        self.mem_used_label.config(text=f"已用: {mem.used_mb:,} MB")
        self.mem_free_label.config(text=f"可用: {mem.available_mb:,} MB")
        self.mem_cached_label.config(text=f"缓存: {mem.cached_mb:,} MB")

        self.swap_total_label.config(text=f"总量: {mem.swap_total_mb:,} MB")
        self.swap_used_label.config(text=f"已用: {mem.swap_used_mb:,} MB")

        # 磁盘
        self.disk_tree.delete(*self.disk_tree.get_children())
        for disk in self.report.disks:
            usage_str = f"{disk.usage_percent:.1f}%"
            self.disk_tree.insert(
                "",
                tk.END,
                values=(
                    disk.device,
                    disk.mount_point,
                    f"{disk.total_gb:.1f} GB",
                    f"{disk.used_gb:.1f} GB",
                    f"{disk.free_gb:.1f} GB",
                    usage_str,
                ),
            )

        # Docker
        docker = self.report.docker
        self.docker_version_label.config(text=f"版本: {docker.version or '未安装'}")

        if docker.installed:
            status_str = "✅ 运行中" if docker.running else "❌ 未运行"
            self.docker_status_label.config(text=f"状态: {status_str}")

            self.docker_containers_label.config(text=f"总数: {docker.containers_total}")
            self.docker_running_label.config(text=f"运行: {docker.containers_running}")
            self.docker_stopped_label.config(text=f"停止: {docker.containers_stopped}")
            self.docker_images_label.config(text=f"数量: {docker.images_total}")
            self.docker_disk_label.config(
                text=f"磁盘占用: {docker.disk_usage_gb:.1f} GB"
            )
        else:
            self.docker_status_label.config(text="状态: 未安装")
            self.docker_containers_label.config(text="总数: --")
            self.docker_running_label.config(text="运行: --")
            self.docker_stopped_label.config(text="停止: --")
            self.docker_images_label.config(text="数量: --")
            self.docker_disk_label.config(text="磁盘占用: --")

        # 服务
        self.service_tree.delete(*self.service_tree.get_children())
        for service in self.report.services:
            status_str = (
                "✅ 运行"
                if service.status == ServiceStatus.RUNNING
                else "❌ 失败"
                if service.status == ServiceStatus.FAILED
                else "⏸️ 停止"
                if service.status == ServiceStatus.STOPPED
                else "未知"
            )
            enabled_str = "✅ 是" if service.enabled else "否"
            pid_str = str(service.pid) if service.pid > 0 else "--"

            self.service_tree.insert(
                "", tk.END, values=(service.name, status_str, enabled_str, pid_str)
            )

        # 系统信息
        self.hostname_label.config(text=f"主机名: {self.report.hostname}")
        self.uptime_label.config(text=f"运行时间: {self.report.uptime_human}")

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

    def _check_services(self):
        """检查服务"""
        services_str = self.service_entry.get().strip()
        services = [s.strip() for s in services_str.split(",") if s.strip()]

        if not services:
            return

        try:
            from core.system_health import get_services_info

            self.report.services = get_services_info(services)
            self._update_ui()
        except Exception as e:
            messagebox.showerror("错误", f"检查失败: {e}")

    def _show_trend(self):
        """显示趋势"""
        trend = get_trend(days=7)
        if not trend or trend.get("records", 0) == 0:
            messagebox.showinfo("趋势", "暂无历史数据")
            return

        # 创建趋势窗口
        trend_win = tk.Toplevel(self.parent)
        trend_win.title("系统健康趋势（7天）")
        trend_win.geometry("700x500")

        # 健康分数趋势
        score_frame = ttk.LabelFrame(trend_win, text="健康分数趋势", padding="10")
        score_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scores = trend.get("health_scores", [])
        if scores:
            avg = trend.get("avg_health", 0)
            ttk.Label(
                score_frame,
                text=f"平均: {avg:.1f}, 最低: {min(scores)}, 最高: {max(scores)}",
                font=("Arial", 12),
            ).pack()

            # 简单文本图表
            chart_lines = []
            for i, s in enumerate(scores[-30:]):  # 最近 30 条
                bar_len = int(s / 2)
                bar = "█" * bar_len
                chart_lines.append(f"{i + 1:2d}: {bar} {s}")
            ttk.Label(
                score_frame, text="\n".join(chart_lines), font=("Courier", 8)
            ).pack()

        # CPU 温度趋势
        temp_frame = ttk.LabelFrame(trend_win, text="CPU 温度趋势", padding="10")
        temp_frame.pack(fill=tk.X, padx=10, pady=10)

        temps = trend.get("cpu_temps", [])
        if temps:
            avg_temp = trend.get("avg_cpu_temp", 0)
            ttk.Label(
                temp_frame, text=f"平均: {avg_temp:.1f}°C, 最高: {max(temps):.1f}°C"
            ).pack()

        # CPU 使用率趋势
        usage_frame = ttk.LabelFrame(trend_win, text="CPU 使用率趋势", padding="10")
        usage_frame.pack(fill=tk.X, padx=10, pady=10)

        usages = trend.get("cpu_usages", [])
        if usages:
            avg_usage = trend.get("avg_cpu_usage", 0)
            ttk.Label(
                usage_frame, text=f"平均: {avg_usage:.1f}%, 最高: {max(usages):.1f}%"
            ).pack()

        # 记录数
        ttk.Label(trend_win, text=f"共 {trend.get('records', 0)} 条记录").pack(pady=10)

    def _export(self):
        """导出报告"""
        if not self.report:
            messagebox.showwarning("警告", "请先执行检测")
            return

        from tkinter import filedialog

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("JSON 文件", "*.json")],
            initialfile=f"system_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
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


def show_system_health_dialog(parent=None, ssh_client=None):
    """显示系统健康检测对话框"""
    dialog = SystemHealthDialog(parent, ssh_client)
    if not parent:
        dialog.parent.mainloop()
    return dialog


if __name__ == "__main__":
    show_system_health_dialog()
