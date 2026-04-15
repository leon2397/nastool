# -*- coding: utf-8 -*-
"""
nastools 主题配置 — 深色科技风
"""

# ── 颜色常量 ──
BG = "#0d1117"
PANEL = "#161b22"
PANEL2 = "#1c2128"
BORDER = "#30363d"
TEXT = "#e6edf3"
DIM = "#8b949e"
GREEN = "#3fb950"
YELLOW = "#d29922"
RED = "#f85149"
BLUE = "#58a6ff"
ACCENT = GREEN

# ── 严重性颜色/图标映射 ──
SEV_COLORS = {
    "passed": GREEN,
    "warning": YELLOW,
    "critical": RED,
    "info": BLUE,
}

SEV_ICONS = {
    "passed": "✓",
    "warning": "!",
    "critical": "✗",
    "info": "i",
}

# ── 检测项元数据 ──
# 与 nastool checks/__init__.py 实际注册项完全对齐（22项）
CHECK_DEFS = {
    # 系统
    "python_version": {"title": "Python 版本", "cat": "系统"},
    "pip_installed": {"title": "pip 管理器", "cat": "系统"},
    "system_libs": {"title": "系统依赖库", "cat": "系统"},
    "memory_check": {"title": "内存状态", "cat": "系统"},
    # 网络
    "internet_access": {"title": "互联网连接", "cat": "网络"},
    "dns_resolve": {"title": "DNS 解析", "cat": "网络"},
    "port_conflict": {"title": "端口冲突", "cat": "网络"},
    "nas_backend": {"title": "NAS 后端连通", "cat": "网络"},
    # 存储
    "disk_space": {"title": "磁盘空间", "cat": "存储"},
    "path_exists": {"title": "存储路径", "cat": "存储"},
    "write_speed": {"title": "写入速度", "cat": "存储"},
    # AI算力
    "gpu_detected": {"title": "GPU/NPU 检测", "cat": "AI算力"},
    "nvidia_driver_version": {"title": "NVIDIA 驱动", "cat": "AI算力"},
    "cuda_version": {"title": "CUDA 版本", "cat": "AI算力"},
    "jetpack_version": {"title": "JetPack 版本", "cat": "AI算力"},
    "pytorch_version": {"title": "PyTorch 版本", "cat": "AI算力"},
    "onnxruntime_version": {"title": "ONNX Runtime", "cat": "AI算力"},
    "tensorrt_version": {"title": "TensorRT 版本", "cat": "AI算力"},
    "rknn_version": {"title": "RKNN SDK 版本", "cat": "AI算力"},
    # 安全
    "firewall": {"title": "防火墙", "cat": "安全"},
    "selinux": {"title": "SELinux 配置", "cat": "安全"},
    "ssh_root": {"title": "SSH Root 登录", "cat": "安全"},
}


def apply_theme(root):
    """给 tkinter root 和 ttk.Style 应用深色主题"""
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, fieldbackground=PANEL2)
    style.configure("TFrame", background=PANEL)
    style.configure("Card.TFrame", background=PANEL, relief="flat", borderwidth=0)
    style.configure("TLabelframe", background=PANEL, foreground=TEXT, borderwidth=0)
    style.configure("TLabelframe.Label", background=PANEL, foreground=TEXT)
    style.configure("TLabel", background=PANEL, foreground=TEXT)
    style.configure("TButton", background=PANEL2, foreground=TEXT, borderwidth=0)
    style.configure(
        "Green.TButton",
        background=GREEN,
        foreground=BG,
        font=("Microsoft YaHei", 10, "bold"),
    )
    style.configure(
        "Red.TButton", background=RED, foreground=BG, font=("Microsoft YaHei", 10)
    )
    style.configure(
        "Yellow.TButton", background=YELLOW, foreground=BG, font=("Microsoft YaHei", 10)
    )
    style.configure("TRadiobutton", background=PANEL, foreground=TEXT)
    style.configure("TCheckbutton", background=PANEL, foreground=TEXT)
    style.configure(
        "Treeview",
        background=PANEL,
        foreground=TEXT,
        fieldbackground=PANEL,
        borderwidth=0,
        rowheight=24,
    )
    style.configure(
        "Treeview.Heading", background=PANEL2, foreground=DIM, borderwidth=0
    )


def set_color(widget, **kwargs):
    """设置 widget 颜色（兼容 ttk / tkinter）"""
    try:
        widget.configure(**kwargs)
    except Exception:
        pass
