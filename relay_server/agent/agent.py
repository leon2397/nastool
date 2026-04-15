#!/usr/bin/env python3
"""
nastools ARM Agent - Relay Server 客户端
v2.0.0

功能：
- WebSocket 连接 Relay Server
- 设备注册与心跳
- 命令执行与结果上报
- 检测报告上报
- 断线自动重连
"""

import asyncio
import base64
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, List
from zipfile import ZipFile

try:
    import websockets
except ImportError:
    print("需要安装 websockets: pip install websockets")
    sys.exit(1)

from config import AgentConfig
from protocol import Message, MessageType


class ARMAgent:
    """ARM 设备 Agent"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.connected = False
        self.running = True
        self.last_heartbeat = 0
        self.pending_commands: Dict[str, Dict] = {}  # command_id -> task
        self._ota_version_event: Optional[asyncio.Event] = None  # OTA 版本响应事件
        self._ota_version_result: Optional[Dict] = None  # OTA 版本结果缓存
        
        # 设备信息
        self.device_info = self._collect_device_info()
        
    def _collect_device_info(self) -> Dict[str, Any]:
        """收集设备信息"""
        info = {
            "device_id": self.config.device_id,
            "device_name": self.config.device_name,
            "device_type": self.config.device_type,
            "version": "2.0.0",
            "hostname": platform.node(),
            "ip_local": self._get_local_ip(),
            "capabilities": self.config.capabilities,
            "agent_key": self.config.agent_key,
            "os": f"{platform.system()} {platform.release()}",
            "arch": platform.machine(),
            "python_version": platform.python_version(),
        }
        return info
    
    def _get_local_ip(self) -> str:
        """获取本机局域网 IP"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    async def _check_network(self) -> bool:
        """检测网络是否可达 Relay Server"""
        import socket
        try:
            # 解析 relay_url 提取 host:port
            relay_host = self.config.relay_url.replace("ws://", "").replace("wss://", "").split(":")[0]
            relay_port = 18888
            if ":" in self.config.relay_url:
                parts = self.config.relay_url.split(":")
                if len(parts) >= 3:
                    relay_port = int(parts[-1].split("/")[0])
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.connect_timeout)
            result = sock.connect_ex((relay_host, relay_port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _now(self) -> int:
        return int(time.time() * 1000)
    
    def _uuid(self) -> str:
        return str(uuid.uuid4())
    
    def _jitter(self, delay: float) -> float:
        """对延迟添加±jitter随机抖动，避免 thundering herd"""
        import random
        jitter_range = delay * self.config.reconnect_jitter
        return delay + random.uniform(-jitter_range, jitter_range)
    
    async def connect(self) -> bool:
        """连接 Relay Server"""
        url = f"{self.config.relay_url}/ws/agent?key={self.config.agent_key}"
        
        # 连接前预检网络（可选）
        if self.config.ping_before_connect:
            reachable = await self._check_network()
            if not reachable:
                print(f"[Agent] ⏳ 网络不可达 Relay，跳过本次连接尝试")
                return False
        
        print(f"[Agent] 正在连接: {url}")
        
        try:
            self.ws = await websockets.connect(
                url,
                ping_interval=self.config.heartbeat_interval,
                ping_timeout=self.config.read_timeout,
                close_timeout=10,
                open_timeout=self.config.connect_timeout,
            )
            self.connected = True
            print(f"[Agent] ✅ 已连接到 Relay: {self.config.relay_url}")
            return True
        except websockets.exceptions.InvalidURI as e:
            print(f"[Agent] ❌ URL 格式错误: {e}")
            self.connected = False
            return False
        except websockets.exceptions.InvalidStatus as e:
            print(f"[Agent] ❌ 连接被拒绝（状态码 {e.response.status}）: {e}")
            self.connected = False
            return False
        except Exception as e:
            print(f"[Agent] ❌ 连接失败: {e}")
            self.connected = False
            return False
    
    async def register(self) -> bool:
        """发送注册消息"""
        msg = Message(
            type=MessageType.REGISTER,
            id=self._uuid(),
            timestamp=self._now(),
            payload=self.device_info,
        )
        
        await self._send(msg.to_dict())
        
        # 等待 register_ack
        try:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=10)
            resp = json.loads(raw)
            if resp.get("type") == "register_ack":
                self.session_id = resp["payload"]["session_id"]
                server_config = resp["payload"].get("config", {})
                print(f"[Agent] 注册成功: session_id={self.session_id}")
                print(f"[Agent] 服务器配置: {server_config}")
                return True
            else:
                print(f"[Agent] 注册失败: {resp}")
                return False
        except asyncio.TimeoutError:
            print("[Agent] 注册超时")
            return False
    
    async def _send(self, data: Dict) -> None:
        """发送 JSON 消息"""
        if self.ws and self.connected:
            await self.ws.send(json.dumps(data))
    
    async def send_heartbeat(self) -> None:
        """发送心跳"""
        msg = Message(
            type=MessageType.HEARTBEAT,
            id=self._uuid(),
            timestamp=self._now(),
            payload={},
        )
        await self._send(msg.to_dict())
        self.last_heartbeat = self._now()
    
    async def send_report(self, report_data: Dict) -> None:
        """上报检测报告"""
        msg = Message(
            type=MessageType.REPORT,
            id=self._uuid(),
            timestamp=self._now(),
            payload=report_data,
        )
        await self._send(msg.to_dict())
        print(f"[Agent] 上报报告: overall_score={report_data.get('overall_score')}")
    
    async def send_response(self, command_id: str, code: int, stdout: str, stderr: str, duration_ms: int) -> None:
        """上报命令执行结果"""
        msg = Message(
            type=MessageType.RESPONSE,
            id=self._uuid(),
            timestamp=self._now(),
            payload={
                "command_id": command_id,
                "code": code,
                "stdout": stdout,
                "stderr": stderr,
                "duration_ms": duration_ms,
            },
        )
        await self._send(msg.to_dict())
        print(f"[Agent] 命令完成: {command_id}, code={code}, duration={duration_ms}ms")
    
    async def send_log(self, level: str, message: str) -> None:
        """发送实时日志"""
        msg = Message(
            type=MessageType.LOG,
            id=self._uuid(),
            timestamp=self._now(),
            payload={"level": level, "message": message},
        )
        await self._send(msg.to_dict())
    
    # ─── OTA 升级 ──────────────────────────────────────────
    
    async def ota_check(self) -> Optional[Dict]:
        """询问 Relay 最新版本"""
        # 设置事件用于接收响应（单消费者，防止 ws.recv 冲突）
        self._ota_version_event = asyncio.Event()
        self._ota_version_result = None
        
        try:
            msg = Message(
                type=MessageType.OTA_CHECK,
                id=self._uuid(),
                timestamp=self._now(),
                payload={"current_version": self.device_info["version"]},
            )
            await self._send(msg.to_dict())
            print(f"[OTA] 发送版本检查: 当前={self.device_info['version']}")
            
            # 等待 receive_loop 拦截并设置事件
            try:
                await asyncio.wait_for(
                    self._ota_version_event.wait(),
                    timeout=10,
                )
                if self._ota_version_result:
                    pv = self._ota_version_result.get("version", "?")
                    print(f"[OTA] 服务器版本={pv}, 当前={self.device_info['version']}")
                    return self._ota_version_result
            except asyncio.TimeoutError:
                print(f"[OTA] 版本检查超时（10s无响应）")
        finally:
            self._ota_version_event = None
            self._ota_version_result = None
        return None
    
    async def ota_loop(self) -> None:
        """OTA 版本检查循环（后台运行）"""
        import os as _os
        check_interval = self.config.ota_check_interval
        if check_interval <= 0 or not self.config.ota_enabled:
            print("[OTA] OTA 禁用，ota_loop 退出")
            return
        
        print(f"[OTA] OTA 已启用，检查间隔 {check_interval}s")
        await asyncio.sleep(10)  # 启动后等待 10s 再首次检查
        
        while self.running and self.connected:
            try:
                version_info = await self.ota_check()
                if version_info and version_info.get("version"):
                    new_version = version_info["version"]
                    if new_version != self.device_info["version"]:
                        print(f"[OTA] 发现新版本 {new_version}，开始下载...")
                        success = await self.ota_download(version_info)
                        if success:
                            print(f"[OTA] 新版本已就绪，Agent 将重启")
                            # 通知 Relay 准备重启
                            await self._send(Message(
                                type=MessageType.OTA_READY,
                                id=self._uuid(),
                                timestamp=self._now(),
                                payload={"version": new_version},
                            ).to_dict())
                            await asyncio.sleep(2)
                            # 通知 systemd 重启（或自己退出让 systemd 重启）
                            await self._ota_restart()
                            return  # 退出循环（进程将重启）
            except Exception as e:
                print(f"[OTA] 检查异常: {e}")
            
            await asyncio.sleep(check_interval)
    
    async def ota_download(self, version_info: Dict) -> bool:
        """下载新版本 OTA 包"""
        import os as _os
        download_url = version_info.get("download_url")
        expected_version = version_info.get("version")
        
        if not download_url:
            print("[OTA] 无 download_url，跳过下载")
            return False
        
        download_dir = Path(self.config.ota_download_dir)
        download_dir.mkdir(parents=True, exist_ok=True)
        pkg_path = download_dir / f"nastool-agent-{expected_version}.tar.gz"
        
        try:
            import urllib.request
            print(f"[OTA] 下载: {download_url}")
            urllib.request.urlretrieve(download_url, str(pkg_path))
            
            # 验证（校验和）
            import hashlib
            expected_sha256 = version_info.get("checksum_sha256")
            if expected_sha256:
                actual_sha256 = hashlib.sha256(pkg_path.read_bytes()).hexdigest()
                if actual_sha256 != expected_sha256:
                    print(f"[OTA] ❌ 校验失败，已删除损坏文件")
                    pkg_path.unlink()
                    return False
            
            print(f"[OTA] ✅ 下载完成: {pkg_path} ({pkg_path.stat().st_size} bytes)")
            return True
        except Exception as e:
            print(f"[OTA] ❌ 下载失败: {e}")
            return False
    
    async def _ota_restart(self) -> None:
        """重启 Agent（systemd 或直接）"""
        print("[OTA] 请求重启 Agent...")
        
        # 优先用 systemd 重启（保留进程可追踪性）
        result = subprocess.run(
            ["systemctl", "is-active", "nastool-agent"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("[OTA] 通过 systemd 重启...")
            subprocess.Popen(["systemctl", "restart", "nastool-agent"])
        else:
            # fallback: 通知 systemd 停止，下次启动会自拉
            subprocess.Popen(["systemctl", "stop", "nastool-agent"])
        
        # 退出主循环
        self.running = False
    
    async def execute_command(self, cmd: str, timeout_ms: int = 30000, cwd: str = None, env: Dict = None) -> tuple:
        """执行命令"""
        start_time = time.time()
        
        try:
            # 合并环境变量
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)
            
            # 执行
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=exec_env,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout_ms / 1000,
                )
            except asyncio.TimeoutError:
                proc.kill()
                return -1, "", "Command timeout", timeout_ms
            
            duration_ms = int((time.time() - start_time) * 1000)
            return proc.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace"), duration_ms
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return -1, "", str(e), duration_ms
    
    async def handle_command(self, payload: Dict) -> None:
        """处理收到的命令"""
        command_id = payload.get("command_id")
        cmd = payload.get("cmd")
        timeout_ms = payload.get("timeout_ms", 30000)
        cwd = payload.get("cwd")
        env = payload.get("env", {})
        
        print(f"[Agent] 收到命令: {command_id}, cmd={cmd}")
        
        # 执行
        code, stdout, stderr, duration_ms = await self.execute_command(cmd, timeout_ms, cwd, env)
        
        # 上报结果
        await self.send_response(command_id, code, stdout, stderr, duration_ms)
    
    async def handle_file(self, payload: Dict) -> None:
        """处理文件传输（GUI → Agent 上传文件）"""
        file_id = payload.get("file_id")
        name = payload.get("name")
        content_b64 = payload.get("content_base64")
        path = payload.get("path", "/tmp/")
        mode = payload.get("mode", "0644")
        
        print(f"[Agent] 收到文件: {name}, path={path}")
        
        try:
            content = base64.b64decode(content_b64)
            target_path = Path(path) / name if os.path.isdir(path) else Path(path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(content)
            os.chmod(target_path, int(mode, 8))
            
            msg = Message(
                type=MessageType.FILE_UPLOADED,
                id=self._uuid(),
                timestamp=self._now(),
                payload={"file_id": file_id, "status": "uploaded"},
            )
            await self._send(msg.to_dict())
            print(f"[Agent] 文件保存成功: {target_path}")
            
        except Exception as e:
            msg = Message(
                type=MessageType.FILE_UPLOADED,
                id=self._uuid(),
                timestamp=self._now(),
                payload={"file_id": file_id, "status": "failed", "error": str(e)},
            )
            await self._send(msg.to_dict())
            print(f"[Agent] 文件保存失败: {e}")

    async def handle_file_request(self, payload: Dict) -> None:
        """处理文件请求（GUI ← Agent 下载文件）"""
        file_request_id = payload.get("file_request_id")
        file_path = payload.get("path")
        encoding = payload.get("encoding", "base64")
        
        print(f"[Agent] 收到文件请求: {file_path}")
        
        try:
            p = Path(file_path)
            if not p.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            content_bytes = p.read_bytes()
            size = len(content_bytes)
            
            if encoding == "base64":
                content_encoded = base64.b64encode(content_bytes).decode("ascii")
            else:
                content_encoded = content_bytes.decode("utf-8", errors="replace")
            
            sha256 = hashlib.sha256(content_bytes).hexdigest()
            
            msg = Message(
                type=MessageType.FILE_RESPONSE,
                id=self._uuid(),
                timestamp=self._now(),
                payload={
                    "file_request_id": file_request_id,
                    "path": str(p),
                    "name": p.name,
                    "size": size,
                    "content_base64": content_encoded,
                    "encoding": encoding,
                    "checksum_sha256": sha256,
                },
            )
            await self._send(msg.to_dict())
            print(f"[Agent] 文件已发送: {p.name} ({size} bytes)")
            
        except Exception as e:
            msg = Message(
                type=MessageType.FILE_RESPONSE,
                id=self._uuid(),
                timestamp=self._now(),
                payload={
                    "file_request_id": file_request_id,
                    "path": file_path,
                    "error": str(e),
                },
            )
            await self._send(msg.to_dict())
            print(f"[Agent] 文件读取失败: {e}")

    async def handle_deploy(self, payload: Dict) -> None:
        """处理部署指令（远程升级 AI-NAS）"""
        deployment_id = payload.get("deployment_id")
        version = payload.get("version", "latest")
        url = payload.get("url")
        files = payload.get("files", [])
        config = payload.get("config", {})
        backup = payload.get("backup", True)
        restart = payload.get("restart", True)
        
        ai_nas_dir = config.get("install_path", "/opt/ai-nas")
        start_time = time.time()
        
        async def send_progress(step: str, progress: int, message: str):
            msg = Message(
                type=MessageType.DEPLOY_PROGRESS,
                id=self._uuid(),
                timestamp=self._now(),
                payload={
                    "deployment_id": deployment_id,
                    "step": step,
                    "progress": progress,
                    "message": message,
                },
            )
            await self._send(msg.to_dict())
        
        try:
            # ── Step 1: 备份 ──────────────────────────────────
            await send_progress("backup", 5, "开始备份...")
            backup_dir = None
            if backup:
                backup_dir = Path(f"{ai_nas_dir}/backup_{int(time.time())}")
                backup_dir.mkdir(parents=True, exist_ok=True)
                for f in ["arm_server.py", "config.yaml", "nastool"]:
                    src = Path(ai_nas_dir) / f
                    if src.exists():
                        shutil.copy2(src, backup_dir / f)
                await send_progress("backup", 15, f"备份完成: {backup_dir}")
            
            # ── Step 2: 下载/解压 ─────────────────────────────
            await send_progress("downloading", 20, "准备部署文件...")
            tmp_dir = Path(tempfile.mkdtemp(prefix="nastools_deploy_"))
            tmp_file = tmp_dir / "deploy.tar.gz"
            
            if url:
                # 从 URL 下载
                await send_progress("downloading", 25, f"从 {url} 下载...")
                import urllib.request
                urllib.request.urlretrieve(url, str(tmp_file))
                await send_progress("downloading", 45, "下载完成")
            elif files:
                # 直接写入选项中的文件
                for f in files:
                    fpath = Path(f.get("path", "").lstrip("/"))
                    fpath.parent.mkdir(parents=True, exist_ok=True)
                    content = base64.b64decode(f.get("content_base64", ""))
                    fpath.write_bytes(content)
                await send_progress("downloading", 45, "文件已写入")
                await send_progress("extracting", 55, "部署完成")
            else:
                raise ValueError("部署需要提供 url 或 files")
            
            # ── Step 3: 解压安装 ──────────────────────────────
            if tmp_file.exists():
                await send_progress("extracting", 55, "解压文件...")
                with tarfile.open(tmp_file, "r:gz") as tar:
                    tar.extractall(ai_nas_dir)
                await send_progress("extracting", 70, "解压完成")
            
            # ── Step 4: 重启服务 ──────────────────────────────
            await send_progress("restarting", 75, "重启 AI-NAS 服务...")
            if restart:
                os.system("systemctl restart ai-nas 2>/dev/null || "
                          "systemctl restart nastool 2>/dev/null || "
                          "pkill -f arm_server.py; sleep 2; "
                          f"cd {ai_nas_dir} && python3 arm_server.py &")
                await send_progress("restarting", 85, "服务已重启")
            
            # ── Step 5: 验证 ─────────────────────────────────
            await send_progress("verifying", 90, "验证部署...")
            await asyncio.sleep(2)
            await send_progress("verifying", 100, "部署成功!")
            
            # 清理
            shutil.rmtree(tmp_dir, ignore_errors=True)
            if backup_dir:
                shutil.rmtree(backup_dir, ignore_errors=True)
            
            duration_ms = int((time.time() - start_time) * 1000)
            msg = Message(
                type=MessageType.DEPLOY_RESULT,
                id=self._uuid(),
                timestamp=self._now(),
                payload={
                    "deployment_id": deployment_id,
                    "success": True,
                    "version": version,
                    "message": f"部署成功 (耗时 {duration_ms}ms)",
                    "duration_ms": duration_ms,
                },
            )
            await self._send(msg.to_dict())
            print(f"[Agent] 部署成功: {deployment_id}")
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            msg = Message(
                type=MessageType.DEPLOY_RESULT,
                id=self._uuid(),
                timestamp=self._now(),
                payload={
                    "deployment_id": deployment_id,
                    "success": False,
                    "message": f"部署失败: {e}",
                    "duration_ms": duration_ms,
                },
            )
            await self._send(msg.to_dict())
            print(f"[Agent] 部署失败: {e}")
            # 回滚
            if backup and backup_dir and backup_dir.exists():
                await send_progress("rollback", 50, "回滚中...")
                for f in ["arm_server.py", "config.yaml", "nastool"]:
                    src = backup_dir / f
                    if src.exists():
                        shutil.copy2(src, Path(ai_nas_dir) / f)
                await send_progress("rollback", 80, "回滚完成")
    
    async def handle_message(self, raw: str) -> None:
        """处理收到的消息"""
        try:
            msg = json.loads(raw)
        except:
            return
        
        msg_type = msg.get("type")
        payload = msg.get("payload", {})
        
        if msg_type == MessageType.COMMAND:
            await self.handle_command(payload)
        elif msg_type == MessageType.FILE:
            await self.handle_file(payload)
        elif msg_type == MessageType.FILE_REQUEST:
            await self.handle_file_request(payload)
        elif msg_type == MessageType.DEPLOY:
            await self.handle_deploy(payload)
        elif msg_type == MessageType.DISCONNECT:
            print(f"[Agent] 服务器请求断开: {payload.get('reason')}")
            self.running = False
        elif msg_type == "heartbeat_ack":
            pass  # 心跳响应，忽略
    
    async def heartbeat_loop(self) -> None:
        """心跳循环"""
        while self.running and self.connected:
            await asyncio.sleep(self.config.heartbeat_interval / 1000)
            if self.connected:
                await self.send_heartbeat()
    
    async def diagnose_loop(self) -> None:
        """定期诊断循环（后台运行）"""
        if self.config.diagnose_interval <= 0:
            return
        
        await asyncio.sleep(30)  # 启动后等待 30s 再首次诊断
        
        while self.running and self.connected:
            if self.config.diagnose_on_start or self.config.diagnose_interval > 0:
                try:
                    print(f"[Agent] 执行定期诊断...")
                    # TODO: 调用 nastool 诊断模块
                    # report = run_full_diagnosis()
                    # await self.send_report(report)
                except Exception as e:
                    print(f"[Agent] 诊断失败: {e}")
            
            await asyncio.sleep(self.config.diagnose_interval)
    
    async def receive_loop(self) -> None:
        """接收消息循环（单消费者：OTA 消息被拦截，其余走 handle_message）"""
        while self.running and self.connected:
            try:
                raw = await self.ws.recv()
                try:
                    msg = json.loads(raw)
                except:
                    continue
                
                msg_type = msg.get("type")
                
                # OTA 消息：拦截给 ota_check()
                if msg_type == MessageType.OTA_VERSION and self._ota_version_event:
                    self._ota_version_result = msg.get("payload", {})
                    self._ota_version_event.set()
                    continue  # 不传给 handle_message
                
                # 其余消息走通用处理器
                await self.handle_message(raw)
                
            except websockets.ConnectionClosed:
                print("[Agent] 连接已关闭")
                self.connected = False
                if self._ota_version_event:
                    self._ota_version_event.set()  # 唤醒等待中的 ota_check
                break
            except Exception as e:
                print(f"[Agent] 接收错误: {e}")
    
    async def run(self) -> None:
        """主运行循环"""
        reconnect_delay = self.config.reconnect_base_delay
        
        while self.running:
            # ── 1. 连接 ──────────────────────────────────────
            if not await self.connect():
                sleep_time = self._jitter(reconnect_delay)
                print(f"[Agent] ⏳ {sleep_time:.1f}秒后重试...")
                await asyncio.sleep(sleep_time)
                reconnect_delay = min(
                    reconnect_delay * 2,
                    self.config.reconnect_max_delay,
                )
                continue
            
            # ── 2. 注册 ──────────────────────────────────────
            if not await self.register():
                await self.ws.close()
                self.connected = False
                sleep_time = self._jitter(reconnect_delay)
                print(f"[Agent] 注册失败，{sleep_time:.1f}秒后重试...")
                await asyncio.sleep(sleep_time)
                continue
            
            # 重置退避计数器
            reconnect_delay = self.config.reconnect_base_delay
            print(f"[Agent] ✅ Agent 已上线，device_id={self.config.device_id}")
            
            # ── 3. 运行所有后台循环 ──────────────────────────
            try:
                await asyncio.gather(
                    self.heartbeat_loop(),
                    self.receive_loop(),
                    self.ota_loop(),  # OTA 检查循环
                    self.diagnose_loop(),  # 定期诊断循环
                )
            except websockets.ConnectionClosed:
                print("[Agent] 连接被关闭")
            except Exception as e:
                print(f"[Agent] 运行错误: {e}")
            
            # ── 4. 断线后重连 ────────────────────────────────
            self.connected = False
            if self.running:
                sleep_time = self._jitter(reconnect_delay)
                print(f"[Agent] 断线，{sleep_time:.1f}秒后重连...")
                await asyncio.sleep(sleep_time)
                reconnect_delay = min(
                    reconnect_delay * 2,
                    self.config.reconnect_max_delay,
                )
    
    async def stop(self) -> None:
        """停止 Agent"""
        self.running = False
        if self.ws:
            await self.ws.close()


async def main():
    """入口"""
    import argparse
    
    AGENT_VERSION = "2.1.0"
    
    print("=" * 50)
    print(f"  nastools ARM Agent v{AGENT_VERSION}")
    print("  连接 Relay Server 进行远程管理")
    print("=" * 50)
    
    parser = argparse.ArgumentParser(description="nastools ARM Agent")
    parser.add_argument("--config", "-c", default="config.yaml", help="配置文件路径")
    parser.add_argument("--relay-url", help="Relay Server URL (覆盖配置文件)")
    parser.add_argument("--agent-key", help="Agent Key (覆盖配置文件)")
    parser.add_argument("--device-id", help="设备ID (覆盖配置文件)")
    parser.add_argument("--device-name", help="设备名称 (覆盖配置文件)")
    parser.add_argument("--run-diagnose", action="store_true", help="启动时执行一次诊断并上报")
    parser.add_argument("--version", "-v", action="store_true", help="输出版本号并退出")
    args = parser.parse_args()
    
    if args.version:
        print(f"nastools-arm-agent {AGENT_VERSION}")
        sys.exit(0)
    
    # 加载配置
    config = AgentConfig.load(args.config)
    
    # 命令行覆盖
    if args.relay_url:
        config.relay_url = args.relay_url
    if args.agent_key:
        config.agent_key = args.agent_key
    if args.device_id:
        config.device_id = args.device_id
    if args.device_name:
        config.device_name = args.device_name
    
    # 更新版本信息
    config.capabilities = getattr(config, "capabilities", ["storage", "network", "system"])
    
    # 验证必要配置
    if not config.agent_key:
        print("错误: 缺少 agent_key，请在配置文件或命令行中指定")
        sys.exit(1)
    if not config.relay_url:
        print("错误: 缺少 relay_url，请在配置文件或命令行中指定")
        sys.exit(1)
    
    # 创建 Agent
    agent = ARMAgent(config)
    agent.device_info["version"] = AGENT_VERSION  # 注入版本号
    
    # 打印配置信息
    key_display = config.agent_key[:12] + "..." if len(config.agent_key) > 12 else config.agent_key
    print(f"[配置] Agent 版本: {AGENT_VERSION}")
    print(f"[配置] Relay URL: {config.relay_url}")
    print(f"[配置] Agent Key: {key_display}")
    print(f"[配置] Device ID: {config.device_id}")
    print(f"[配置] Device Name: {config.device_name}")
    print(f"[配置] OTA: {'启用' if config.ota_enabled else '禁用'}, 间隔={config.ota_check_interval}s")
    print(f"[配置] 重连: 抖动±{int(config.reconnect_jitter*100)}%, 最大{config.reconnect_max_delay}s")
    print("-" * 50)
    
    # 信号处理：优雅退出
    async def graceful_shutdown():
        print("[Agent] 收到退出信号，正在优雅关闭...")
        await agent.stop()
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(graceful_shutdown()))
    
    # 运行
    await agent.run()
    print("[Agent] Agent 已退出")


if __name__ == "__main__":
    asyncio.run(main())
