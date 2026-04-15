#!/usr/bin/env python3
import requests
import json

url = "http://120.77.249.3:18888/devices/nvidia-01/commands"
data = {"cmd": "hostname", "timeout_ms": 30000}

try:
    resp = requests.post(url, json=data, timeout=35)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
