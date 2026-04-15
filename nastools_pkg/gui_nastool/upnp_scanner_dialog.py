# -*- coding: utf-8 -*-
"""
gui/upnp_scanner_dialog.py — UPnP 设备发现对话框
局域网设备扫描 / 端口映射
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, List
import threading

from core.upnp_scanner import (
    scan_upnp,
    scan_nas_devices,
    scan_routers,
    scan_media_devices,
    get_external_ip,
    add_port_mapping,
    delete_port_mapping,
    format_scan_result,
    UPnPScanResult,
    UPnPDevice,
    DeviceType,
)


class UPnPScannerDialog:
    """UPnP 设备发现对话框"""

    def __init__(self, parent: Optional[tk.Tk] = None, ssh_client=None):
        self.parent = parent or tk.Tk()
        self.ssh_client = ssh_client
        self.result: Optional[UPnPScanResult] = None
        self.scanning = False

        self._setup_ui()

    def _setup_ui(self):
        """构建 UI"""
        self.parent.title("UPnP 设备发现")
        self.parent.geometry("950x700")

        # 主框架
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ────────────────────────────────────────────────────────────
        # 顶部：扫描控制
        # ────────────────────────────────────────────────────────────
        control_frame = ttk.LabelFrame(main_frame, text="扫描控制", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # 超时设置
        timeout_frame = ttk.Frame(control_frame)
        timeout_frame.pack(side=tk.LEFT, padx=10)

        ttk.Label(timeout_frame, text="超时:").pack(side=tk.LEFT)
        self.timeout_var = tk.StringVar(value="5")
        ttk.Entry(timeout_frame, textvariable=self.timeout_var, width=5).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Label(timeout_frame, text="秒").pack(side=tk.LEFT)

        # 扫描按钮
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.LEFT, padx=20)

        self.scan_btn = ttk.Button(
            btn_frame, text="🔍 扫描所有设备", command=self._scan_all
        )
        self.scan_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="🖥️ 扫描 NAS", command=self._scan_nas).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="🌐 扫描路由器", command=self._scan_routers).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="🎬 扫描媒体设备", command=self._scan_media).pack(
            side=tk.LEFT, padx=5
        )

        # 状态
        self.status_label = ttk.Label(control_frame, text="就绪", font=("Arial", 10))
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # ────────────────────────────────────────────────────────────
        # 中部：设备列表 + 详情
        # ────────────────────────────────────────────────────────────
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧：设备列表
        list_frame = ttk.LabelFrame(content_frame, text="设备列表", padding="5")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        columns = ("name", "ip", "type", "manufacturer")
        self.device_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=20
        )

        self.device_tree.heading("name", text="名称")
        self.device_tree.heading("ip", text="IP")
        self.device_tree.heading("type", text="类型")
        self.device_tree.heading("manufacturer", text="制造商")

        self.device_tree.column("name", width=150)
        self.device_tree.column("ip", width=120)
        self.device_tree.column("type", width=80)
        self.device_tree.column("manufacturer", width=150)

        self.device_tree.bind("<<TreeviewSelect>>", self._on_device_select)

        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.device_tree.yview
        )
        self.device_tree.configure(yscrollcommand=scrollbar.set)

        self.device_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 右侧：设备详情
        detail_frame = ttk.LabelFrame(content_frame, text="设备详情", padding="10")
        detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))

        self.detail_text = tk.Text(detail_frame, width=40, wrap=tk.WORD)
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        # ────────────────────────────────────────────────────────────
        # 底部：操作按钮
        # ────────────────────────────────────────────────────────────
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(bottom_frame, text="📋 复制 IP", command=self._copy_ip).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(bottom_frame, text="🌐 打开 Web 界面", command=self._open_web).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(
            bottom_frame, text="🔌 添加端口映射", command=self._add_port_mapping
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(bottom_frame, text="💾 导出", command=self._export).pack(
            side=tk.LEFT, padx=5
        )

        # 状态栏
        self.time_label = ttk.Label(main_frame, text="", font=("Arial", 9))
        self.time_label.pack(fill=tk.X, pady=(10, 0))

    def _scan_all(self):
        """扫描所有设备"""
        self._start_scan(scan_upnp)

    def _scan_nas(self):
        """扫描 NAS 设备"""

        def scan_func():
            devices = scan_nas_devices(timeout=float(self.timeout_var.get()))
            result = UPnPScanResult(
                timestamp=datetime.now().isoformat(),
                devices=devices,
                total=len(devices),
            )
            return result

        self._start_scan(scan_func)

    def _scan_routers(self):
        """扫描路由器"""

        def scan_func():
            devices = scan_routers(timeout=float(self.timeout_var.get()))
            result = UPnPScanResult(
                timestamp=datetime.now().isoformat(),
                devices=devices,
                total=len(devices),
            )
            return result

        self._start_scan(scan_func)

    def _scan_media(self):
        """扫描媒体设备"""

        def scan_func():
            devices = scan_media_devices(timeout=float(self.timeout_var.get()))
            result = UPnPScanResult(
                timestamp=datetime.now().isoformat(),
                devices=devices,
                total=len(devices),
            )
            return result

        self._start_scan(scan_func)

    def _start_scan(self, scan_func):
        """开始扫描"""
        if self.scanning:
            return

        self.scanning = True
        self.scan_btn.config(state="disabled")
        self.status_label.config(text="扫描中...")

        # 清空列表
        self.device_tree.delete(*self.device_tree.get_children())
        self.detail_text.delete("1.0", tk.END)

        # 在线程中扫描
        def scan_thread():
            try:
                timeout = float(self.timeout_var.get())
                if callable(scan_func) and scan_func == scan_upnp:
                    self.result = scan_func(timeout=timeout)
                else:
                    self.result = scan_func()

                self.parent.after(0, self._scan_complete)
            except Exception as e:
                self.parent.after(0, lambda: self._scan_error(str(e)))

        threading.Thread(target=scan_thread, daemon=True).start()

    def _scan_complete(self):
        """扫描完成"""
        self.scanning = False
        self.scan_btn.config(state="normal")

        if self.result:
            self.status_label.config(text=f"发现 {self.result.total} 个设备")
            self.time_label.config(
                text=f"扫描时间: {self.result.timestamp} | 耗时: {self.result.scan_time_ms} ms"
            )

            # 更新设备列表
            for device in self.result.devices:
                name = device.friendly_name or device.ip
                type_str = device.category.value

                self.device_tree.insert(
                    "",
                    tk.END,
                    values=(
                        name,
                        f"{device.ip}:{device.port}",
                        type_str,
                        device.manufacturer or "--",
                    ),
                    tags=(device.ip,),
                )

    def _scan_error(self, error: str):
        """扫描错误"""
        self.scanning = False
        self.scan_btn.config(state="normal")
        self.status_label.config(text=f"扫描失败: {error}")
        messagebox.showerror("错误", f"扫描失败: {error}")

    def _on_device_select(self, event):
        """设备选择事件"""
        selection = self.device_tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.device_tree.item(item, "values")
        ip = values[1].split(":")[0]

        # 查找设备
        device = None
        if self.result:
            for d in self.result.devices:
                if d.ip == ip:
                    device = d
                    break

        if device:
            self._show_device_detail(device)

    def _show_device_detail(self, device: UPnPDevice):
        """显示设备详情"""
        self.detail_text.delete("1.0", tk.END)

        lines = []
        lines.append(f"名称: {device.friendly_name or '--'}")
        lines.append(f"IP: {device.ip}:{device.port}")
        lines.append(f"类型: {device.category.value}")
        lines.append("")
        lines.append(f"制造商: {device.manufacturer or '--'}")
        lines.append(f"型号: {device.model_name or '--'}")
        lines.append(f"型号编号: {device.model_number or '--'}")
        lines.append(f"序列号: {device.serial_number or '--'}")
        lines.append("")
        lines.append(f"设备类型: {device.device_type or '--'}")
        lines.append(f"服务器: {device.server or '--'}")
        lines.append("")
        lines.append("服务列表:")
        if device.services:
            for service in device.services[:10]:
                lines.append(f"  • {service}")
        else:
            lines.append("  无")

        lines.append("")
        lines.append(f"USN: {device.usn or '--'}")
        lines.append(f"Location: {device.location or '--'}")

        self.detail_text.insert("1.0", "\n".join(lines))

    def _copy_ip(self):
        """复制 IP 地址"""
        selection = self.device_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择设备")
            return

        item = selection[0]
        values = self.device_tree.item(item, "values")
        ip = values[1]

        self.parent.clipboard_clear()
        self.parent.clipboard_append(ip)
        messagebox.showinfo("成功", f"已复制: {ip}")

    def _open_web(self):
        """打开 Web 界面"""
        selection = self.device_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择设备")
            return

        item = selection[0]
        values = self.device_tree.item(item, "values")
        ip = values[1].split(":")[0]

        # 尝试常见端口
        import webbrowser

        url = f"http://{ip}"

        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开: {e}")

    def _add_port_mapping(self):
        """添加端口映射"""
        selection = self.device_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择路由器设备")
            return

        item = selection[0]
        values = self.device_tree.item(item, "values")
        ip = values[1].split(":")[0]

        # 查找设备
        device = None
        if self.result:
            for d in self.result.devices:
                if d.ip == ip:
                    device = d
                    break

        if not device:
            return

        if device.category != DeviceType.ROUTER:
            messagebox.showwarning("提示", "请选择路由器设备")
            return

        # 弹出对话框
        dialog = PortMappingDialog(self.parent, device)
        self.parent.wait_window(dialog.dialog)

    def _export(self):
        """导出扫描结果"""
        if not self.result:
            messagebox.showwarning("提示", "请先执行扫描")
            return

        from tkinter import filedialog

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("JSON 文件", "*.json")],
            initialfile=f"upnp_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )

        if not filepath:
            return

        try:
            if filepath.endswith(".json"):
                import json
                from dataclasses import asdict

                data = asdict(self.result)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(format_scan_result(self.result))

            messagebox.showinfo("成功", f"报告已保存到: {filepath}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")


class PortMappingDialog:
    """端口映射对话框"""

    def __init__(self, parent, device: UPnPDevice):
        self.device = device
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("添加端口映射")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        """构建 UI"""
        frame = ttk.Frame(self.dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # 设备信息
        ttk.Label(
            frame,
            text=f"设备: {self.device.friendly_name or self.device.ip}",
            font=("Arial", 12, "bold"),
        ).pack(anchor=tk.W, pady=(0, 10))

        # 外部端口
        ext_frame = ttk.Frame(frame)
        ext_frame.pack(fill=tk.X, pady=5)
        ttk.Label(ext_frame, text="外部端口:").pack(side=tk.LEFT)
        self.ext_port_var = tk.StringVar(value="8080")
        ttk.Entry(ext_frame, textvariable=self.ext_port_var, width=10).pack(
            side=tk.LEFT, padx=10
        )

        # 内部端口
        int_frame = ttk.Frame(frame)
        int_frame.pack(fill=tk.X, pady=5)
        ttk.Label(int_frame, text="内部端口:").pack(side=tk.LEFT)
        self.int_port_var = tk.StringVar(value="8080")
        ttk.Entry(int_frame, textvariable=self.int_port_var, width=10).pack(
            side=tk.LEFT, padx=10
        )

        # 内部客户端
        client_frame = ttk.Frame(frame)
        client_frame.pack(fill=tk.X, pady=5)
        ttk.Label(client_frame, text="内部 IP:").pack(side=tk.LEFT)
        self.client_var = tk.StringVar(value="")
        ttk.Entry(client_frame, textvariable=self.client_var, width=15).pack(
            side=tk.LEFT, padx=10
        )

        # 协议
        proto_frame = ttk.Frame(frame)
        proto_frame.pack(fill=tk.X, pady=5)
        ttk.Label(proto_frame, text="协议:").pack(side=tk.LEFT)
        self.proto_var = tk.StringVar(value="TCP")
        ttk.Radiobutton(
            proto_frame, text="TCP", variable=self.proto_var, value="TCP"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            proto_frame, text="UDP", variable=self.proto_var, value="UDP"
        ).pack(side=tk.LEFT, padx=5)

        # 描述
        desc_frame = ttk.Frame(frame)
        desc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(desc_frame, text="描述:").pack(side=tk.LEFT)
        self.desc_var = tk.StringVar(value="nastool")
        ttk.Entry(desc_frame, textvariable=self.desc_var, width=20).pack(
            side=tk.LEFT, padx=10
        )

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(btn_frame, text="添加", command=self._add_mapping).pack(
            side=tk.LEFT, padx=10
        )

        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy).pack(
            side=tk.LEFT, padx=10
        )

    def _add_mapping(self):
        """添加端口映射"""
        try:
            ext_port = int(self.ext_port_var.get())
            int_port = int(self.int_port_var.get())
            client = self.client_var.get()
            proto = self.proto_var.get()
            desc = self.desc_var.get()

            if not client:
                messagebox.showwarning("提示", "请输入内部 IP")
                return

            success = add_port_mapping(
                self.device, ext_port, int_port, client, proto, desc
            )

            if success:
                messagebox.showinfo(
                    "成功", f"端口映射已添加: {ext_port} → {client}:{int_port}"
                )
                self.dialog.destroy()
            else:
                messagebox.showerror("失败", "添加端口映射失败")

        except ValueError:
            messagebox.showerror("错误", "端口必须是数字")


def show_upnp_scanner_dialog(parent=None, ssh_client=None):
    """显示 UPnP 扫描对话框"""
    dialog = UPnPScannerDialog(parent, ssh_client)
    if not parent:
        dialog.parent.mainloop()
    return dialog


if __name__ == "__main__":
    show_upnp_scanner_dialog()
