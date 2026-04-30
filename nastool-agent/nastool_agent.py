#!/usr/bin/env python3
"""
nastool-agent.py - NASTool Remote Agent v1.0

Deploys on target devices and connects to Relay Server via WebSocket.
Allows remote diagnosis, command execution, and file transfer.

Usage:
    # Test mode (connect 10 seconds)
    python3 nastool_agent.py --relay http://120.77.249.3:18888 --key YOUR_AGENT_KEY --device-id nvidia-123 --once
    
    # Production mode (run forever)
    python3 nastool_agent.py --relay http://120.77.249.3:18888 --key YOUR_AGENT_KEY --device-id nvidia-123
    
    # Background mode
    nohup python3 nastool_agent.py --relay http://120.77.249.3:18888 --key YOUR_AGENT_KEY --device-id nvidia-123 > agent.log 2>&1 &
"""

import sys
import os
import json
import time
import argparse
import platform
import subprocess
import threading

try:
    import websocket
except ImportError:
    print("Installing websocket-client...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client", "-q"])
    import websocket


class NASToolAgent:
    """NASTool Remote Agent"""

    def __init__(self, relay_url, agent_key, device_id, device_name="", device_type="", group="default"):
        self.relay_url = relay_url
        self.relay_ws = relay_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws/agent"
        self.agent_key = agent_key
        self.device_id = device_id
        self.device_name = device_name or device_id
        self.device_type = device_type or "unknown"
        self.group = group
        self.session_id = None
        self.heartbeat_ms = 30000
        self._stop = threading.Event()
        self.ws = None

    def get_device_info(self):
        """Collect device information"""
        info = {
            "hostname": platform.node(),
            "os": platform.system(),
            "os_version": platform.version(),
            "arch": platform.machine(),
            "python_version": platform.python_version(),
        }
        try:
            s = __import__("socket").socket(__import__("socket").AF_INET, __import__("socket").SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            info["ip_local"] = s.getsockname()[0]
            s.close()
        except Exception:
            info["ip_local"] = "127.0.0.1"
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split("\n")[0].split(",")
                info["gpu_name"] = parts[0].strip() if len(parts) > 0 else ""
                info["gpu_driver"] = parts[1].strip() if len(parts) > 1 else ""
                info["gpu_mem_total"] = parts[2].strip() if len(parts) > 2 else ""
                info["gpu_mem_used"] = parts[3].strip() if len(parts) > 3 else ""
        except Exception:
            pass
        return info

    def _run_check(self, name, cmd):
        """Run a shell command and return result dict"""
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return {"check_id": name, "status": "ok" if r.returncode == 0 else "error", "stdout": r.stdout[:500], "stderr": r.stderr[:500], "exit_code": r.returncode}
        except Exception as e:
            return {"check_id": name, "status": "error", "message": str(e)}

    def run_diagnosis(self):
        """Run local diagnosis checks"""
        checks = []
        checks.append(self._run_check("cpu", "cat /proc/cpuinfo | head -5; echo '---'; nproc; echo '---'; uptime"))
        checks.append(self._run_check("memory", "free -h"))
        checks.append(self._run_check("disk", "df -h /"))
        checks.append(self._run_check("gpu", "nvidia-smi 2>/dev/null || echo 'No GPU'"))
        checks.append(self._run_check("network", "ip addr show 2>/dev/null || ifconfig 2>/dev/null || hostname -I"))
        checks.append(self._run_check("os", "uname -a; cat /etc/os-release 2>/dev/null | head -5"))
        return checks

    def _send(self, msg):
        """Send JSON message"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            self.ws.send(json.dumps(msg))

    def _on_open(self, ws):
        print("[Agent] Connected to Relay Server")
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
                "version": "1.0.0",
                "capabilities": json.dumps(["diagnosis", "command", "file"]),
                **info
            }
        })
        print("[Agent] Registration sent: %s" % self.device_id)

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
                print("[Agent] Registered! session=%s" % self.session_id[:16])

            # Handle heartbeat ping
            elif msg_type == "agent:ping" or msg_type == "ping":
                self._send({"type": "agent:pong", "session_id": self.session_id})

            # Handle commands
            elif msg_type == "command":
                self._handle_command(data)

            # Handle disconnect request
            elif msg_type == "disconnect":
                print("[Agent] Disconnect requested")
                self._stop.set()

            else:
                print("[Agent] Unknown message: %s" % msg_type)

        except Exception as e:
            print("[Agent] Message error: %s" % e)

    def _handle_command(self, data):
        """Handle incoming command"""
        payload = data.get("payload", {})
        command_id = payload.get("command_id", "")
        cmd = payload.get("cmd", "")
        timeout_ms = payload.get("timeout_ms", 30000)

        print("[Agent] Command: %s (timeout=%sms)" % (cmd[:80], timeout_ms))

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
                # Execute arbitrary shell command
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=min(timeout_ms / 1000, 300))
                result["status"] = "success" if r.returncode == 0 else "error"
                result["data"] = {"stdout": r.stdout[:5000], "stderr": r.stderr[:2000], "exit_code": r.returncode}

        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = "Command timed out"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        self._send(result)
        print("[Agent] Result sent: %s" % result["status"])

    def _on_error(self, ws, error):
        print("[Agent] Error: %s" % str(error)[:200])

    def _on_close(self, ws, code, reason):
        print("[Agent] Disconnected (code=%s)" % str(code))

    def start(self):
        """Start agent (blocking)"""
        url = "%s?key=%s" % (self.relay_ws, self.agent_key)
        print("[Agent] Starting NASTool Agent")
        print("[Agent] Device: %s (%s)" % (self.device_id, self.device_type))
        print("[Agent] Relay:  %s" % self.relay_url)
        print("[Agent] Key:     %s...%s" % (self.agent_key[:10], self.agent_key[-6:]))
        print()

        while not self._stop.is_set():
            try:
                ws = websocket.WebSocketApp(url, on_open=self._on_open, on_message=self._on_message, on_error=self._on_error, on_close=self._on_close)
                self.ws = ws
                ws.run_forever(ping_interval=self.heartbeat_ms / 1000, ping_timeout=10)
            except websocket.WebSocketConnectionClosedException:
                print("[Agent] Connection closed, reconnecting in 5s...")
            except Exception as e:
                print("[Agent] Error: %s, reconnecting in 5s..." % str(e)[:100])
            self._stop.wait(5)

    def start_test(self, timeout=10):
        """Start agent in test mode (auto-stop after timeout)"""
        print("[Agent] TEST MODE - will disconnect after %ss" % timeout)

        def run():
            self.start()

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=timeout)
        self._stop.set()
        print("[Agent] Test complete")


def main():
    parser = argparse.ArgumentParser(description="NASTool Remote Agent v1.0")
    parser.add_argument("--relay", required=True, help="Relay Server URL")
    parser.add_argument("--key", required=True, help="Agent Key (from /keys/generate)")
    parser.add_argument("--device-id", required=True, help="Unique device ID")
    parser.add_argument("--device-name", default="", help="Human-readable name")
    parser.add_argument("--device-type", default="", help="Device type (nvidia/rk3588/jetson/nas)")
    parser.add_argument("--group", default="test", help="Device group")
    parser.add_argument("--once", action="store_true", help="Test mode: connect, register, disconnect")
    args = parser.parse_args()

    agent = NASToolAgent(
        relay_url=args.relay,
        agent_key=args.key,
        device_id=args.device_id,
        device_name=args.device_name,
        device_type=args.device_type,
        group=args.group,
    )

    if args.once:
        agent.start_test(timeout=10)
    else:
        agent.start()


if __name__ == "__main__":
    main()
