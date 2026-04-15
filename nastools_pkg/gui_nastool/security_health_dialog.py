# -*- coding: utf-8 -*-
"""
gui/security_health_dialog.py — 安全健康检测对话框
登录失败 / 防火墙 / SSL / 自动更新
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, List

from core.security_health import (
    check_security_health,
    format_report,
    SecurityHealthReport,
    FirewallStatus,
    SSLStatus,
)


class SecurityHealthDialog:
    """安全健康检测对话框"""

    def __init__(self, parent: Optional[tk.Tk] = None, ssh_client=None):
        self.parent = parent or tk.Tk()
        self.ssh_client = ssh_client
        self.report: Optional[SecurityHealthReport] = None

        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        """构建 UI"""
        self.parent.title("安全健康检测")
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
        score_frame = ttk.LabelFrame(top_frame, text="安全分数", padding="10")
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

        ttk.Button(btn_frame, text="🚫 封禁 IP", command=self._ban_ips).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="💾 导出", command=self._export).pack(
            side=tk.LEFT, padx=5
        )

        # ────────────────────────────────────────────────────────────
        # 中部：Notebook（登录失败 / 防火墙 / SSL / 更新 / SSH / 问题）
        # ────────────────────────────────────────────────────────────
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 登录失败页
        login_frame = ttk.Frame(notebook, padding="10")
        notebook.add(login_frame, text="🔐 登录失败")
        self._setup_login_tab(login_frame)

        # 防火墙页
        firewall_frame = ttk.Frame(notebook, padding="10")
        notebook.add(firewall_frame, text="🔥 防火墙")
        self._setup_firewall_tab(firewall_frame)

        # SSL 页
        ssl_frame = ttk.Frame(notebook, padding="10")
        notebook.add(ssl_frame, text="🔒 SSL")
        self._setup_ssl_tab(ssl_frame)

        # 更新页
        update_frame = ttk.Frame(notebook, padding="10")
        notebook.add(update_frame, text="📦 更新")
        self._setup_update_tab(update_frame)

        # SSH 页
        ssh_frame = ttk.Frame(notebook, padding="10")
        notebook.add(ssh_frame, text="🔑 SSH")
        self._setup_ssh_tab(ssh_frame)

        # 问题页
        issues_frame = ttk.Frame(notebook, padding="10")
        notebook.add(issues_frame, text="⚠️ 问题")
        self._setup_issues_tab(issues_frame)

        # ────────────────────────────────────────────────────────────
        # 底部：状态栏
        # ────────────────────────────────────────────────────────────
        self.time_label = ttk.Label(main_frame, text="", font=("Arial", 9))
        self.time_label.pack(fill=tk.X, pady=(10, 0))

    def _setup_login_tab(self, parent: ttk.Frame):
        """登录失败页"""
        # 统计信息
        stats_frame = ttk.LabelFrame(parent, text="24小时统计", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.login_count_label = ttk.Label(
            stats_frame, text="失败次数: --", font=("Arial", 12)
        )
        self.login_count_label.pack(anchor=tk.W)

        self.brute_force_label = ttk.Label(
            stats_frame, text="暴力破解 IP: --", font=("Arial", 12)
        )
        self.brute_force_label.pack(anchor=tk.W)

        # 失败记录表格
        table_frame = ttk.LabelFrame(parent, text="失败记录", padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("username", "ip", "timestamp", "service")
        self.login_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=15
        )

        self.login_tree.heading("username", text="用户名")
        self.login_tree.heading("ip", text="IP")
        self.login_tree.heading("timestamp", text="时间")
        self.login_tree.heading("service", text="服务")

        self.login_tree.column("username", width=150)
        self.login_tree.column("ip", width=150)
        self.login_tree.column("timestamp", width=150)
        self.login_tree.column("service", width=100)

        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.login_tree.yview
        )
        self.login_tree.configure(yscrollcommand=scrollbar.set)

        self.login_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _setup_firewall_tab(self, parent: ttk.Frame):
        """防火墙页"""
        # 基本信息
        info_frame = ttk.LabelFrame(parent, text="防火墙信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.fw_backend_label = ttk.Label(info_frame, text="后端: --")
        self.fw_backend_label.pack(anchor=tk.W)

        self.fw_status_label = ttk.Label(info_frame, text="状态: --")
        self.fw_status_label.pack(anchor=tk.W)

        self.fw_rules_label = ttk.Label(info_frame, text="规则数: --")
        self.fw_rules_label.pack(anchor=tk.W)

        # 开放端口
        ports_frame = ttk.LabelFrame(parent, text="开放端口", padding="10")
        ports_frame.pack(fill=tk.X, pady=(0, 10))

        self.fw_ports_label = ttk.Label(ports_frame, text="--")
        self.fw_ports_label.pack(anchor=tk.W)

        # 操作按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="启用防火墙", command=self._enable_firewall).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="禁用防火墙", command=self._disable_firewall).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="开放 NAS 端口", command=self._allow_nas_ports).pack(
            side=tk.LEFT, padx=5
        )

    def _setup_ssl_tab(self, parent: ttk.Frame):
        """SSL 证书页"""
        # 域名输入
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="域名（逗号分隔）:").pack(side=tk.LEFT)
        self.ssl_entry = ttk.Entry(input_frame, width=50)
        self.ssl_entry.insert(0, "example.com,www.example.com")
        self.ssl_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(input_frame, text="检查", command=self._check_ssl).pack(
            side=tk.LEFT, padx=5
        )

        # 证书信息表格
        columns = ("domain", "status", "days", "issuer", "expires")
        self.ssl_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=12
        )

        self.ssl_tree.heading("domain", text="域名")
        self.ssl_tree.heading("status", text="状态")
        self.ssl_tree.heading("days", text="剩余天数")
        self.ssl_tree.heading("issuer", text="颁发者")
        self.ssl_tree.heading("expires", text="过期时间")

        self.ssl_tree.column("domain", width=150)
        self.ssl_tree.column("status", width=100)
        self.ssl_tree.column("days", width=80)
        self.ssl_tree.column("issuer", width=200)
        self.ssl_tree.column("expires", width=150)

        self.ssl_tree.pack(fill=tk.BOTH, expand=True)

    def _setup_update_tab(self, parent: ttk.Frame):
        """系统更新页"""
        # 更新统计
        stats_frame = ttk.LabelFrame(parent, text="可用更新", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.update_security_label = ttk.Label(
            stats_frame, text="安全更新: --", font=("Arial", 12)
        )
        self.update_security_label.pack(anchor=tk.W)

        self.update_regular_label = ttk.Label(
            stats_frame, text="常规更新: --", font=("Arial", 12)
        )
        self.update_regular_label.pack(anchor=tk.W)

        self.update_kernel_label = ttk.Label(stats_frame, text="内核更新: --")
        self.update_kernel_label.pack(anchor=tk.W)

        # 自动更新
        auto_frame = ttk.LabelFrame(parent, text="自动更新", padding="10")
        auto_frame.pack(fill=tk.X, pady=(0, 10))

        self.auto_update_label = ttk.Label(auto_frame, text="状态: --")
        self.auto_update_label.pack(anchor=tk.W)

        self.last_update_label = ttk.Label(auto_frame, text="上次更新: --")
        self.last_update_label.pack(anchor=tk.W)

        self.reboot_label = ttk.Label(auto_frame, text="重启: --")
        self.reboot_label.pack(anchor=tk.W)

        # 操作按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame, text="安装安全更新", command=self._install_security_updates
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame, text="安装所有更新", command=self._install_all_updates
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame, text="启用自动更新", command=self._enable_auto_update
        ).pack(side=tk.LEFT, padx=5)

    def _setup_ssh_tab(self, parent: ttk.Frame):
        """SSH 配置页"""
        # 基本信息
        info_frame = ttk.LabelFrame(parent, text="SSH 配置", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.ssh_port_label = ttk.Label(info_frame, text="端口: --")
        self.ssh_port_label.pack(anchor=tk.W)

        self.ssh_root_label = ttk.Label(info_frame, text="Root 登录: --")
        self.ssh_root_label.pack(anchor=tk.W)

        self.ssh_password_label = ttk.Label(info_frame, text="密码认证: --")
        self.ssh_password_label.pack(anchor=tk.W)

        self.ssh_pubkey_label = ttk.Label(info_frame, text="密钥认证: --")
        self.ssh_pubkey_label.pack(anchor=tk.W)

        self.ssh_max_tries_label = ttk.Label(info_frame, text="最大尝试: --")
        self.ssh_max_tries_label.pack(anchor=tk.W)

        # 安全建议
        issues_frame = ttk.LabelFrame(parent, text="安全建议", padding="10")
        issues_frame.pack(fill=tk.BOTH, expand=True)

        self.ssh_issues_text = tk.Text(issues_frame, height=10, wrap=tk.WORD)
        self.ssh_issues_text.pack(fill=tk.BOTH, expand=True)

        # 操作按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="加固 SSH", command=self._harden_ssh).pack(
            side=tk.LEFT, padx=5
        )

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
                self.report = check_security_health(
                    check_login_failures=True,
                    check_firewall=True,
                    check_ssl=False,
                    check_updates=True,
                    check_ssh=True,
                )

            # 更新 UI
            self._update_ui()

        except Exception as e:
            messagebox.showerror("错误", f"检测失败: {e}")
            self.status_label.config(text="检测失败")

    def _remote_check(self) -> SecurityHealthReport:
        """远程检测"""
        return check_security_health()

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
            self.status_label.config(text="✅ 安全", foreground="green")
        else:
            self.status_label.config(text="❌ 存在风险", foreground="red")

        # 时间
        self.time_label.config(text=f"检测时间: {self.report.timestamp}")

        # 登录失败
        self.login_count_label.config(
            text=f"失败次数: {self.report.login_failure_count_24h}"
        )
        if self.report.brute_force_ips:
            self.brute_force_label.config(
                text=f"暴力破解 IP: {len(self.report.brute_force_ips)} 个"
            )
        else:
            self.brute_force_label.config(text="暴力破解 IP: 无")

        self.login_tree.delete(*self.login_tree.get_children())
        for f in self.report.login_failures[:50]:
            self.login_tree.insert(
                "", tk.END, values=(f.username, f.ip, f.timestamp, f.service)
            )

        # 防火墙
        fw = self.report.firewall
        self.fw_backend_label.config(text=f"后端: {fw.backend or '未检测到'}")

        if fw.status == FirewallStatus.ACTIVE:
            self.fw_status_label.config(text="状态: ✅ 已启用", foreground="green")
        elif fw.status == FirewallStatus.INACTIVE:
            self.fw_status_label.config(text="状态: ❌ 未启用", foreground="red")
        else:
            self.fw_status_label.config(text="状态: ⚠️ 未安装", foreground="orange")

        self.fw_rules_label.config(text=f"规则数: {fw.rules_count}")

        if fw.open_ports:
            self.fw_ports_label.config(
                text=f"开放端口: {', '.join(map(str, fw.open_ports))}"
            )
        else:
            self.fw_ports_label.config(text="开放端口: 无")

        # SSL
        self.ssl_tree.delete(*self.ssl_tree.get_children())
        for cert in self.report.ssl_certificates:
            status_str = (
                "✅ 有效"
                if cert.status == SSLStatus.VALID
                else "❌ 已过期"
                if cert.status == SSLStatus.EXPIRED
                else "⚠️ 即将过期"
                if cert.status == SSLStatus.EXPIRING_SOON
                else "无效"
            )
            self.ssl_tree.insert(
                "",
                tk.END,
                values=(
                    cert.domain,
                    status_str,
                    str(cert.days_remaining),
                    cert.issuer[:50] if cert.issuer else "--",
                    cert.not_after[:20] if cert.not_after else "--",
                ),
            )

        # 更新
        updates = self.report.updates
        self.update_security_label.config(text=f"安全更新: {updates.security_updates}")
        self.update_regular_label.config(text=f"常规更新: {updates.regular_updates}")
        self.update_kernel_label.config(
            text=f"内核更新: {'✅ 有' if updates.kernel_update else '无'}"
        )

        self.auto_update_label.config(
            text=f"状态: {'✅ 已启用' if updates.auto_update_enabled else '❌ 未启用'}"
        )
        self.last_update_label.config(text=f"上次更新: {updates.last_update or '未知'}")
        self.reboot_label.config(
            text=f"重启: {'⚠️ 需要' if updates.reboot_required else '不需要'}"
        )

        # SSH
        ssh = self.report.ssh_config
        self.ssh_port_label.config(text=f"端口: {ssh.port}")
        self.ssh_root_label.config(
            text=f"Root 登录: {'❌ 允许' if ssh.permit_root_login else '✅ 禁止'}"
        )
        self.ssh_password_label.config(
            text=f"密码认证: {'⚠️ 允许' if ssh.password_authentication else '✅ 仅密钥'}"
        )
        self.ssh_pubkey_label.config(
            text=f"密钥认证: {'✅ 启用' if ssh.pubkey_authentication else '❌ 禁用'}"
        )
        self.ssh_max_tries_label.config(text=f"最大尝试: {ssh.max_auth_tries}")

        self.ssh_issues_text.delete("1.0", tk.END)
        if ssh.issues:
            self.ssh_issues_text.insert("1.0", "\n".join(ssh.issues))
        else:
            self.ssh_issues_text.insert("1.0", "配置良好")

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

    def _ban_ips(self):
        """封禁暴力破解 IP"""
        if not self.report or not self.report.brute_force_ips:
            messagebox.showinfo("提示", "没有检测到暴力破解 IP")
            return

        ips = self.report.brute_force_ips
        count = len(ips)

        if not messagebox.askyesno(
            "确认", f"确定要封禁 {count} 个 IP 吗？\n\n{', '.join(ips[:10])}"
        ):
            return

        # 执行封禁
        try:
            for ip in ips:
                os.system(f"ufw deny from {ip}")
            messagebox.showinfo("成功", f"已封禁 {count} 个 IP")
            self._refresh()
        except Exception as e:
            messagebox.showerror("错误", f"封禁失败: {e}")

    def _check_ssl(self):
        """检查 SSL 证书"""
        domains_str = self.ssl_entry.get().strip()
        domains = [d.strip() for d in domains_str.split(",") if d.strip()]

        if not domains:
            return

        try:
            from core.security_health import check_ssl_certificates

            self.report.ssl_certificates = check_ssl_certificates(domains)
            self._update_ui()
        except Exception as e:
            messagebox.showerror("错误", f"检查失败: {e}")

    def _enable_firewall(self):
        """启用防火墙"""
        if not messagebox.askyesno("确认", "确定要启用防火墙吗？"):
            return

        try:
            os.system("ufw --force enable")
            messagebox.showinfo("成功", "防火墙已启用")
            self._refresh()
        except Exception as e:
            messagebox.showerror("错误", f"启用失败: {e}")

    def _disable_firewall(self):
        """禁用防火墙"""
        if not messagebox.askyesno(
            "确认", "⚠️ 确定要禁用防火墙吗？\n这将暴露所有端口！"
        ):
            return

        try:
            os.system("ufw disable")
            messagebox.showinfo("成功", "防火墙已禁用")
            self._refresh()
        except Exception as e:
            messagebox.showerror("错误", f"禁用失败: {e}")

    def _allow_nas_ports(self):
        """开放 NAS 端口"""
        ports = [8000, 443, 80]
        if not messagebox.askyesno("确认", f"确定要开放端口 {ports} 吗？"):
            return

        try:
            for port in ports:
                os.system(f"ufw allow {port}/tcp")
            messagebox.showinfo("成功", f"已开放端口: {ports}")
            self._refresh()
        except Exception as e:
            messagebox.showerror("错误", f"开放失败: {e}")

    def _install_security_updates(self):
        """安装安全更新"""
        if not messagebox.askyesno("确认", "确定要安装安全更新吗？"):
            return

        try:
            os.system("apt update && apt upgrade -y --with-new-pkgs")
            messagebox.showinfo("成功", "安全更新已安装")
            self._refresh()
        except Exception as e:
            messagebox.showerror("错误", f"安装失败: {e}")

    def _install_all_updates(self):
        """安装所有更新"""
        if not messagebox.askyesno("确认", "确定要安装所有更新吗？"):
            return

        try:
            os.system("apt update && apt full-upgrade -y")
            messagebox.showinfo("成功", "所有更新已安装")
            self._refresh()
        except Exception as e:
            messagebox.showerror("错误", f"安装失败: {e}")

    def _enable_auto_update(self):
        """启用自动更新"""
        try:
            os.system("apt install -y unattended-upgrades")
            os.system(
                "echo 'APT::Periodic::Update-Package-Lists \"1\";' > /etc/apt/apt.conf.d/20auto-upgrades"
            )
            os.system(
                "echo 'APT::Periodic::Unattended-Upgrade \"1\";' >> /etc/apt/apt.conf.d/20auto-upgrades"
            )
            messagebox.showinfo("成功", "自动更新已启用")
            self._refresh()
        except Exception as e:
            messagebox.showerror("错误", f"启用失败: {e}")

    def _harden_ssh(self):
        """加固 SSH"""
        if not messagebox.askyesno(
            "确认",
            "将执行以下加固:\n"
            "- 禁止 root 登录\n"
            "- 禁用密码认证\n"
            "- 修改端口为 2222\n"
            "- 减少最大尝试次数为 3\n\n"
            "⚠️ 请确保已配置 SSH 密钥！",
        ):
            return

        try:
            # 备份配置
            os.system("cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak")

            # 修改配置
            config_changes = [
                ("PermitRootLogin", "no"),
                ("PasswordAuthentication", "no"),
                ("Port", "2222"),
                ("MaxAuthTries", "3"),
            ]

            for key, value in config_changes:
                os.system(f"sed -i 's/^#*{key}.*/{key} {value}/' /etc/ssh/sshd_config")

            # 重启 SSH
            os.system("systemctl restart sshd")

            messagebox.showinfo("成功", "SSH 已加固\n\n新端口: 2222\n请使用密钥登录")
            self._refresh()
        except Exception as e:
            messagebox.showerror("错误", f"加固失败: {e}")

    def _export(self):
        """导出报告"""
        if not self.report:
            messagebox.showwarning("警告", "请先执行检测")
            return

        from tkinter import filedialog

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("JSON 文件", "*.json")],
            initialfile=f"security_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
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


def show_security_health_dialog(parent=None, ssh_client=None):
    """显示安全健康检测对话框"""
    dialog = SecurityHealthDialog(parent, ssh_client)
    if not parent:
        dialog.parent.mainloop()
    return dialog


if __name__ == "__main__":
    show_security_health_dialog()
