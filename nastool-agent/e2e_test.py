"""e2e_test.py - Full end-to-end test: agent register + diagnosis command"""
import websocket
import websocket._app
import json
import time
import threading
import sys
import os

# 从环境变量读取配置，避免硬编码敏感信息
# 使用方式: AGENT_KEY=xxx RELAY_HOST=120.77.249.3 python e2e_test.py
AGENT_KEY = os.environ.get("AGENT_KEY", "")
RELAY_HOST = os.environ.get("RELAY_HOST", "localhost")
RELAY_PORT = os.environ.get("RELAY_PORT", "18888")

# 验证必要配置
if not AGENT_KEY:
    print("ERROR: AGENT_KEY environment variable is required")
    print("Usage: AGENT_KEY=xxx RELAY_HOST=120.77.249.3 python e2e_test.py")
    sys.exit(1)

RELAY_WS = "ws://%s:%s/ws/agent" % (RELAY_HOST, RELAY_PORT)
RELAY_HTTP = "http://%s:%s" % (RELAY_HOST, RELAY_PORT)
DEVICE_ID = "test-e2e-agent"

agent_registered = threading.Event()
agent_result = {"received": False, "data": None}
gui_messages = []

# ---- Agent side (simulates 192.168.1.123) ----
def agent_on_open(ws):
    msg = json.dumps({
        "type": "register",
        "agent_key": AGENT_KEY,
        "data": {
            "device_id": DEVICE_ID,
            "device_name": "E2E Test Agent",
            "device_type": "test",
            "group": "test",
            "version": "1.0.0",
            "capabilities": json.dumps(["diagnosis", "command"]),
            "hostname": "test-host",
            "os": "Linux",
            "arch": "x86_64"
        }
    })
    ws.send(msg)
    print("[AGENT] Registration sent")

def agent_on_message(ws, message):
    data = json.loads(message)
    msg_type = data.get("type", "")
    payload = data.get("payload", {})

    if msg_type == "agent:register":
        print("[AGENT] Registered! session=%s" % str(payload.get("session_id", ""))[:20])
        agent_registered.set()

    elif msg_type == "command":
        cmd = payload.get("cmd", "")
        command_id = payload.get("command_id", "")
        print("[AGENT] Received command: %s" % cmd)

        # Execute command
        import subprocess
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            result = {
                "type": "command_result",
                "command_id": command_id,
                "session_id": "",
                "status": "success" if r.returncode == 0 else "error",
                "data": {"stdout": r.stdout[:2000], "stderr": r.stderr[:500], "exit_code": r.returncode}
            }
        except Exception as e:
            result = {"type": "command_result", "command_id": command_id, "session_id": "", "status": "error", "error": str(e)}

        time.sleep(1)
        ws.send(json.dumps(result))
        print("[AGENT] Result sent: %s" % result["status"])

    elif msg_type in ["agent:ping", "ping"]:
        ws.send(json.dumps({"type": "agent:pong"}))

def agent_on_error(ws, error):
    print("[AGENT] Error: %s" % str(error)[:100])

def agent_on_close(ws, code, reason):
    print("[AGENT] Closed (code=%s)" % str(code))

def run_agent():
    url = "%s?key=%s" % (RELAY_WS, AGENT_KEY)
    ws = websocket._app.WebSocketApp(url, on_open=agent_on_open, on_message=agent_on_message, on_error=agent_on_error, on_close=agent_on_close)
    ws.run_forever(ping_interval=15, ping_timeout=5)


# ---- GUI side (simulates cloud desktop monitoring) ----
def gui_on_message(ws, message):
    data = json.loads(message)
    msg_type = data.get("type", "")
    gui_messages.append(data)
    if msg_type in ["command_result", "agent:message"]:
        agent_result["received"] = True
        agent_result["data"] = data

def gui_on_open(ws):
    print("[GUI] Connected to GUI WebSocket")

def gui_on_error(ws, error):
    print("[GUI] Error: %s" % str(error)[:100])

def gui_on_close(ws, code, reason):
    print("[GUI] Closed (code=%s)" % str(code))

def run_gui():
    url = "%s?key=%s" % ("ws://%s:%s/ws/gui" % (RELAY_HOST, RELAY_PORT), AGENT_KEY.replace("ak_", "gui_"))
    ws = websocket._app.WebSocketApp(url, on_open=gui_on_open, on_message=gui_on_message, on_error=gui_on_error, on_close=gui_on_close)
    ws.run_forever(ping_interval=15, ping_timeout=5)


# ---- Main test flow ----
print("=" * 60)
print("  NASTool Agent E2E Test")
print("=" * 60)
print()

# Start agent in background
print("[TEST] Starting agent...")
agent_thread = threading.Thread(target=run_agent, daemon=True)
agent_thread.start()

# Wait for registration
print("[TEST] Waiting for agent registration...")
if not agent_registered.wait(timeout=10):
    print("[TEST] FAILED: Agent did not register in 10s")
    sys.exit(1)

print("[TEST] Agent registered! Waiting 2s for server sync...")
time.sleep(2)

# Check via REST API
print()
print("[TEST] Checking device list via REST API...")
import urllib.request
try:
    req = urllib.request.urlopen("%s/devices" % RELAY_HTTP, timeout=5)
    devices_data = json.loads(req.read())
    print("[TEST] Total devices: %s, Online: %s" % (devices_data.get("total", 0), devices_data.get("online", 0)))
    for d in devices_data.get("devices", []):
        print("[TEST]   %s  status=%s  type=%s" % (d.get("device_id"), d.get("status"), d.get("device_type")))
except Exception as e:
    print("[TEST] REST API error: %s" % e)

# Send diagnosis command via REST API
print()
print("[TEST] Sending diagnosis command to %s..." % DEVICE_ID)
cmd_body = json.dumps({"cmd": "uname -a", "timeout_ms": 10000}).encode()
req = urllib.request.Request(
    "%s/devices/%s/commands" % (RELAY_HTTP, DEVICE_ID),
    data=cmd_body,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    resp = urllib.request.urlopen(req, timeout=5)
    cmd_result = json.loads(resp.read())
    command_id = cmd_result.get("command_id", "")
    status = cmd_result.get("status", "")
    print("[TEST] Command sent! id=%s status=%s" % (command_id[:20], status))
except Exception as e:
    print("[TEST] Command send error: %s" % e)
    command_id = None

# Wait for agent to process command
if command_id:
    print("[TEST] Waiting for command result (max 15s)...")
    for i in range(15):
        time.sleep(1)
        try:
            req2 = urllib.request.urlopen("%s/devices/%s/commands/%s" % (RELAY_HTTP, DEVICE_ID, command_id), timeout=5)
            result = json.loads(req2.read())
            rstatus = result.get("status", "")
            if rstatus in ["success", "error"]:
                print("[TEST] Command result: %s" % rstatus)
                print("[TEST] stdout: %s" % result.get("stdout", "")[:200])
                if result.get("stderr"):
                    print("[TEST] stderr: %s" % result.get("stderr", "")[:100])
                print("[TEST] exit_code: %s" % result.get("exit_code"))
                break
        except Exception as e:
            print("[TEST] Poll error: %s" % e)
    else:
        print("[TEST] Timeout waiting for command result")

print()
print("=" * 60)
print("  E2E Test Complete!")
print("=" * 60)
sys.exit(0)
