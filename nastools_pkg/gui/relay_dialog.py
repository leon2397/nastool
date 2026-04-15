# -*- coding: utf-8 -*-
"""
gui/relay_dialog.py — Relay Server 连接对话框

功能：
- 输入 Relay Server URL 和登录凭据
- 连接 WebSocket 获取在线设备列表
- 多设备批量操作（命令/文件/部署）
- 设备详情面板（系统信息/在线状态）
- 命令历史记录（持久化）
- 自动刷新设备状态
"""

import tkinter as tk
import os
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import json
import time
import uuid
from typing import Optional, Dict, List, Callable

try:
    import websockets
    import asyncio

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

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
)

# ── 历史记录存储 ─────────────────────────────────────────────────────────
_HISTORY_FILE = os.path.join(os.path.dirname(__file__), ".relay_history.json")


def _load_history() -> List[Dict]:
    try:
        if os.path.exists(_HISTORY_FILE):
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_history(entries: List[Dict]):
    try:
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(entries[-500:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── Relay Connection ──────────────────────────────────────────────────────


class RelayConnection:
    """Relay Server 连接管理"""

    def __init__(self):
        self.url = ""
        self.token = ""
        self.ws = None
        self.connected = False
        self.devices: List[Dict] = []
        self.loop = None
        self.ws_thread = None
        self.message_callback: Optional[Callable] = None

    def login(self, relay_url: str, username: str, password: str) -> tuple:
        """登录获取 token"""
        if not HAS_REQUESTS:
            return False, "需要安装 requests: pip install requests"

        base = relay_url.rstrip("/")
        if base.startswith("wss://"):
            base = "https://" + base[6:]
        elif base.startswith("ws://"):
            base = "http://" + base[5:]

        api_url = f"{base}/api/v1/auth/login"

        try:
            resp = requests.post(
                api_url, json={"username": username, "password": password}, timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("token", "")
                self.url = base
                return True, "登录成功"
            else:
                return False, f"登录失败: {resp.status_code}"
        except Exception as e:
            return False, f"连接失败: {e}"

    def connect_ws(self, on_message: Callable) -> tuple:
        """连接 WebSocket"""
        if not HAS_WEBSOCKETS:
            return False, "需要安装 websockets: pip install websockets"

        if not self.token:
            return False, "未登录"

        ws_url = self.url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/ws/gui?token={self.token}"

        self.message_callback = on_message

        self.ws_thread = threading.Thread(
            target=self._ws_loop, args=(ws_url,), daemon=True
        )
        self.ws_thread.start()

        return True, "正在连接..."

    def _ws_loop(self, ws_url: str):
        """WebSocket 事件循环"""

        async def run():
            try:
                self.ws = await websockets.connect(ws_url)
                self.connected = True
                if self.message_callback:
                    self.message_callback({"type": "connected"})

                while self.connected:
                    try:
                        raw = await asyncio.wait_for(self.ws.recv(), timeout=1)
                        msg = json.loads(raw)
                        if self.message_callback:
                            self.message_callback(msg)
                    except asyncio.TimeoutError:
                        continue
                    except websockets.ConnectionClosed:
                        break

            except Exception as e:
                if self.message_callback:
                    self.message_callback(
                        {"type": "error", "payload": {"message": str(e)}}
                    )
            finally:
                self.connected = False
                if self.message_callback:
                    self.message_callback({"type": "disconnected"})

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(run())

    def send_command(self, device_id: str, cmd: str, timeout_ms: int = 30000) -> str:
        """发送命令到设备"""
        import uuid

        command_id = f"cmd_{uuid.uuid4().hex[:12]}"

        msg = {
            "type": "command",
            "id": command_id,
            "timestamp": int(time.time() * 1000),
            "target": device_id,
            "payload": {
                "command_id": command_id,
                "cmd": cmd,
                "timeout_ms": timeout_ms,
            },
        }

        if self.ws and self.connected:
            asyncio.run_coroutine_threadsafe(self.ws.send(json.dumps(msg)), self.loop)
            return command_id
        return ""

    def subscribe(self, device_id: str):
        """订阅设备消息"""
        msg = {
            "type": "subscribe",
            "id": f"sub_{int(time.time())}",
            "timestamp": int(time.time() * 1000),
            "payload": {"device_id": device_id},
        }
        if self.ws and self.connected:
            asyncio.run_coroutine_threadsafe(self.ws.send(json.dumps(msg)), self.loop)

    def upload_file(
        self, device_id: str, file_path: str, target_path: str = "/tmp/"
    ) -> str:
        """上传本地文件到设备"""
        import base64, uuid

        file_id = f"file_{uuid.uuid4().hex[:12]}"

        try:
            with open(file_path, "rb") as f:
                content_bytes = f.read()
            content_b64 = base64.b64encode(content_bytes).decode("ascii")
            name = os.path.basename(file_path)
            size = len(content_bytes)
        except Exception as e:
            return ""

        msg = {
            "type": "file",
            "id": file_id,
            "timestamp": int(time.time() * 1000),
            "target": device_id,
            "payload": {
                "file_id": file_id,
                "name": name,
                "size": size,
                "content_base64": content_b64,
                "path": target_path,
                "mode": "0755" if name.endswith(".sh") else "0644",
            },
        }

        if self.ws and self.connected:
            asyncio.run_coroutine_threadsafe(self.ws.send(json.dumps(msg)), self.loop)
            return file_id
        return ""

    def request_file(
        self, device_id: str, file_path: str, file_request_id: str = None
    ) -> str:
        """请求设备上的文件"""
        import uuid

        freq_id = file_request_id or f"freq_{uuid.uuid4().hex[:12]}"

        msg = {
            "type": "file_request",
            "id": freq_id,
            "timestamp": int(time.time() * 1000),
            "target": device_id,
            "payload": {
                "file_request_id": freq_id,
                "path": file_path,
                "encoding": "base64",
            },
        }

        if self.ws and self.connected:
            asyncio.run_coroutine_threadsafe(self.ws.send(json.dumps(msg)), self.loop)
            return freq_id
        return ""

    def batch_command(
        self, device_ids: List[str], cmd: str, timeout_ms: int = 30000
    ) -> List[str]:
        """向多个设备发送同一命令，返回命令ID列表"""
        command_ids = []
        for device_id in device_ids:
            cid = self.send_command(device_id, cmd, timeout_ms)
            if cid:
                command_ids.append(cid)
        return command_ids

    def deploy(
        self,
        device_id: str,
        deployment_id: str,
        version: str = "latest",
        url: str = None,
        install_path: str = "/opt/ai-nas",
        backup: bool = True,
        restart: bool = True,
    ) -> bool:
        """发送部署指令到设备"""
        msg = {
            "type": "deploy",
            "id": deployment_id,
            "timestamp": int(time.time() * 1000),
            "target": device_id,
            "payload": {
                "deployment_id": deployment_id,
                "version": version,
                "url": url,
                "files": [],
                "config": {"install_path": install_path},
                "backup": backup,
                "restart": restart,
            },
        }

        if self.ws and self.connected:
            asyncio.run_coroutine_threadsafe(self.ws.send(json.dumps(msg)), self.loop)
            return True
        return False

    def close(self):
        """关闭连接"""
        self.connected = False
        if self.ws:
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)

    def register_agent(
        self, label: str, device_type: str = "generic", device_name: str = ""
    ) -> tuple:
        """通过 Relay API 预注册设备，返回 (success, agent_key_or_error_msg)"""
        if not self.url:
            return False, "未连接 Relay，请先登录"

        api_base = self.url
        # 使用 agent_key 或 token
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            import requests

            # 优先 v7.1 端点，fallback v2.0 端点
            for endpoint in ["/agent/keys/generate", "/keys/generate"]:
                try:
                    resp = requests.post(
                        f"{api_base}{endpoint}",
                        json={
                            "label": label,
                            "device_type": device_type,
                            "device_name": device_name,
                        },
                        headers=headers,
                        timeout=10,
                    )
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        return True, data.get("agent_key", "")
                    elif resp.status_code == 404:
                        continue  # 试下一个端点
                    else:
                        return False, f"HTTP {resp.status_code}: {resp.text[:100]}"
                except requests.RequestException:
                    continue

            return False, "Relay 不支持设备注册 API"
        except ImportError:
            return False, "需要安装 requests: pip install requests"
        except Exception as e:
            return False, str(e)


class RelayDialog:
    """Relay Server 连接对话框"""

    def __init__(self, parent: Optional[tk.Tk] = None):
        self.parent = parent or tk.Tk()
        self.relay = RelayConnection()
        self.queue: queue.Queue = queue.Queue()
        self.devices: List[Dict] = []
        self.selected_device: Optional[str] = None
        self._selected_devices: Dict[str, bool] = {}  # device_id → selected
        self._pending_downloads: Dict[str, str] = {}  # file_request_id → save_path
        self._pending_deploy: Optional[str] = None
        self._auto_refresh_running = False

        self._setup_ui()
        self._start_consumer()

    def _setup_ui(self):
        """构建 UI"""
        self.parent.title("Relay Server - 远程设备管理")
        self.parent.geometry("900x700")
        self.parent.configure(bg=BG)

        main = tk.Frame(self.parent, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # ── 标题 ─────────────────────────────────────────────────
        hdr = tk.Frame(main, bg=BG)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(
            hdr, text="Relay Server", font=("Consolas", 16, "bold"), fg=ACCENT, bg=BG
        ).pack(side="left")
        tk.Label(
            hdr, text="远程设备管理", font=("Microsoft YaHei", 10), fg=DIM, bg=BG
        ).pack(side="left", padx=8)
        self.status_label = tk.Label(
            hdr, text="未连接", font=("Microsoft YaHei", 9), fg=DIM, bg=BG
        )
        self.status_label.pack(side="right")

        self._sep(main).pack(fill="x", pady=5)

        # ── 连接面板 ─────────────────────────────────────────────
        self._build_connection_panel(main)
        self._sep(main).pack(fill="x", pady=5)

        # ── 设备列表 ─────────────────────────────────────────────
        self._build_device_list(main)
        self._sep(main).pack(fill="x", pady=5)

        # ── 命令面板 ─────────────────────────────────────────────
        self._build_command_panel(main)
        self._sep(main).pack(fill="x", pady=5)

        # ── 底部标签页（结果/文件/部署）────────────────────────
        self._build_bottom_tabs(main)

    def _sep(self, parent):
        return tk.Frame(parent, bg=BORDER, height=1)

    def _build_connection_panel(self, parent):
        """连接面板"""
        conn = tk.LabelFrame(
            parent,
            text="连接 Relay Server",
            font=("Microsoft YaHei", 10, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=12,
            pady=10,
            relief="flat",
            bd=0,
        )
        conn.pack(fill="x", pady=(0, 8))

        # URL
        row1 = tk.Frame(conn, bg=PANEL)
        row1.pack(fill="x", pady=2)
        tk.Label(
            row1,
            text="Relay URL",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=12,
            anchor="e",
        ).pack(side="left")
        self.url_var = tk.StringVar(value="http://120.77.249.3:18888")
        tk.Entry(
            row1,
            textvariable=self.url_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 10),
            relief="flat",
            width=40,
            bd=0,
        ).pack(side="left", padx=4)

        # 用户名密码
        row2 = tk.Frame(conn, bg=PANEL)
        row2.pack(fill="x", pady=2)
        tk.Label(
            row2,
            text="用户名",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=12,
            anchor="e",
        ).pack(side="left")
        self.user_var = tk.StringVar(value="admin")
        tk.Entry(
            row2,
            textvariable=self.user_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 10),
            relief="flat",
            width=16,
            bd=0,
        ).pack(side="left", padx=4)
        tk.Label(
            row2,
            text="密码",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=6,
            anchor="e",
        ).pack(side="left")
        self.pass_var = tk.StringVar(value="relay-admin-2026")
        tk.Entry(
            row2,
            textvariable=self.pass_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 10),
            relief="flat",
            width=16,
            bd=0,
            show="●",
        ).pack(side="left")

        # 按钮
        row3 = tk.Frame(conn, bg=PANEL)
        row3.pack(fill="x", pady=(6, 0))
        self.connect_btn = tk.Button(
            row3,
            text="连接",
            font=("Microsoft YaHei", 10, "bold"),
            fg=BG,
            bg=GREEN,
            activebackground=GREEN,
            relief="flat",
            bd=0,
            padx=16,
            pady=4,
            cursor="hand2",
            command=self._on_connect,
        )
        self.connect_btn.pack(side="left")
        self.disconnect_btn = tk.Button(
            row3,
            text="断开",
            font=("Microsoft YaHei", 9),
            fg=TEXT,
            bg=BORDER,
            activebackground=BORDER,
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            state="disabled",
            command=self._on_disconnect,
        )
        self.disconnect_btn.pack(side="left", padx=4)
        self.refresh_btn = tk.Button(
            row3,
            text="刷新设备",
            font=("Microsoft YaHei", 9),
            fg=TEXT,
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            state="disabled",
            command=self._on_refresh,
        )
        self.refresh_btn.pack(side="left", padx=4)

        # ── 注册设备按钮（T3 新增）──────────────────────────────
        self.register_btn = tk.Button(
            row3,
            text="注册设备",
            font=("Microsoft YaHei", 9),
            fg="#FF9800",
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            state="disabled",
            command=self._on_register_device,
        )
        self.register_btn.pack(side="left", padx=4)

    def _build_device_list(self, parent):
        """设备列表 + 详情面板（左右布局）"""
        dev_frame = tk.LabelFrame(
            parent,
            text="在线设备",
            font=("Microsoft YaHei", 10, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=12,
            pady=8,
            relief="flat",
            bd=0,
        )
        dev_frame.pack(fill="both", expand=True, pady=(0, 8))

        # ── 左右容器 ─────────────────────────────────────────
        split = tk.Frame(dev_frame, bg=PANEL)
        split.pack(fill="both", expand=True)

        # 左：设备列表
        left = tk.Frame(split, bg=PANEL)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # 全选/反选工具栏
        toolbar = tk.Frame(left, bg=PANEL)
        toolbar.pack(fill="x", pady=(0, 4))

        self.select_all_btn = tk.Button(
            toolbar,
            text="全选",
            font=("Microsoft YaHei", 8),
            fg=TEXT,
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            state="disabled",
            command=self._on_select_all,
        )
        self.select_all_btn.pack(side="left", padx=(0, 4))

        self.deselect_btn = tk.Button(
            toolbar,
            text="取消选择",
            font=("Microsoft YaHei", 8),
            fg=TEXT,
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            state="disabled",
            command=self._on_deselect_all,
        )
        self.deselect_btn.pack(side="left", padx=(0, 4))

        self.selection_label = tk.Label(
            toolbar,
            text="已选: 0 台设备",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 8),
        )
        self.selection_label.pack(side="right")

        cols = ("select", "device_id", "name", "type", "status")
        self.device_tree = ttk.Treeview(left, columns=cols, show="headings", height=6)
        self.device_tree.heading("select", text="☑")
        self.device_tree.heading("device_id", text="设备ID")
        self.device_tree.heading("name", text="名称")
        self.device_tree.heading("type", text="类型")
        self.device_tree.heading("status", text="状态")
        self.device_tree.column("select", width=30, anchor="center")
        self.device_tree.column("device_id", width=180, anchor="w")
        self.device_tree.column("name", width=120, anchor="w")
        self.device_tree.column("type", width=100, anchor="w")
        self.device_tree.column("status", width=60, anchor="center")

        self.device_tree.bind("<<TreeviewSelect>>", self._on_device_select)
        self.device_tree.bind("<Button-1>", self._on_tree_click)

        sb = ttk.Scrollbar(left, orient="vertical", command=self.device_tree.yview)
        self.device_tree.configure(yscrollcommand=sb.set)

        self.device_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # 右：设备详情
        self.detail_panel = self._build_device_detail(split)
        self.detail_panel.pack(side="right", fill="y", padx=(8, 0))

        # 追踪选中的设备
        self._selected_devices: Dict[str, bool] = {}  # device_id → selected

    def _build_device_detail(self, parent) -> tk.Frame:
        """设备详情面板（右侧）"""
        frame = tk.LabelFrame(
            parent,
            text="设备详情",
            font=("Microsoft YaHei", 9, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=10,
            pady=8,
            relief="flat",
            bd=0,
        )

        self.detail_device_id = tk.Label(
            frame, text="—", fg=DIM, bg=PANEL, font=("Microsoft YaHei", 9)
        )
        self.detail_device_id.pack(anchor="w")

        self.detail_rows: Dict[str, tk.Label] = {}
        for key, label in [
            ("type", "类型"),
            ("status", "状态"),
            ("online_time", "在线时长"),
            ("last_report", "最后报告"),
            ("version", "版本"),
            ("ip", "IP 地址"),
        ]:
            row = tk.Frame(frame, bg=PANEL)
            row.pack(fill="x", pady=1)
            tk.Label(
                row,
                text=f"{label}：",
                fg=DIM,
                bg=PANEL,
                font=("Microsoft YaHei", 8),
                width=10,
                anchor="e",
            ).pack(side="left")
            lbl = tk.Label(row, text="—", fg=DIM, bg=PANEL, font=("Microsoft YaHei", 8))
            lbl.pack(side="left")
            self.detail_rows[key] = lbl

        # 快捷批量操作
        batch = tk.Frame(frame, bg=PANEL)
        batch.pack(fill="x", pady=(8, 0))
        tk.Label(
            batch, text="批量操作：", fg=DIM, bg=PANEL, font=("Microsoft YaHei", 8)
        ).pack(anchor="w")

        for label, cmd in [
            ("快速检测", "python3 /opt/ai-nas/arm_diagnose.py --quick"),
            ("完整检测", "python3 /opt/ai-nas/arm_diagnose.py --full"),
            ("系统状态", "echo '=== System ===' && uptime && free -h && df -h"),
        ]:
            btn = tk.Button(
                batch,
                text=label,
                font=("Microsoft YaHei", 7),
                fg=TEXT,
                bg=PANEL2,
                activebackground=PANEL2,
                relief="flat",
                bd=0,
                padx=6,
                pady=2,
                cursor="hand2",
                state="disabled",
                command=lambda c=cmd: self._on_batch_cmd(c),
            )
            btn.pack(anchor="w", pady=1, fill="x")

        # 批量部署按钮
        self.batch_deploy_btn = tk.Button(
            batch,
            text="批量部署 AI-NAS",
            font=("Microsoft YaHei", 7, "bold"),
            fg="#fff",
            bg="#2196F3",
            activebackground="#1976D2",
            relief="flat",
            bd=0,
            padx=6,
            pady=3,
            cursor="hand2",
            state="disabled",
            command=self._on_batch_deploy,
        )
        self.batch_deploy_btn.pack(anchor="w", pady=(8, 1), fill="x")

        # 批量部署进度标签
        self.batch_deploy_label = tk.Label(
            batch, text="", fg="#FF9800", bg=PANEL, font=("Microsoft YaHei", 7)
        )

        return frame

    def _on_tree_click(self, event):
        """处理 Treeview 点击（用于切换选择）"""
        region = self.device_tree.identify("region", event.x, event.y)
        if region == "heading":
            col = self.device_tree.identify_column(event.x)
            if col == "#1":  # 选择列
                self._on_toggle_select()

    def _on_toggle_select(self):
        """切换全选/取消"""
        all_selected = all(
            self._selected_devices.get(d, False) for d in self._selected_devices
        )
        if all_selected:
            self._on_deselect_all()
        else:
            self._on_select_all()

    def _on_select_all(self):
        """全选所有设备"""
        for d in self._selected_devices:
            self._selected_devices[d] = True
        self._redraw_device_tree()
        self._update_selection_label()
        self._update_batch_buttons()

    def _on_deselect_all(self):
        """取消所有选择"""
        for d in self._selected_devices:
            self._selected_devices[d] = False
        self._redraw_device_tree()
        self._update_selection_label()
        self._update_batch_buttons()

    def _update_selection_label(self):
        count = sum(1 for v in self._selected_devices.values() if v)
        self.selection_label.config(text=f"已选: {count} 台设备")
        self.select_all_btn.config(state="normal")
        self.deselect_btn.config(
            state="normal" if self._selected_devices else "disabled"
        )

    def _update_batch_buttons(self):
        """启用/禁用批量操作按钮"""
        has_sel = any(self._selected_devices.values())
        state = "normal" if has_sel and self.relay.connected else "disabled"
        for child in self.detail_panel.winfo_children():
            if isinstance(child, tk.Frame):
                for btn in child.winfo_children():
                    if isinstance(btn, tk.Button):
                        btn.config(state=state)

    def _on_batch_cmd(self, cmd: str):
        """向所有已选设备发送批量命令"""
        selected = [d for d, v in self._selected_devices.items() if v]
        if not selected:
            messagebox.showwarning("提示", "请先选择设备", parent=self.parent)
            return

        if len(selected) > 1:
            confirm = messagebox.askyesno(
                "确认批量操作",
                f"将向 {len(selected)} 台设备执行：\n\n{cmd}",
                parent=self.parent,
            )
            if not confirm:
                return

        # 切换到"命令"标签页显示结果
        try:
            self.notebook.select(0)
        except Exception:
            pass

        self.log(f"\n=== 批量执行 ({len(selected)} 台) ===")
        self.log(f"> {cmd}")

        ids = self.relay.batch_command(selected, cmd)
        self.log(f"已发送 {len(ids)} 个命令请求")

    def _on_batch_deploy(self):
        """批量部署到所有已选设备"""
        selected = [d for d, v in self._selected_devices.items() if v]
        if not selected:
            messagebox.showwarning("提示", "请先选择设备", parent=self.parent)
            return

        version = self.deploy_version_var.get().strip() or "latest"
        install_path = self.install_path_var.get().strip() or "/opt/ai-nas"
        url = self.deploy_url_var.get().strip()
        backup = self.backup_var.get()
        restart = self.restart_var.get()

        # 确认对话框
        confirm = messagebox.askyesno(
            "确认批量部署",
            f"将部署 AI-NAS v{version} 到 {len(selected)} 台设备\n\n"
            f"安装路径: {install_path}\n"
            f"选项: {'备份+重启' if backup and restart else ('备份' if backup else ('重启' if restart else '无'))}",
            parent=self.parent,
        )
        if not confirm:
            return

        # 切换到部署标签页
        try:
            self.notebook.select(2)  # 部署标签页
        except Exception:
            pass

        # 初始化批量部署状态
        self._batch_deploy_results = {}
        target_count = len(selected)

        self.file_log_write(f"\n=== 批量部署 ({len(selected)} 台) ===")
        self.batch_deploy_label.config(text=f"正在部署: 0/{target_count}")
        self.batch_deploy_btn.config(state="disabled", text="部署中...")

        # 逐个发送部署请求
        success_count = 0
        import uuid

        for device_id in selected:
            deployment_id = f"dep_{uuid.uuid4().hex[:12]}"
            ok = self.relay.deploy(
                device_id,
                deployment_id,
                version=version,
                url=url or None,
                install_path=install_path,
                backup=backup,
                restart=restart,
            )
            if ok:
                success_count += 1
                self._batch_deploy_results[device_id] = {
                    "status": "pending",
                    "deployment_id": deployment_id,
                }

        self.file_log_write(f"已发送 {success_count}/{target_count} 个部署请求")

        if success_count == 0:
            self.batch_deploy_btn.config(state="normal", text="批量部署 AI-NAS")
            self.batch_deploy_label.config(text="")
            messagebox.showerror("错误", "发送失败：未连接", parent=self.parent)

    def _update_batch_deploy_progress(
        self, device_id: str, progress: int, step: str, message: str
    ):
        """更新单台设备的部署进度"""
        if device_id in self._batch_deploy_results:
            self._batch_deploy_results[device_id]["progress"] = progress
            self._batch_deploy_results[device_id]["step"] = step

        # 更新汇总进度
        total = len(self._batch_deploy_results)
        if total > 0:
            avg_progress = (
                sum(v.get("progress", 0) for v in self._batch_deploy_results.values())
                / total
            )
            self.batch_deploy_label.config(text=f"正在部署: {int(avg_progress)}%")

    def _finish_batch_deploy(
        self, device_id: str, success: bool, version: str, message: str
    ):
        """完成单台设备的部署"""
        if device_id in self._batch_deploy_results:
            self._batch_deploy_results[device_id]["status"] = (
                "success" if success else "failed"
            )
            self._batch_deploy_results[device_id]["message"] = message

        # 更新计数
        total = len(self._batch_deploy_results)
        done = sum(
            1
            for v in self._batch_deploy_results.values()
            if v.get("status") != "pending"
        )

        if done < total:
            self.batch_deploy_label.config(text=f"正在部署: {done}/{total}")
        else:
            # 全部完成
            success_count = sum(
                1
                for v in self._batch_deploy_results.values()
                if v.get("status") == "success"
            )
            self.batch_deploy_btn.config(state="normal", text="批量部署 AI-NAS")
            self.batch_deploy_label.config(text=f"完成: {success_count}/{total} 成功")
            self.file_log_write(f"\n批量部署完成: {success_count}/{total} 成功")

            if success_count == total:
                messagebox.showinfo(
                    "部署成功", f"全部 {total} 台设备部署成功！", parent=self.parent
                )
            elif success_count > 0:
                messagebox.showwarning(
                    "部分成功",
                    f"{success_count}/{total} 台设备部署成功",
                    parent=self.parent,
                )
            else:
                messagebox.showerror(
                    "部署失败", "所有设备部署均失败", parent=self.parent
                )

    def _build_command_panel(self, parent):
        """命令面板"""
        cmd_frame = tk.LabelFrame(
            parent,
            text="执行命令",
            font=("Microsoft YaHei", 10, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=12,
            pady=8,
            relief="flat",
            bd=0,
        )
        cmd_frame.pack(fill="x", pady=(0, 8))

        # 设备选择
        row1 = tk.Frame(cmd_frame, bg=PANEL)
        row1.pack(fill="x", pady=2)
        tk.Label(
            row1,
            text="目标设备",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=12,
            anchor="e",
        ).pack(side="left")
        self.target_label = tk.Label(
            row1,
            text="（请在上方选择设备）",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
        )
        self.target_label.pack(side="left", padx=4)

        # 命令输入
        row2 = tk.Frame(cmd_frame, bg=PANEL)
        row2.pack(fill="x", pady=2)
        tk.Label(
            row2,
            text="命令",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=12,
            anchor="e",
        ).pack(side="left")
        self.cmd_var = tk.StringVar(value="")
        tk.Entry(
            row2,
            textvariable=self.cmd_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 10),
            relief="flat",
            width=60,
            bd=0,
        ).pack(side="left", padx=4)

        # 快捷命令
        row3 = tk.Frame(cmd_frame, bg=PANEL)
        row3.pack(fill="x", pady=(6, 0))

        quick_cmds = [
            ("检测", "python3 /opt/ai-nas/arm_diagnose.py --quick"),
            ("完整检测", "python3 /opt/ai-nas/arm_diagnose.py --full"),
            ("磁盘", "df -h"),
            ("内存", "free -h"),
            ("进程", "ps aux | head -20"),
        ]

        for label, cmd in quick_cmds:
            btn = tk.Button(
                row3,
                text=label,
                font=("Microsoft YaHei", 8),
                fg=TEXT,
                bg=PANEL2,
                activebackground=PANEL2,
                relief="flat",
                bd=0,
                padx=8,
                pady=2,
                cursor="hand2",
                command=lambda c=cmd: self._set_cmd(c),
            )
            btn.pack(side="left", padx=2)

        tk.Label(row3, text="", fg=DIM, bg=PANEL, font=("", 4)).pack(
            side="left", fill="x", expand=True
        )

        self.exec_btn = tk.Button(
            row3,
            text="执行",
            font=("Microsoft YaHei", 9, "bold"),
            fg=BG,
            bg=BLUE,
            activebackground=BLUE,
            relief="flat",
            bd=0,
            padx=12,
            pady=3,
            cursor="hand2",
            state="disabled",
            command=self._on_exec,
        )
        self.exec_btn.pack(side="right")

    def _build_bottom_tabs(self, parent):
        """底部标签页：命令结果 / 文件传输 / 部署"""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True, pady=(0, 4))

        # ── 标签1: 执行结果 ────────────────────────────────
        tab_result = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(tab_result, text="  执行结果  ")

        tk.Label(
            tab_result, text="执行结果", fg=DIM, bg=PANEL, font=("Microsoft YaHei", 9)
        ).pack(anchor="w")
        self.result_area = scrolledtext.ScrolledText(
            tab_result,
            font=("Consolas", 9),
            fg=TEXT,
            bg=BG,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            height=10,
            state="disabled",
        )
        self.result_area.pack(fill="both", expand=True, pady=(2, 0))

        # ── 标签2: 文件传输 ────────────────────────────────
        tab_file = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(tab_file, text="  文件传输  ")
        self._build_file_tab(tab_file)

        # ── 标签3: 部署 ──────────────────────────────────
        tab_deploy = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(tab_deploy, text="  远程部署  ")
        self._build_deploy_tab(tab_deploy)

        # ── 标签4: 命令历史 ──────────────────────────────
        tab_hist = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(tab_hist, text="  命令历史  ")
        self._build_history_tab(tab_hist)

    def _build_file_tab(self, parent):
        """文件传输标签页"""
        f = tk.LabelFrame(
            parent,
            text="文件传输",
            font=("Microsoft YaHei", 10, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=12,
            pady=8,
            relief="flat",
            bd=0,
        )
        f.pack(fill="both", expand=True, padx=4, pady=4)

        # ── 上传 ───────────────────────────────────────
        upload = tk.LabelFrame(
            f,
            text="上传文件到设备",
            font=("Microsoft YaHei", 9, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=8,
            pady=6,
            relief="flat",
            bd=0,
        )
        upload.pack(fill="x", pady=(0, 6))

        row1 = tk.Frame(upload, bg=PANEL)
        row1.pack(fill="x", pady=2)
        tk.Label(
            row1,
            text="本地文件",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=10,
            anchor="e",
        ).pack(side="left")
        self.local_file_var = tk.StringVar(value="")
        tk.Entry(
            row1,
            textvariable=self.local_file_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 9),
            relief="flat",
            width=40,
            bd=0,
        ).pack(side="left", padx=4)
        tk.Button(
            row1,
            text="浏览...",
            font=("Microsoft YaHei", 8),
            fg=TEXT,
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=8,
            cursor="hand2",
            command=self._browse_file,
        ).pack(side="left")

        row2 = tk.Frame(upload, bg=PANEL)
        row2.pack(fill="x", pady=2)
        tk.Label(
            row2,
            text="目标路径",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=10,
            anchor="e",
        ).pack(side="left")
        self.remote_path_var = tk.StringVar(value="/opt/ai-nas/")
        tk.Entry(
            row2,
            textvariable=self.remote_path_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 9),
            relief="flat",
            width=40,
            bd=0,
        ).pack(side="left", padx=4)
        self.upload_btn = tk.Button(
            row2,
            text="上传",
            font=("Microsoft YaHei", 9, "bold"),
            fg=BG,
            bg=GREEN,
            activebackground=GREEN,
            relief="flat",
            bd=0,
            padx=10,
            pady=2,
            cursor="hand2",
            state="disabled",
            command=self._on_upload,
        )
        self.upload_btn.pack(side="right")

        # ── 下载 ───────────────────────────────────────
        download = tk.LabelFrame(
            f,
            text="从设备下载文件",
            font=("Microsoft YaHei", 9, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=8,
            pady=6,
            relief="flat",
            bd=0,
        )
        download.pack(fill="x")

        row3 = tk.Frame(download, bg=PANEL)
        row3.pack(fill="x", pady=2)
        tk.Label(
            row3,
            text="设备文件路径",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=10,
            anchor="e",
        ).pack(side="left")
        self.download_path_var = tk.StringVar(value="/opt/ai-nas/config.yaml")
        tk.Entry(
            row3,
            textvariable=self.download_path_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 9),
            relief="flat",
            width=40,
            bd=0,
        ).pack(side="left", padx=4)
        self.download_btn = tk.Button(
            row3,
            text="下载",
            font=("Microsoft YaHei", 9, "bold"),
            fg=BG,
            bg=BLUE,
            activebackground=BLUE,
            relief="flat",
            bd=0,
            padx=10,
            pady=2,
            cursor="hand2",
            state="disabled",
            command=self._on_download,
        )
        self.download_btn.pack(side="right")

        # ── 文件日志 ───────────────────────────────────
        self.file_log = scrolledtext.ScrolledText(
            f,
            font=("Consolas", 8),
            fg=TEXT,
            bg=BG,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            height=5,
            state="disabled",
        )
        self.file_log.pack(fill="x", pady=(6, 0))

    def _build_deploy_tab(self, parent):
        """部署标签页"""
        f = tk.LabelFrame(
            parent,
            text="远程部署 AI-NAS",
            font=("Microsoft YaHei", 10, "bold"),
            fg=TEXT,
            bg=PANEL,
            padx=12,
            pady=8,
            relief="flat",
            bd=0,
        )
        f.pack(fill="both", expand=True, padx=4, pady=4)

        row1 = tk.Frame(f, bg=PANEL)
        row1.pack(fill="x", pady=2)
        tk.Label(
            row1,
            text="版本",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=10,
            anchor="e",
        ).pack(side="left")
        self.deploy_version_var = tk.StringVar(value="latest")
        tk.Entry(
            row1,
            textvariable=self.deploy_version_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 9),
            relief="flat",
            width=20,
            bd=0,
        ).pack(side="left", padx=4)
        tk.Label(
            row1,
            text="（latest 或具体版本号）",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 8),
        ).pack(side="left")

        row2 = tk.Frame(f, bg=PANEL)
        row2.pack(fill="x", pady=2)
        tk.Label(
            row2,
            text="安装路径",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=10,
            anchor="e",
        ).pack(side="left")
        self.install_path_var = tk.StringVar(value="/opt/ai-nas")
        tk.Entry(
            row2,
            textvariable=self.install_path_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 9),
            relief="flat",
            width=40,
            bd=0,
        ).pack(side="left", padx=4)

        row3 = tk.Frame(f, bg=PANEL)
        row3.pack(fill="x", pady=2)
        tk.Label(
            row3,
            text="下载地址",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            width=10,
            anchor="e",
        ).pack(side="left")
        self.deploy_url_var = tk.StringVar(value="")
        tk.Entry(
            row3,
            textvariable=self.deploy_url_var,
            fg=TEXT,
            bg=PANEL2,
            insertbackground=TEXT,
            font=("Consolas", 9),
            relief="flat",
            width=40,
            bd=0,
        ).pack(side="left", padx=4)
        tk.Label(
            row3,
            text="（留空则用内置包）",
            fg=DIM,
            bg=PANEL,
            font=("Microsoft YaHei", 8),
        ).pack(side="left")

        # 选项
        row4 = tk.Frame(f, bg=PANEL)
        row4.pack(fill="x", pady=(4, 2))
        self.backup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row4,
            variable=self.backup_var,
            text="部署前备份",
            fg=TEXT,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            selectcolor=PANEL2,
            activebackground=PANEL,
            activeforeground=TEXT,
            anchor="w",
        ).pack(side="left", padx=(0, 12))
        self.restart_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row4,
            variable=self.restart_var,
            text="部署后重启服务",
            fg=TEXT,
            bg=PANEL,
            font=("Microsoft YaHei", 9),
            selectcolor=PANEL2,
            activebackground=PANEL,
            activeforeground=TEXT,
            anchor="w",
        ).pack(side="left")

        # 进度条
        self.deploy_progress = ttk.Progressbar(f, length=400, mode="determinate")
        self.deploy_progress.pack(fill="x", pady=(6, 2))
        self.deploy_status_label = tk.Label(
            f, text="", fg=DIM, bg=PANEL, font=("Microsoft YaHei", 9)
        )
        self.deploy_status_label.pack(anchor="w")

        # 按钮
        row5 = tk.Frame(f, bg=PANEL)
        row5.pack(fill="x", pady=(4, 0))
        self.deploy_btn = tk.Button(
            row5,
            text="开始部署",
            font=("Microsoft YaHei", 10, "bold"),
            fg=BG,
            bg=GREEN,
            activebackground=GREEN,
            relief="flat",
            bd=0,
            padx=16,
            pady=4,
            cursor="hand2",
            state="disabled",
            command=self._on_deploy,
        )
        self.deploy_btn.pack(side="left")
        tk.Button(
            row5,
            text="停止部署",
            font=("Microsoft YaHei", 9),
            fg=TEXT,
            bg=BORDER,
            activebackground=BORDER,
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            state="disabled",
            command=self._on_stop_deploy,
        ).pack(side="left", padx=4)

    def _build_history_tab(self, parent):
        """命令历史标签页"""
        # 工具栏
        toolbar = tk.Frame(parent, bg=PANEL)
        toolbar.pack(fill="x", padx=8, pady=6)

        tk.Label(
            toolbar,
            text="历史命令",
            fg=TEXT,
            bg=PANEL,
            font=("Microsoft YaHei", 9, "bold"),
        ).pack(side="left")

        tk.Button(
            toolbar,
            text="重新执行",
            font=("Microsoft YaHei", 8),
            fg=TEXT,
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._on_rerun_cmd,
        ).pack(side="right")

        tk.Button(
            toolbar,
            text="CSV导出",
            font=("Microsoft YaHei", 8),
            fg=TEXT,
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._on_export_csv,
        ).pack(side="right", padx=4)

        tk.Button(
            toolbar,
            text="趋势图",
            font=("Microsoft YaHei", 8),
            fg="#2196F3",
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._on_show_trend,
        ).pack(side="right", padx=4)

        tk.Button(
            toolbar,
            text="清空历史",
            font=("Microsoft YaHei", 8),
            fg=RED,
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._on_clear_history,
        ).pack(side="right", padx=4)

        tk.Button(
            toolbar,
            text="保存到文件",
            font=("Microsoft YaHei", 8),
            fg=TEXT,
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._on_save_history,
        ).pack(side="right")

        # 历史列表
        cols = ("time", "device", "command", "status")
        self.history_tree = ttk.Treeview(
            parent, columns=cols, show="headings", height=8
        )
        self.history_tree.heading("time", text="时间")
        self.history_tree.heading("device", text="设备")
        self.history_tree.heading("command", text="命令")
        self.history_tree.heading("status", text="状态")
        self.history_tree.column("time", width=80, anchor="w")
        self.history_tree.column("device", width=150, anchor="w")
        self.history_tree.column("command", width=350, anchor="w")
        self.history_tree.column("status", width=60, anchor="center")
        self.history_tree.bind("<Double-Button-1>", lambda e: self._on_rerun_cmd())

        sb = ttk.Scrollbar(parent, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=sb.set)

        self.history_tree.pack(
            side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8)
        )
        sb.pack(side="right", fill="y", padx=(0, 8), pady=(0, 8))

        # 加载历史
        self._history: List[Dict] = _load_history()
        self._reload_history_tree()

    def _reload_history_tree(self):
        """重新加载历史到 Treeview"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for entry in reversed(self._history[-200:]):
            ts = entry.get("time", "")
            device = entry.get("device", "")
            cmd = entry.get("command", "")
            status = entry.get("status", "pending")
            status_text = (
                "✅" if status == "success" else "❌" if status == "failed" else "⏳"
            )
            self.history_tree.insert("", "end", values=(ts, device, cmd, status_text))

    def _add_history(
        self, device: str, cmd: str, status: str = "pending", response: str = ""
    ):
        """添加历史记录"""
        entry = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "device": device,
            "command": cmd,
            "status": status,
            "response": response,
        }
        self._history.append(entry)
        _save_history(self._history)
        self._reload_history_tree()

    def _on_rerun_cmd(self):
        """重新执行选中的历史命令"""
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一条历史记录", parent=self.parent)
            return
        values = self.history_tree.item(selected[0], "values")
        cmd = values[2]
        device = values[1]

        # 切换到命令标签页并填入
        try:
            self.notebook.select(0)
        except Exception:
            pass
        self.cmd_var.set(cmd)

        # 如果设备在线，执行
        if device in [d.get("device_id") for d in self.devices]:
            self._selected_devices = {
                d: d == device for d in [d.get("device_id") for d in self.devices]
            }
            self.selected_device = device
            self._on_exec()
        else:
            messagebox.showwarning(
                "提示", f"设备 {device} 当前不在线", parent=self.parent
            )

    def _on_export_csv(self):
        """导出历史为 CSV"""
        if not self._history:
            messagebox.showwarning("提示", "没有历史记录", parent=self.parent)
            return

        path = filedialog.asksaveasfilename(
            parent=self.parent,
            initialfile="relay_history.csv",
            title="导出 CSV",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
        )
        if not path:
            return

        try:
            import csv

            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["时间", "设备", "命令", "状态", "耗时"])
                for h in self._history:
                    w.writerow(
                        [
                            h.get("time", ""),
                            h.get("device", ""),
                            h.get("command", ""),
                            h.get("status", ""),
                            h.get("duration_ms", ""),
                        ]
                    )
            messagebox.showinfo(
                "成功",
                f"已导出 {len(self._history)} 条记录到\n{path}",
                parent=self.parent,
            )
        except Exception as e:
            messagebox.showerror("失败", str(e), parent=self.parent)

    def _on_show_trend(self):
        """显示趋势图"""
        if not self._history:
            messagebox.showwarning("提示", "没有历史记录", parent=self.parent)
            return

        # 统计每日命令数
        from collections import Counter

        dates = Counter(
            h.get("time", "").split()[0] for h in self._history if h.get("time")
        )
        if not dates:
            messagebox.showwarning("提示", "无法解析历史时间", parent=self.parent)
            return

        # 弹出趋势窗口
        top = tk.Toplevel(self.parent)
        top.title("命令执行趋势")
        top.geometry("500x300")
        top.configure(bg=PANEL)

        tk.Label(
            top,
            text="最近7天命令执行统计",
            fg=TEXT,
            bg=PANEL,
            font=("Microsoft YaHei", 12, "bold"),
        ).pack(pady=10)

        # Canvas 绘图
        c = tk.Canvas(top, width=460, height=180, bg=BG, highlightthickness=0)
        c.pack(pady=10)

        # 排序日期
        sorted_dates = sorted(dates.keys())[-7:]
        max_cnt = max(dates.values()) or 1

        c_width, c_height = 460, 170
        bar_width = c_width // max(len(sorted_dates), 1) - 20

        for i, d in enumerate(sorted_dates):
            cnt = dates[d]
            bar_h = int(cnt / max_cnt * (c_height - 30))
            x = 20 + i * (bar_width + 20)
            y = c_height - bar_h

            # 绘制柱状
            c.create_rectangle(
                x, y, x + bar_width, c_height, fill="#2196F3", outline=""
            )
            c.create_text(
                x + bar_width // 2,
                y - 10,
                text=str(cnt),
                fill=TEXT,
                font=("Microsoft YaHei", 9),
            )
            c.create_text(
                x + bar_width // 2,
                c_height + 10,
                text=d[-5:],
                fill=DIM,
                font=("Microsoft YaHei", 7),
            )

        tk.Button(
            top,
            text="关闭",
            font=("Microsoft YaHei", 9),
            fg=TEXT,
            bg=PANEL2,
            activebackground=PANEL2,
            relief="flat",
            bd=0,
            padx=20,
            pady=4,
            command=top.destroy,
        ).pack(pady=10)

    def _on_register_device(self):
        """打开设备注册对话框（T3）"""
        if not self.relay.connected and not self.relay.token:
            messagebox.showwarning("提示", "请先连接 Relay Server", parent=self.parent)
            return

        # 创建设备类型下拉数据
        device_types = [
            ("Jetson (NVIDIA)", "jetson"),
            ("RK3588 (Rockchip)", "rk3588"),
            ("Synology NAS", "synology"),
            ("QNAP NAS", "qnap"),
            ("SOPHON (算能)", "sophon"),
            ("Raspberry Pi 5", "pi5"),
            ("通用设备", "generic"),
        ]

        # 注册对话框
        reg = tk.Toplevel(self.parent)
        reg.title("注册新设备")
        reg.geometry("520x420")
        reg.configure(bg=BG)
        reg.resizable(False, False)
        reg.transient(self.parent)
        reg.grab_set()

        # 标题
        tk.Label(
            reg,
            text="注册新设备",
            font=("Microsoft YaHei", 14, "bold"),
            fg=ACCENT,
            bg=BG,
        ).pack(pady=(16, 4))

        tk.Label(
            reg,
            text="在目标设备上运行 installer.py 完成接入",
            font=("Microsoft YaHei", 9),
            fg=DIM,
            bg=BG,
        ).pack()

        form = tk.Frame(reg, bg=PANEL, padx=20, pady=16)
        form.pack(fill="x", padx=20, pady=12)

        # 设备名称
        row_name = tk.Frame(form, bg=PANEL)
        row_name.pack(fill="x", pady=4)
        tk.Label(
            row_name, text="设备名称", fg=DIM, bg=PANEL, font=("", 9), width=10, anchor="e"
        ).pack(side="left")
        name_var = tk.StringVar(value=os.environ.get("COMPUTERNAME", "My NAS"))
        tk.Entry(
            row_name, textvariable=name_var, fg=TEXT, bg=PANEL2, font=("Microsoft YaHei", 10),
            relief="flat", width=28, bd=0, insertbackground=TEXT
        ).pack(side="left", padx=4)

        # 设备类型
        row_type = tk.Frame(form, bg=PANEL)
        row_type.pack(fill="x", pady=4)
        tk.Label(
            row_type, text="设备类型", fg=DIM, bg=PANEL, font=("", 9), width=10, anchor="e"
        ).pack(side="left")
        type_var = tk.StringVar(value="jetson")
        type_combo = ttk.Combobox(
            row_type, textvariable=type_var, values=[v for _, v in device_types],
            state="readonly", width=26, font=("Microsoft YaHei", 10)
        )
        type_combo.pack(side="left", padx=4)

        # 说明
        note = tk.Label(
            reg,
            text="注册成功后，将 agent_key 复制到目标设备，运行：",
            fg=DIM, bg=BG, font=("Microsoft YaHei", 9)
        )
        note.pack(pady=(0, 4))

        cmd_text = (
            "sudo python3 installer.py --auto \\\\\n"
            '  --relay-url "ws://120.77.249.3:18888" \\\\\n'
            "  --device-name <你的名称> \\\\\n"
            "  --device-type <类型> \\\\\n"
            "  --install-service"
        )
        cmd_label = tk.Label(
            reg, text=cmd_text, font=("Consolas", 9), fg=TEXT, bg=BG, justify="left"
        )
        cmd_label.pack()

        # agent_key 显示区
        result_frame = tk.LabelFrame(
            reg, text="注册结果", font=("", 9, "bold"), fg=TEXT, bg=PANEL,
            padx=12, pady=8, relief="flat", bd=0
        )
        result_frame.pack(fill="x", padx=20, pady=(12, 4))

        key_var = tk.StringVar(value="（注册后将显示 agent_key）")
        key_entry = tk.Entry(
            result_frame, textvariable=key_var, fg=DIM, bg=PANEL2,
            font=("Consolas", 10), relief="flat", bd=0, insertbackground=TEXT
        )
        key_entry.pack(fill="x")
        key_entry.configure(state="readonly")

        status_label = tk.Label(
            reg, text="", fg=DIM, bg=BG, font=("Microsoft YaHei", 8)
        )
        status_label.pack(pady=(2, 8))

        # 按钮行
        btn_row = tk.Frame(reg, bg=BG)
        btn_row.pack(pady=(0, 16))

        def do_register():
            """执行注册"""
            name = name_var.get().strip()
            dtype = type_var.get()
            status_label.config(text="正在注册...", fg=DIM)

            def _reg():
                ok, result = self.relay.register_agent(
                    label=name, device_type=dtype, device_name=name
                )

                def _ui():
                    if ok:
                        key_var.set(result)
                        key_entry.configure(fg=GREEN)
                        status_label.config(
                            text=f"✅ 注册成功！请将上方 agent_key 填入 installer.py 命令",
                            fg=GREEN
                        )
                        reg_btn.configure(state="disabled")
                        copy_btn.configure(state="normal")
                        # 自动复制
                        reg.clipboard_clear()
                        reg.clipboard_append(result)
                    else:
                        status_label.config(text=f"❌ 注册失败: {result}", fg=RED)
                        key_var.set("（注册失败）")
                        key_entry.configure(fg=RED)

                reg.after(0, _ui)

            threading.Thread(target=_reg, daemon=True).start()

        reg_btn = tk.Button(
            btn_row,
            text="注册",
            font=("Microsoft YaHei", 10, "bold"),
            fg=BG, bg=GREEN, activebackground=GREEN,
            relief="flat", bd=0, padx=20, pady=6, cursor="hand2",
            command=do_register
        )
        reg_btn.pack(side="left", padx=4)

        def copy_key():
            key = key_var.get()
            if key and "（" not in key:
                reg.clipboard_clear()
                reg.clipboard_append(key)
                status_label.config(text="已复制到剪贴板", fg=GREEN)

        copy_btn = tk.Button(
            btn_row,
            text="复制 agent_key",
            font=("Microsoft YaHei", 9),
            fg=TEXT, bg=PANEL2, activebackground=PANEL2,
            relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
            state="disabled", command=copy_key
        )
        copy_btn.pack(side="left", padx=4)

        tk.Button(
            btn_row,
            text="关闭",
            font=("Microsoft YaHei", 9),
            fg=TEXT, bg=BORDER, activebackground=BORDER,
            relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
            command=reg.destroy
        ).pack(side="left", padx=4)

    def _on_clear_history(self):
        """清空历史"""
        if messagebox.askyesno("确认", "确定清空所有命令历史？", parent=self.parent):
            self._history = []
            _save_history(self._history)
            self._reload_history_tree()

    def _on_save_history(self):
        """保存历史到文件"""
        path = filedialog.asksaveasfilename(
            parent=self.parent,
            initialfile="relay_history.json",
            title="保存历史记录",
            filetypes=[("JSON", "*.json"), ("Text", "*.txt")],
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self._history, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("成功", f"已保存到 {path}", parent=self.parent)
            except Exception as e:
                messagebox.showerror("失败", str(e), parent=self.parent)

    def _set_cmd(self, cmd: str):
        """设置快捷命令"""
        self.cmd_var.set(cmd)

    def _on_connect(self):
        """连接按钮"""
        url = self.url_var.get().strip()
        user = self.user_var.get().strip()
        password = self.pass_var.get()

        if not url:
            messagebox.showwarning(
                "提示", "请输入 Relay Server URL", parent=self.parent
            )
            return

        self.connect_btn.config(state="disabled", text="连接中...")
        self.log("正在连接 Relay Server...")

        def do_connect():
            # 1. 登录
            ok, msg = self.relay.login(url, user, password)
            if not ok:
                self.queue.put(("login_failed", msg))
                return

            self.queue.put(("login_ok", msg))

            # 2. 连接 WebSocket
            ok2, msg2 = self.relay.connect_ws(
                lambda m: self.queue.put(("ws_message", m))
            )
            if not ok2:
                self.queue.put(("ws_failed", msg2))

        threading.Thread(target=do_connect, daemon=True).start()

    def _on_disconnect(self):
        """断开按钮"""
        self.relay.close()
        self._update_disconnected()
        self.log("已断开连接")

    def _on_refresh(self):
        """刷新设备列表"""
        if not HAS_REQUESTS:
            return

        try:
            resp = requests.get(
                f"{self.relay.url}/api/v1/devices",
                headers={"Authorization": f"Bearer {self.relay.token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.devices = data.get("devices", [])
                # 重新初始化选择状态（保留之前选中的）
                self._selected_devices = {
                    d.get("device_id", ""): self._selected_devices.get(
                        d.get("device_id", ""), False
                    )
                    for d in self.devices
                }
                self._update_device_list()
                self.log(f"获取到 {len(self.devices)} 个设备")
        except Exception as e:
            self.log(f"刷新失败: {e}")

    def _start_auto_refresh(self, interval_ms: int = 30000):
        """定时自动刷新设备列表（后台线程）"""

        def _loop():
            while self._auto_refresh_running:
                time.sleep(interval_ms / 1000)
                if self._auto_refresh_running:
                    self.queue.put(("auto_refresh", None))

        if self._auto_refresh_running:
            return
        self._auto_refresh_running = True
        threading.Thread(target=_loop, daemon=True).start()

    def _stop_auto_refresh(self):
        self._auto_refresh_running = False

    def _on_device_select(self, event=None):
        """更新已选设备（从 Treeview selection 同步到 _selected_devices）"""
        selected = self.device_tree.selection()
        # 重置全部选择状态
        for d in self._selected_devices:
            self._selected_devices[d] = False
        # 从 selection 恢复
        for item_id in selected:
            values = self.device_tree.item(item_id, "values")
            if len(values) >= 2:
                device_id = values[1]  # 列1 是 device_id
                self._selected_devices[device_id] = True

        # 单选时更新详情面板
        if len(selected) == 1:
            values = self.device_tree.item(selected[0], "values")
            self._update_detail_panel(values)
            self.selected_device = values[1]
            self.target_label.config(text=f"{values[2]} ({values[1][:20]}...)", fg=TEXT)
            self.exec_btn.config(state="normal")
            self.relay.subscribe(self.selected_device)
        else:
            self.selected_device = None
            self.target_label.config(text=f"（已选 {len(selected)} 台设备）", fg=ACCENT)
            self.exec_btn.config(state="disabled")
            self._clear_detail_panel()

        self._update_selection_label()
        self._update_batch_buttons()

    def _redraw_device_tree(self):
        """重新绘制设备列表（同设备信息）"""
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)

        for dev in self.devices:
            d_id = dev.get("device_id", "")
            name = dev.get("name", dev.get("hostname", "—"))
            dtype = dev.get("type", dev.get("device_type", "未知"))
            status = dev.get("status", "offline")
            online = dev.get("online_time", "")
            selected = self._selected_devices.get(d_id, False)
            check = "☑" if selected else "☐"

            self.device_tree.insert(
                "", "end", values=(check, d_id, name, dtype, status)
            )

    def _update_detail_panel(self, values: tuple):
        """更新设备详情面板"""
        self.detail_device_id.config(text=values[1], fg=TEXT)

        dev = next((d for d in self.devices if d.get("device_id") == values[1]), {})

        self.detail_rows["type"].config(text=values[3] if len(values) > 3 else "—")
        self.detail_rows["status"].config(
            text=values[4] if len(values) > 4 else "—", fg=GREEN
        )
        self.detail_rows["online_time"].config(text=dev.get("online_time", "—"))
        self.detail_rows["last_report"].config(text=dev.get("last_report_time", "—"))
        self.detail_rows["version"].config(
            text=dev.get("version", dev.get("ai_nas_version", "—"))
        )
        self.detail_rows["ip"].config(text=dev.get("ip", dev.get("local_ip", "—")))

    def _clear_detail_panel(self):
        """清空详情面板"""
        self.detail_device_id.config(text="—", fg=DIM)
        for lbl in self.detail_rows.values():
            lbl.config(text="—", fg=DIM)

    def _on_exec(self):
        """执行命令（单选或多选）"""
        selected = [d for d, v in self._selected_devices.items() if v]
        if not selected:
            messagebox.showwarning("提示", "请先选择设备", parent=self.parent)
            return

        cmd = self.cmd_var.get().strip()
        if not cmd:
            messagebox.showwarning("提示", "请输入命令", parent=self.parent)
            return

        # 批量执行时添加到历史
        for device_id in selected:
            self._add_history(device_id, cmd, "pending")

        self.log(f"\n=== 批量执行 ({len(selected)} 台) ===")
        self.log(f"> {cmd}")
        self.exec_btn.config(state="disabled", text="执行中...")

        ids = self.relay.batch_command(selected, cmd)
        if ids:
            self.log(f"已发送 {len(ids)} 个命令请求")
        else:
            self.log("发送失败: 未连接")
            self.exec_btn.config(state="normal", text="执行")

    def _browse_file(self):
        """浏览本地文件"""
        path = filedialog.askopenfilename(parent=self.parent)
        if path:
            self.local_file_var.set(path)

    def _on_upload(self):
        """上传文件到设备"""
        if not self.selected_device:
            messagebox.showwarning("提示", "请先选择设备", parent=self.parent)
            return

        local = self.local_file_var.get().strip()
        if not local or not os.path.exists(local):
            messagebox.showwarning("提示", "请选择有效的本地文件", parent=self.parent)
            return

        remote = self.remote_path_var.get().strip() or "/tmp/"
        self.file_log_write(
            f"上传: {os.path.basename(local)} → {remote}/{os.path.basename(local)}"
        )
        self.upload_btn.config(state="disabled", text="上传中...")

        file_id = self.relay.upload_file(self.selected_device, local, remote)
        if file_id:
            self.file_log_write(f"请求已发送: {file_id}")
        else:
            self.file_log_write("发送失败: 未连接")
            self.upload_btn.config(state="normal", text="上传")

    def _on_download(self):
        """从设备下载文件"""
        if not self.selected_device:
            messagebox.showwarning("提示", "请先选择设备", parent=self.parent)
            return

        remote = self.download_path_var.get().strip()
        if not remote:
            messagebox.showwarning("提示", "请输入设备上的文件路径", parent=self.parent)
            return

        save_path = filedialog.asksaveasfilename(
            parent=self.parent,
            initialfile=os.path.basename(remote),
            title="保存文件到...",
        )
        if not save_path:
            return

        freq_id = self.relay.request_file(self.selected_device, remote)
        if freq_id:
            self.file_log_write(f"下载请求已发送: {remote} → {save_path}")
            self._pending_downloads[freq_id] = save_path
        else:
            self.file_log_write("发送失败: 未连接")

    def _on_deploy(self):
        """发送部署指令"""
        if not self.selected_device:
            messagebox.showwarning("提示", "请先选择设备", parent=self.parent)
            return

        version = self.deploy_version_var.get().strip() or "latest"
        install_path = self.install_path_var.get().strip() or "/opt/ai-nas"
        url = self.deploy_url_var.get().strip()
        backup = self.backup_var.get()
        restart = self.restart_var.get()

        import uuid

        deployment_id = f"dep_{uuid.uuid4().hex[:12]}"

        self.deploy_progress["value"] = 0
        self.deploy_status_label.config(
            text=f"正在部署 v{version} 到 {self.selected_device}..."
        )
        self.deploy_btn.config(state="disabled", text="部署中...")

        ok = self.relay.deploy(
            self.selected_device,
            deployment_id,
            version=version,
            url=url or None,
            install_path=install_path,
            backup=backup,
            restart=restart,
        )

        if ok:
            self.file_log_write(f"部署请求已发送: {deployment_id}")
            self._pending_deploy = deployment_id
        else:
            self.file_log_write("发送失败: 未连接")
            self.deploy_btn.config(state="normal", text="开始部署")

    def _on_stop_deploy(self):
        """停止部署（发送命令让 Agent 中止）"""
        self.file_log_write("停止部署: 发送中断信号...")
        # Agent 不支持停止，只能记录
        self.deploy_status_label.config(text="Agent 不支持中途停止，请等待...")

    def file_log_write(self, msg: str):
        """写文件日志"""
        self.file_log.config(state="normal")
        self.file_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.file_log.see("end")
        self.file_log.config(state="disabled")

    def _update_device_list(self):
        """更新设备列表（重新绘制以显示选择状态）"""
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)

        for dev in self.devices:
            d_id = dev.get("device_id", "")
            name = dev.get("device_name", dev.get("hostname", "—"))
            dtype = dev.get("device_type", "未知")
            status = dev.get("status", "offline")
            status_text = "🟢 在线" if status == "online" else "⚪ 离线"
            selected = self._selected_devices.get(d_id, False)
            check = "☑" if selected else "☐"

            self.device_tree.insert(
                "", "end", values=(check, d_id, name, dtype, status_text)
            )

        self._update_selection_label()
        self._update_batch_buttons()

    def _update_connected(self):
        """更新连接状态"""
        self.status_label.config(text="已连接", fg=GREEN)
        self.connect_btn.config(state="disabled", text="已连接")
        self.disconnect_btn.config(state="normal")
        self.refresh_btn.config(state="normal")
        self.register_btn.config(state="normal")  # T3: 注册设备
        self.select_all_btn.config(state="normal")
        self._start_auto_refresh(interval_ms=30000)
        # 启用操作按钮
        try:
            self.upload_btn.config(state="normal")
            self.deploy_btn.config(state="normal")
            self.batch_deploy_btn.config(state="normal")
        except Exception:
            pass

    def _update_disconnected(self):
        """更新断开状态"""
        self._stop_auto_refresh()
        self.status_label.config(text="未连接", fg=DIM)
        self.connect_btn.config(state="normal", text="连接")
        self.disconnect_btn.config(state="disabled")
        self.refresh_btn.config(state="disabled")
        self.exec_btn.config(state="disabled")
        self.device_tree.delete(*self.device_tree.get_children())
        self.devices = []
        self._selected_devices = {}
        self._update_selection_label()
        # 禁用操作按钮
        try:
            self.upload_btn.config(state="disabled")
            self.download_btn.config(state="disabled")
            self.deploy_btn.config(state="disabled")
            self.batch_deploy_btn.config(state="disabled")
        except Exception:
            pass

    def log(self, msg: str):
        """日志"""
        self.result_area.config(state="normal")
        self.result_area.insert("end", msg + "\n")
        self.result_area.see("end")
        self.result_area.config(state="disabled")

    def _start_consumer(self):
        """消息消费者"""

        def consume():
            try:
                while True:
                    item = self.queue.get_nowait()
                    kind = item[0]

                    if kind == "login_ok":
                        self.log("登录成功")
                    elif kind == "login_failed":
                        self.log(f"登录失败: {item[1]}")
                        self._update_disconnected()
                    elif kind == "ws_failed":
                        self.log(f"WebSocket 连接失败: {item[1]}")
                        self._update_disconnected()
                    elif kind == "ws_message":
                        self._handle_ws_message(item[1])
                    elif kind == "auto_refresh":
                        if self.relay.connected:
                            self._on_refresh()
            except queue.Empty:
                pass

            self.parent.after(100, consume)

        self.parent.after(100, consume)

    def _handle_ws_message(self, msg: Dict):
        """处理 WebSocket 消息"""
        msg_type = msg.get("type")

        if msg_type == "connected":
            self._update_connected()
            self.log("WebSocket 已连接")
            # 自动刷新设备列表
            self._on_refresh()

        elif msg_type == "disconnected":
            self._update_disconnected()
            self.log("WebSocket 已断开")

        elif msg_type == "device_online":
            device_id = msg.get("device_id")
            self.log(f"设备上线: {device_id}")
            self._on_refresh()

        elif msg_type == "device_offline":
            device_id = msg.get("device_id")
            self.log(f"设备离线: {device_id}")
            self._on_refresh()

        elif msg_type == "response":
            payload = msg.get("payload", {})
            command_id = payload.get("command_id", "")
            device_id = msg.get("device_id", "")
            stdout = payload.get("stdout", "")
            stderr = payload.get("stderr", "")
            code = payload.get("code", -1)
            duration = payload.get("duration_ms", 0)
            success = code == 0

            self.log(f"\n执行完成 (exit={code}, {duration}ms)")
            if stdout:
                self.log(stdout)
            if stderr:
                self.log(f"[stderr] {stderr}")

            # 更新历史记录
            for entry in reversed(self._history):
                if (
                    entry.get("device") == device_id
                    and entry.get("status") == "pending"
                ):
                    entry["status"] = "success" if success else "failed"
                    break
            _save_history(self._history)
            self._reload_history_tree()

            # 更新 exec 按钮
            self.exec_btn.config(state="normal", text="执行")

        elif msg_type == "report":
            payload = msg.get("payload", {})
            score = payload.get("overall_score", 0)
            self.log(f"\n收到检测报告: 评分 {score}")

        elif msg_type == "log":
            payload = msg.get("payload", {})
            level = payload.get("level", "INFO")
            message = payload.get("message", "")
            self.log(f"[{level}] {message}")

        elif msg_type == "file_uploaded":
            payload = msg.get("payload", {})
            status = payload.get("status", "")
            file_id = payload.get("file_id", "")
            error = payload.get("error", "")
            if status == "uploaded":
                self.file_log_write(f"文件上传成功: {file_id}")
                self.upload_btn.config(state="normal", text="上传")
            else:
                self.file_log_write(f"文件上传失败: {error}")
                self.upload_btn.config(state="normal", text="上传")

        elif msg_type == "file_response":
            payload = msg.get("payload", {})
            freq_id = payload.get("file_request_id", "")
            error = payload.get("error", "")
            if error:
                self.file_log_write(f"文件下载失败: {error}")
                return

            import base64

            content_b64 = payload.get("content_base64", "")
            name = payload.get("name", "downloaded_file")
            save_path = self._pending_downloads.get(freq_id)
            if save_path and content_b64:
                try:
                    content = base64.b64decode(content_b64)
                    Path = __import__("pathlib").Path
                    Path(save_path).write_bytes(content)
                    self.file_log_write(
                        f"文件已保存: {save_path} ({len(content)} bytes)"
                    )
                except Exception as e:
                    self.file_log_write(f"保存失败: {e}")
            elif save_path:
                self.file_log_write(f"文件已保存（无内容）: {save_path}")

        elif msg_type == "deploy_progress":
            payload = msg.get("payload", {})
            device_id = msg.get("device_id", "")
            step = payload.get("step", "")
            progress = payload.get("progress", 0)
            message = payload.get("message", "")
            self.deploy_progress["value"] = progress
            self.deploy_status_label.config(text=f"[{step}] {message}")
            self.file_log_write(f"部署进度 {progress}%: {message}")

            # 批量部署进度
            if (
                device_id
                and hasattr(self, "_batch_deploy_results")
                and device_id in self._batch_deploy_results
            ):
                self._update_batch_deploy_progress(device_id, progress, step, message)

        elif msg_type == "deploy_result":
            payload = msg.get("payload", {})
            device_id = msg.get("device_id", "")
            success = payload.get("success", False)
            version = payload.get("version", "")
            result_msg = payload.get("message", "")
            duration = payload.get("duration_ms", 0)
            self.deploy_btn.config(state="normal", text="开始部署")

            # 批量部署结果
            if (
                device_id
                and hasattr(self, "_batch_deploy_results")
                and device_id in self._batch_deploy_results
            ):
                self._finish_batch_deploy(device_id, success, version, result_msg)

            if success:
                self.deploy_status_label.config(
                    text=f"部署成功! v{version} (耗时 {duration}ms)"
                )
                self.file_log_write(f"部署成功: v{version}，耗时 {duration}ms")
                messagebox.showinfo(
                    "部署成功", f"AI-NAS v{version} 部署成功！", parent=self.parent
                )
            else:
                self.deploy_status_label.config(text=f"部署失败: {result_msg}")
                self.file_log_write(f"部署失败: {result_msg}")
                messagebox.showerror("部署失败", result_msg, parent=self.parent)

        elif msg_type == "error":
            payload = msg.get("payload", {})
            self.log(f"错误: {payload.get('message', '')}")

    def run(self):
        """运行"""
        self.parent.mainloop()


def show_relay_dialog(parent: tk.Tk = None):
    """显示 Relay 对话框"""
    if not HAS_WEBSOCKETS or not HAS_REQUESTS:
        messagebox.showerror(
            "缺少依赖",
            "需要安装依赖:\n  pip install websockets requests",
            parent=parent,
        )
        return

    dialog = RelayDialog(parent)
    dialog.run()


if __name__ == "__main__":
    show_relay_dialog()
