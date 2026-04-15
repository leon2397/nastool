#!/usr/bin/env python3
import requests
import json
import time

# 1. 检查设备状态
url = "http://120.77.249.3:18888/devices/nvidia-01"
resp = requests.get(url, timeout=10)
device = resp.json()
print(f"设备状态: {device.get('status')}")
print(f"最后在线: {device.get('last_seen')}")

# 2. 发送测试命令
url_cmd = "http://120.77.249.3:18888/devices/nvidia-01/commands"
data = {"cmd": "uname -a", "timeout_ms": 30000}
resp = requests.post(url_cmd, json=data, timeout=35)
cmd_result = resp.json()
print(f"\n命令状态: {cmd_result.get('status')}")
print(f"Command ID: {cmd_result.get('command_id')}")

# 3. 等待一下再检查命令结果
time.sleep(2)
cmd_id = cmd_result.get('command_id')
url_result = f"http://120.77.249.3:18888/devices/nvidia-01/commands/{cmd_id}"
resp2 = requests.get(url_result, timeout=10)
result = resp2.json()
print(f"\n执行结果:")
print(f"  Status: {result.get('status')}")
print(f"  Exit code: {result.get('exit_code')}")
print(f"  Stdout: {result.get('stdout', '')[:200]}")
print(f"  Stderr: {result.get('stderr', '')[:200]}")
