#!/usr/bin/env python3
"""
nastool-agent.py - NASTool Remote Agent v1.1

Deploys on target devices and connects to Relay Server via WebSocket.
Allows remote diagnosis, command execution, and file transfer.

Usage:
    # Test mode (connect 10 seconds)
    python3 nastool_agent.py --relay http://120.77.249.3:18888 --key YOUR_AGENT_KEY --device-id nvidia-123 --once
    
    # Production mode (run forever)
    python3 nastool_agent.py --relay http://120.77.249.3:18888 --key YOUR_AGENT_KEY --device-id nvidia-123
    
    # Background mode
    nohup python3 nastool_agent.py --relay http://120.77.249.3:18888 --key YOUR_AGENT_KEY --device-id nvidia-123 > agent.log 2>&1 &

    # Using environment variables
    export NASTOOL_RELAY_URL=http://120.77.249.3:18888
    export NASTOOL_AGENT_KEY=YOUR_AGENT_KEY
    export NASTOOL_DEVICE_ID=nvidia-123
    python3 nastool_agent.py
"""

import sys
import os
import json
import time
import argparse
import platform
import subprocess
import threading
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import websocket
except ImportError:
    logger.info("Installing websocket-client...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client", "-q"])
    import websocket


class NASToolAgent:
    """NASTool Remote Agent"""

    # 命令白名单
    ALLOWED_COMMANDS = {
        "diagnose", "info", "ping",
        "ls", "df", "free", "uptime", "uname",
        "nvidia-smi", "ip", "ifconfig", "hostname"
    }

    def __init__(self, relay_url, agent_key, device_id, device_name="", device_type="", group="default", 
                 command_whitelist=None, require_secure=False):
        self.relay_url = relay_url
        # 支持wss://协议
        if relay_url.startswith("https://"):
            self.relay_ws = relay_url.replace("https://", "wss://") + "/ws/agent"
        else:
            self.relay_ws = relay_url.replace("http://", "ws://") + "/ws/agent"
        self.agent_key = agent_key
        self.device_id = device_id
        self.device_name = device_name or device_id
        self.device_type = device_type or "unknown"
        self.group = group
        self.session_id = None
        self.heartbeat_ms = 30000
        self._stop = threading.Event()
        self.ws = None
        self.command_whitelist = command_whitelist or self.ALLOWED_COMMANDS
        self.require_secure = require_secure

    def get_device_info(self):
        """Collect device information"""
        info = {
            "hostname": platform.node(),
            "os": platform.system(),
            "os_version": platform.version(),
            "arch": platform.machine(),
            "python_version": platform.python_version(),
            "agent_version": "1.1.0"
        }
        try:
            s = __import__("socket").socket(__import__("socket").AF_INET, __import__("socket").SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            info["ip_local"] = s.getsockname()[0]
            s.close()
        except Exception as e:
            logger.warning(f"Failed to get local IP: {e}")
            info["ip_local"] = "127.0.0.1"
        
        # 设备类型检测
        try:
            # 检测NVIDIA设备
            r = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used", "--format=csv,noheader,nounits"], 
                              capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split("\n")[0].split(",")
                info["gpu_name"] = parts[0].strip() if len(parts) > 0 else ""
                info["gpu_driver"] = parts[1].strip() if len(parts) > 1 else ""
                info["gpu_mem_total"] = parts[2].strip() if len(parts) > 2 else ""
                info["gpu_mem_used"] = parts[3].strip() if len(parts) > 3 else ""
                if not self.device_type or self.device_type == "unknown":
                    self.device_type = "nvidia"
        except Exception as e:
            logger.debug(f"Failed to get GPU info: {e}")
        
        # 检测其他设备类型
        if not self.device_type or self.device_type == "unknown":
            try:
                # 检测Rockchip设备
                if os.path.exists("/proc/device-tree/compatible"):
                    with open("/proc/device-tree/compatible", "r") as f:
                        content = f.read().lower()
                        if "rockchip" in content or "rk3" in content:
                            self.device_type = "rockchip"
                # 检测树莓派
                elif os.path.exists("/proc/device-tree/model"):
                    with open("/proc/device-tree/model", "r") as f:
                        content = f.read().lower()
                        if "raspberry pi" in content:
                            self.device_type = "raspberry"
            except Exception as e:
                logger.debug(f"Failed to detect device type: {e}")
        
        info["device_type"] = self.device_type
        return info

    def _run_check(self, name, cmd):
        """Run a shell command and return result dict"""
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return {"check_id": name, "status": "ok" if r.returncode == 0 else "error", 
                    "stdout": r.stdout[:500], "stderr": r.stderr[:500], "exit_code": r.returncode}
        except Exception as e:
            logger.error(f"Error running check {name}: {e}")
            return {"check_id": name, "status": "error", "message": str(e)}

    def run_diagnosis(self):
        """Run local diagnosis checks"""
        checks = []
        
        # 根据设备类型调整命令
        if self.device_type == "nvidia":
            checks.append(self._run_check("cpu", "cat /proc/cpuinfo | head -5; echo '---'; nproc; echo '---'; uptime"))
            checks.append(self._run_check("memory", "free -h"))
            checks.append(self._run_check("disk", "df -h /"))
            checks.append(self._run_check("gpu", "nvidia-smi 2>/dev/null || echo 'No GPU'"))
            checks.append(self._run_check("network", "ip addr show 2>/dev/null || ifconfig 2>/dev/null || hostname -I"))
            checks.append(self._run_check("os", "uname -a; cat /etc/os-release 2>/dev/null | head -5"))
        elif self.device_type == "rockchip":
            checks.append(self._run_check("cpu", "cat /proc/cpuinfo | head -5; echo '---'; nproc; echo '---'; uptime"))
            checks.append(self._run_check("memory", "free -h"))
            checks.append(self._run_check("disk", "df -h /"))
            checks.append(self._run_check("gpu", "echo 'Rockchip GPU'"))
            checks.append(self._run_check("network", "ip addr show 2>/dev/null || ifconfig 2>/dev/null || hostname -I"))
            checks.append(self._run_check("os", "uname -a; cat /etc/os-release 2>/dev/null | head -5"))
        else:
            # 默认检查
            checks.append(self._run_check("cpu", "cat /proc/cpuinfo | head -5; echo '---'; nproc; echo '---'; uptime"))
            checks.append(self._run_check("memory", "free -h"))
            checks.append(self._run_check("disk", "df -h /"))
            checks.append(self._run_check("network", "ip addr show 2>/dev/null || ifconfig 2>/dev/null || hostname -I"))
            checks.append(self._run_check("os", "uname -a; cat /etc/os-release 2>/dev/null | head -5"))
        
        return checks

    def _send(self, msg):
        """Send JSON message"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            try:
                self.ws.send(json.dumps(msg))
                return True
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                return False
        return False

    def _on_open(self, ws):
        logger.info("Connected to Relay Server")
        # Send registration
        info = self.get_device_info()
        self._send({
            "type": "register",
            "agent_key": self.agent_key,
            "data": {
                "device_id": self.device_id,
                "device_name": self.device_name,
                "device_type": self.device_type,
                "group": self.group,
                "version": "1.1.0",
                "capabilities": json.dumps(["diagnosis", "command", "file"]),
                **info
            }
        })
        logger.info(f"Registration sent: {self.device_id}")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")
            payload = data.get("payload", {})

            # Handle registration response
            if msg_type == "agent:register":
                self.session_id = payload.get("session_id", "")
                config = payload.get("config", {})
                self.heartbeat_ms = config.get("heartbeat_interval", 30000)
                logger.info(f"Registered! session={self.session_id[:16]}")

            # Handle heartbeat ping
            elif msg_type == "agent:ping" or msg_type == "ping":
                self._send({"type": "agent:pong", "session_id": self.session_id})

            # Handle commands
            elif msg_type == "command":
                self._handle_command(data)

            # Handle disconnect request
            elif msg_type == "disconnect":
                logger.info("Disconnect requested")
                self._stop.set()

            else:
                logger.warning(f"Unknown message: {msg_type}")

        except Exception as e:
            logger.error(f"Message error: {e}")

    def _handle_command(self, data):
        """Handle incoming command"""
        payload = data.get("payload", {})
        command_id = payload.get("command_id", "")
        cmd = payload.get("cmd", "")
        timeout_ms = payload.get("timeout_ms", 30000)

        logger.info(f"Command: {cmd[:80]} (timeout={timeout_ms}ms)")

        result = {"type": "command_result", "command_id": command_id, "session_id": self.session_id}

        try:
            if cmd == "diagnose":
                checks = self.run_diagnosis()
                result["status"] = "success"
                result["data"] = {"checks": checks, "device_info": self.get_device_info()}
            elif cmd == "info":
                result["status"] = "success"
                result["data"] = self.get_device_info()
            elif cmd == "ping":
                result["status"] = "success"
                result["data"] = {"pong": True, "timestamp": time.time()}
            else:
                # 检查命令是否在白名单中
                cmd_name = cmd.split()[0] if cmd else ""
                if cmd_name not in self.command_whitelist:
                    result["status"] = "error"
                    result["error"] = f"Command not allowed: {cmd_name}"
                    logger.warning(f"Attempt to execute unauthorized command: {cmd}")
                else:
                    # 执行白名单内的命令
                    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, 
                                     timeout=min(timeout_ms / 1000, 300))
                    result["status"] = "success" if r.returncode == 0 else "error"
                    result["data"] = {"stdout": r.stdout[:5000], "stderr": r.stderr[:2000], 
                                     "exit_code": r.returncode}

        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = "Command timed out"
            logger.error(f"Command timed out: {cmd}")
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Error executing command: {e}")

        self._send(result)
        logger.info(f"Result sent: {result['status']}")

    def _on_error(self, ws, error):
        logger.error(f"Error: {str(error)[:200]}")

    def _on_close(self, ws, code, reason):
        logger.info(f"Disconnected (code={str(code)})")

    def start(self):
        """Start agent (blocking)"""
        url = "%s?key=%s" % (self.relay_ws, self.agent_key)
        logger.info("Starting NASTool Agent")
        logger.info(f"Device: {self.device_id} ({self.device_type})")
        logger.info(f"Relay:  {self.relay_url}")
        logger.info(f"WebSocket: {self.relay_ws}")
        logger.info(f"Key:     {self.agent_key[:10]}...{self.agent_key[-6:]}")
        logger.info("")

        retry_count = 0
        max_retries = 10

        while not self._stop.is_set() and retry_count < max_retries:
            try:
                ws = websocket.WebSocketApp(url, on_open=self._on_open, 
                                           on_message=self._on_message, 
                                           on_error=self._on_error, 
                                           on_close=self._on_close)
                self.ws = ws
                ws.run_forever(ping_interval=self.heartbeat_ms / 1000, ping_timeout=10)
            except websocket.WebSocketConnectionClosedException:
                logger.info("Connection closed, reconnecting in 5s...")
                retry_count += 1
            except Exception as e:
                logger.error(f"Error: {str(e)[:100]}, reconnecting in 5s...")
                retry_count += 1
            self._stop.wait(5)
        
        if retry_count >= max_retries:
            logger.error("Max retry attempts reached, stopping agent")

    def start_test(self, timeout=10):
        """Start agent in test mode (auto-stop after timeout)"""
        logger.info(f"TEST MODE - will disconnect after {timeout}s")

        def run():
            self.start()

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=timeout)
        self._stop.set()
        logger.info("Test complete")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="NASTool Remote Agent v1.1")
    parser.add_argument("--relay", help="Relay Server URL")
    parser.add_argument("--key", help="Agent Key (from /keys/generate)")
    parser.add_argument("--device-id", help="Unique device ID")
    parser.add_argument("--device-name", default="", help="Human-readable name")
    parser.add_argument("--device-type", default="", help="Device type (nvidia/rk3588/jetson/nas)")
    parser.add_argument("--group", default="test", help="Device group")
    parser.add_argument("--once", action="store_true", help="Test mode: connect, register, disconnect")
    parser.add_argument("--secure", action="store_true", help="Require secure connection (wss://)")
    args = parser.parse_args()

    # 从环境变量读取配置
    relay_url = args.relay or os.environ.get("NASTOOL_RELAY_URL")
    agent_key = args.key or os.environ.get("NASTOOL_AGENT_KEY")
    device_id = args.device_id or os.environ.get("NASTOOL_DEVICE_ID")
    device_name = args.device_name or os.environ.get("NASTOOL_DEVICE_NAME", "")
    device_type = args.device_type or os.environ.get("NASTOOL_DEVICE_TYPE", "")
    group = args.group or os.environ.get("NASTOOL_GROUP", "test")

    # 验证必要参数
    if not relay_url:
        logger.error("Relay URL is required (--relay or NASTOOL_RELAY_URL)")
        sys.exit(1)
    if not agent_key:
        logger.error("Agent Key is required (--key or NASTOOL_AGENT_KEY)")
        sys.exit(1)
    if not device_id:
        logger.error("Device ID is required (--device-id or NASTOOL_DEVICE_ID)")
        sys.exit(1)

    agent = NASToolAgent(
        relay_url=relay_url,
        agent_key=agent_key,
        device_id=device_id,
        device_name=device_name,
        device_type=device_type,
        group=group,
        require_secure=args.secure
    )

    if args.once:
        agent.start_test(timeout=10)
    else:
        agent.start()


if __name__ == "__main__":
    main()
