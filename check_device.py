#!/usr/bin/env python3
import requests

# 获取设备详情
url = "http://120.77.249.3:18888/devices/nvidia-01"
resp = requests.get(url, timeout=10)
print("Device details:")
print(resp.text)

# 获取所有 sessions
url2 = "http://120.77.249.3:18888/api/v1/sessions"
try:
    resp2 = requests.get(url2, timeout=10)
    print("\nSessions:")
    print(resp2.text)
except Exception as e:
    print(f"Sessions error: {e}")
