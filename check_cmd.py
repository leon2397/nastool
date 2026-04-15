#!/usr/bin/env python3
import requests

# 获取命令状态
cmd_id = "cmd_8256ad66f42c4679"
url = f"http://120.77.249.3:18888/devices/nvidia-01/commands/{cmd_id}"

try:
    resp = requests.get(url, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
