# -*- coding: utf-8 -*-
"""
gui/network_health_dialog.py — 网络健康检测对话框
带宽 / 端口 / DNS / 网卡速率
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, List

from core.network_health import (
    check_network_health,
    scan_ports,
    test_dns_coverage,
    test_bandwidth_speedtest,
    format_report,
    NetworkHealthReport,
    PortStatus,
    LinkState,
)


class NetworkHealthDialog:
    """网络健康检测对话框"""

    def __init__(self, parent: Optional[tk.Tk] = None, ssh_client=None):
        self.parent = parent or tk.Tk()
        self.ssh_client = ssh_client
        self.report: Optional[NetworkHealthReport] = None

        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        """构建 UI"""
        self.parent.title("网络健康检测")
        self.parent.geometry("950x700")

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

        ttk.Button(btn_frame, text="📊 带宽测试", command=self._test_bandwidth).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="🚪 端口扫描", command=self._scan_ports).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="🔍 DNS 测试", command=self._test_dns).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="💾 导出", command=self._export).pack(
            side=tk.LEFT, padx=5
        )

        # ────────────────────────────────────────────────────────────
        # 中部：Notebook（网卡 / 带宽 / 端口 / DNS / 问题）
        # ────────────────────────────────────────────────────────────
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 网卡页
        iface_frame = ttk.Frame(notebook, padding="10")
        notebook.add(iface_frame, text="🌐 网卡")
        self._setup_iface_tab(iface_frame)

        # 带宽页
        bw_frame = ttk.Frame(notebook, padding="10")
        notebook.add(bw_frame, text="📊 带宽")
        self._setup_bandwidth_tab(bw_frame)

        # 端口页
        port_frame = ttk.Frame(notebook, padding="10")
        notebook.add(port_frame, text="🚪 端口")
        self._setup_port_tab(port_frame)

        # DNS 页
        dns_frame = ttk.Frame(notebook, padding="10")
        notebook.add(dns_frame, text="🔍 DNS")
        self._setup_dns_tab(dns_frame)

        # 问题页
        issues_frame = ttk.Frame(notebook, padding="10")
        notebook.add(issues_frame, text="⚠️ 问题")
        self._setup_issues_tab(issues_frame)

        # ────────────────────────────────────────────────────────────
        # 底部：状态栏
        # ────────────────────────────────────────────────────────────
        self.time_label = ttk.Label(main_frame, text="", font=("Arial", 9))
        self.time_label.pack(fill=tk.X, pady=(10, 0))

    def _setup_iface_tab(self, parent: ttk.Frame):
        """网卡信息页"""
        columns = ("name", "ip", "mac", "speed", "state", "rx_errors", "tx_errors")
        self.iface_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=12
        )

        self.iface_tree.heading("name", text="网卡")
        self.iface_tree.heading("ip", text="IP 地址")
        self.iface_tree.heading("mac", text="MAC 地址")
        self.iface_tree.heading("speed", text="速率")
        self.iface_tree.heading("state", text="状态")
        self.iface_tree.heading("rx_errors", text="RX 错误")
        self.iface_tree.heading("tx_errors", text="TX 错误")

        self.iface_tree.column("name", width=80)
        self.iface_tree.column("ip", width=120)
        self.iface_tree.column("mac", width=130)
        self.iface_tree.column("speed", width=80)
        self.iface_tree.column("state", width=60)
        self.iface_tree.column("rx_errors", width=80)
        self.iface_tree.column("tx_errors", width=80)

        self.iface_tree.pack(fill=tk.BOTH, expand=True)

        # 连通性信息
        conn_frame = ttk.LabelFrame(parent, text="连通性", padding="10")
        conn_frame.pack(fill=tk.X, pady=(10, 0))

        self.gateway_label = ttk.Label(conn_frame, text="网关: --")
        self.gateway_label.pack(side=tk.LEFT, padx=20)

        self.internet_label = ttk.Label(conn_frame, text="互联网: --")
        self.internet_label.pack(side=tk.LEFT, padx=20)

    def _setup_bandwidth_tab(self, parent: ttk.Frame):
        """带宽信息页"""
        # 测试结果
        result_frame = ttk.LabelFrame(parent, text="带宽测试结果", padding="20")
        result_frame.pack(fill=tk.X, pady=(0, 10))

        self.download_label = ttk.Label(
            result_frame, text="下载: -- Mbps", font=("Arial", 14)
        )
        self.download_label.pack(anchor=tk.W)

        self.upload_label = ttk.Label(
            result_frame, text="上传: -- Mbps", font=("Arial", 14)
        )
        self.upload_label.pack(anchor=tk.W)

        self.latency_label = ttk.Label(
            result_frame, text="延迟: -- ms", font=("Arial", 14)
        )
        self.latency_label.pack(anchor=tk.W)

        self.packet_loss_label = ttk.Label(
            result_frame, text="丢包: --%", font=("Arial", 14)
        )
        self.packet_loss_label.pack(anchor=tk.W)

        # 进度
        self.bw_progress = ttk.Progressbar(parent, mode="indeterminate")
        self.bw_progress.pack(fill=tk.X, pady=10)

        self.bw_status = ttk.Label(parent, text="")
        self.bw_status.pack()

    def _setup_port_tab(self, parent: ttk.Frame):
        """端口扫描页"""
        # 输入框
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="目标主机:").pack(side=tk.LEFT)
        self.port_host_entry = ttk.Entry(input_frame, width=20)
        self.port_host_entry.insert(0, "localhost")
        self.port_host_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(input_frame, text="端口 (逗号分隔):").pack(side=tk.LEFT, padx=(20, 0))
        self.port_entry = ttk.Entry(input_frame, width=40)
        self.port_entry.insert(0, "22,80,443,3000,8000,8080")
        self.port_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(input_frame, text="扫描", command=self._scan_ports).pack(
            side=tk.LEFT, padx=5
        )

        # 结果表格
        columns = ("port", "status", "service", "banner")
        self.port_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=15
        )

        self.port_tree.heading("port", text="端口")
        self.port_tree.heading("status", text="状态")
        self.port_tree.heading("service", text="服务")
        self.port_tree.heading("banner", text="Banner")

        self.port_tree.column("port", width=80)
        self.port_tree.column("status", width=80)
        self.port_tree.column("service", width=100)
        self.port_tree.column("banner", width=300)

        self.port_tree.pack(fill=tk.BOTH, expand=True)

    def _setup_dns_tab(self, parent: ttk.Frame):
        """DNS 测试页"""
        # 输入框
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="域名:").pack(side=tk.LEFT)
        self.dns_domain_entry = ttk.Entry(input_frame, width=30)
        self.dns_domain_entry.insert(0, "www.baidu.com")
        self.dns_domain_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(input_frame, text="测试", command=self._test_dns).pack(
            side=tk.LEFT, padx=5
        )

        # 结果表格
        columns = ("server", "ip", "rtt", "status")
        self.dns_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=15
        )

        self.dns_tree.heading("server", text="DNS 服务器")
        self.dns_tree.heading("ip", text="解析 IP")
        self.dns_tree.heading("rtt", text="延迟")
        self.dns_tree.heading("status", text="状态")

        self.dns_tree.column("server", width=150)
        self.dns_tree.column("ip", width=150)
        self.dns_tree.column("rtt", width=80)
        self.dns_tree.column("status", width=80)

        self.dns_tree.pack(fill=tk.BOTH, expand=True)

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
                self.report = check_network_health(do_bandwidth=False, test_dns=True)

            # 更新 UI
            self._update_ui()

        except Exception as e:
            messagebox.showerror("错误", f"检测失败: {e}")
            self.status_label.config(text="检测失败")

    def _remote_check(self) -> NetworkHealthReport:
        """远程检测"""
        return check_network_health()

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

        # 网卡表格
        self.iface_tree.delete(*self.iface_tree.get_children())
        for iface in self.report.interfaces:
            status_str = "UP" if iface.link_state == LinkState.UP else "DOWN"
            speed_str = f"{iface.speed_mbps} Mbps" if iface.speed_mbps > 0 else "--"

            self.iface_tree.insert(
                "",
                tk.END,
                values=(
                    iface.name,
                    iface.ip or "--",
                    iface.mac or "--",
                    speed_str,
                    status_str,
                    str(iface.rx_errors),
                    str(iface.tx_errors),
                ),
            )

        # 连通性
        gw_icon = "✅" if self.report.gateway_reachable else "❌"
        self.gateway_label.config(
            text=f"网关: {gw_icon} {self.report.gateway or '未知'}"
        )
        net_icon = "✅" if self.report.internet_reachable else "❌"
        self.internet_label.config(text=f"互联网: {net_icon}")

        # 带宽
        bw = self.report.bandwidth
        self.download_label.config(
            text=f"下载: {bw.download_mbps:.1f} Mbps"
            if bw.download_mbps > 0
            else "下载: -- Mbps"
        )
        self.upload_label.config(
            text=f"上传: {bw.upload_mbps:.1f} Mbps"
            if bw.upload_mbps > 0
            else "上传: -- Mbps"
        )
        self.latency_label.config(
            text=f"延迟: {bw.latency_ms:.1f} ms" if bw.latency_ms > 0 else "延迟: -- ms"
        )
        self.packet_loss_label.config(
            text=f"丢包: {bw.packet_loss:.1f}%" if bw.packet_loss > 0 else "丢包: --%"
        )

        # 端口
        self.port_tree.delete(*self.port_tree.get_children())
        for p in self.report.port_scan:
            status_str = (
                "✅ 开放"
                if p.status == PortStatus.OPEN
                else "❌ 关闭"
                if p.status == PortStatus.CLOSED
                else "⚠️ 过滤"
                if p.status == PortStatus.FILTERED
                else "未知"
            )

            self.port_tree.insert(
                "",
                tk.END,
                values=(
                    str(p.port),
                    status_str,
                    p.service,
                    p.banner[:50] if p.banner else "",
                ),
            )

        # DNS
        self.dns_tree.delete(*self.dns_tree.get_children())
        for d in self.report.dns_results:
            status_str = "✅" if d.success else "❌"

            self.dns_tree.insert(
                "",
                tk.END,
                values=(
                    d.server,
                    d.ip or "--",
                    f"{d.rtt_ms:.1f} ms" if d.rtt_ms > 0 else "--",
                    status_str,
                ),
            )

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

    def _test_bandwidth(self):
        """测试带宽"""
        self.bw_status.config(text="测试中...")
        self.bw_progress.start()

        def run_test():
            try:
                result = test_bandwidth_speedtest()
                self.report.bandwidth = result
                self.parent.after(0, self._update_bandwidth_ui)
            except Exception as e:
                self.parent.after(
                    0, lambda: self.bw_status.config(text=f"测试失败: {e}")
                )
            finally:
                self.parent.after(0, self.bw_progress.stop)

        threading.Thread(target=run_test, daemon=True).start()

    def _update_bandwidth_ui(self):
        """更新带宽 UI"""
        bw = self.report.bandwidth
        self.download_label.config(text=f"下载: {bw.download_mbps:.1f} Mbps")
        self.upload_label.config(text=f"上传: {bw.upload_mbps:.1f} Mbps")
        self.latency_label.config(text=f"延迟: {bw.latency_ms:.1f} ms")
        self.packet_loss_label.config(text=f"丢包: {bw.packet_loss:.1f}%")
        self.bw_status.config(text="测试完成")

    def _scan_ports(self):
        """扫描端口"""
        host = self.port_host_entry.get().strip()
        ports_str = self.port_entry.get().strip()

        try:
            ports = [int(p.strip()) for p in ports_str.split(",") if p.strip()]
        except:
            messagebox.showerror("错误", "端口格式错误")
            return

        # 清空表格
        self.port_tree.delete(*self.port_tree.get_children())

        def run_scan():
            try:
                results = scan_ports(host, ports)
                self.report.port_scan = results
                self.parent.after(0, self._update_port_ui)
            except Exception as e:
                self.parent.after(
                    0, lambda: messagebox.showerror("错误", f"扫描失败: {e}")
                )

        threading.Thread(target=run_scan, daemon=True).start()

    def _update_port_ui(self):
        """更新端口 UI"""
        self.port_tree.delete(*self.port_tree.get_children())
        for p in self.report.port_scan:
            status_str = (
                "✅ 开放"
                if p.status == PortStatus.OPEN
                else "❌ 关闭"
                if p.status == PortStatus.CLOSED
                else "⚠️ 过滤"
                if p.status == PortStatus.FILTERED
                else "未知"
            )

            self.port_tree.insert(
                "",
                tk.END,
                values=(
                    str(p.port),
                    status_str,
                    p.service,
                    p.banner[:50] if p.banner else "",
                ),
            )

    def _test_dns(self):
        """测试 DNS"""
        domain = self.dns_domain_entry.get().strip()

        def run_test():
            try:
                results = test_dns_coverage(domain)
                self.report.dns_results = results
                self.parent.after(0, self._update_dns_ui)
            except Exception as e:
                self.parent.after(
                    0, lambda: messagebox.showerror("错误", f"测试失败: {e}")
                )

        threading.Thread(target=run_test, daemon=True).start()

    def _update_dns_ui(self):
        """更新 DNS UI"""
        self.dns_tree.delete(*self.dns_tree.get_children())
        for d in self.report.dns_results:
            status_str = "✅" if d.success else "❌"

            self.dns_tree.insert(
                "",
                tk.END,
                values=(
                    d.server,
                    d.ip or "--",
                    f"{d.rtt_ms:.1f} ms" if d.rtt_ms > 0 else "--",
                    status_str,
                ),
            )

    def _export(self):
        """导出报告"""
        if not self.report:
            messagebox.showwarning("警告", "请先执行检测")
            return

        from tkinter import filedialog

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("JSON 文件", "*.json")],
            initialfile=f"network_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
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


def show_network_health_dialog(parent=None, ssh_client=None):
    """显示网络健康检测对话框"""
    dialog = NetworkHealthDialog(parent, ssh_client)
    if not parent:
        dialog.parent.mainloop()
    return dialog


if __name__ == "__main__":
    import threading

    show_network_health_dialog()
