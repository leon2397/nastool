"""test_relay_ws.py - Test WebSocket connection to Relay Server"""
import websocket
import json
import time
import sys
import threading

AGENT_KEY = "ak_1c4d26d5f49c459fbd5ae83a309dd7f7"
RELAY_URL = "ws://120.77.249.3:18888/ws/agent"

result = {"connected": False, "registered": False, "error": None, "response": None}
stop_event = threading.Event()

def on_open(ws):
    print("[TEST] WebSocket OPEN - Connection successful!")
    result["connected"] = True
    
    msg = json.dumps({
        "type": "register",
        "agent_key": AGENT_KEY,
        "data": {
            "device_id": "test-cloud-desktop",
            "device_name": "Cloud Desktop Test",
            "device_type": "test",
            "group": "test",
            "version": "1.0.0-test",
            "capabilities": "[]"
        }
    })
    ws.send(msg)
    print("[TEST] Sent: register (device_id=test-cloud-desktop)")

def on_message(ws, message):
    data = json.loads(message)
    msg_type = data.get("type", "")
    print("[TEST] Received: %s" % json.dumps(data)[:300])
    result["response"] = data
    
    if msg_type in ["register", "registered", "connected", "agent:register"]:
        result["registered"] = True
    
    # After receiving response, stop
    time.sleep(1)
    stop_event.set()
    ws.close()

def on_error(ws, error):
    print("[TEST] Error: %s" % str(error))
    result["error"] = str(error)
    stop_event.set()

def on_close(ws, code, reason):
    print("[TEST] Closed (code=%s, reason=%s)" % (str(code), str(reason)))
    stop_event.set()

print("[TEST] Connecting to %s ..." % RELAY_URL)

ws = websocket.WebSocketApp(
    "%s?key=%s" % (RELAY_URL, AGENT_KEY),
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

# Run in a thread with timeout
t = threading.Thread(target=ws.run_forever, kwargs={"ping_interval": 30})
t.daemon = True
t.start()

# Wait up to 15 seconds
stop_event.wait(timeout=15)

if ws.sock and ws.sock.connected:
    ws.close()

t.join(timeout=3)

print()
print("=== RESULTS ===")
print("Connected:    %s" % result["connected"])
print("Registered:   %s" % result["registered"])
print("Error:        %s" % result["error"])

if result["connected"] and result["registered"]:
    print()
    print("SUCCESS: Agent can connect and register via Relay!")
    sys.exit(0)
elif result["connected"]:
    print()
    print("PARTIAL: Connected but registration may have failed.")
    print("Response: %s" % json.dumps(result["response"]) if result["response"] else "None")
    sys.exit(2)
else:
    print()
    print("FAILED: Cannot connect to Relay Server.")
    sys.exit(1)
