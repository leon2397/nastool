#!/usr/bin/env python3
import subprocess
import base64

TARGET_HOST = "192.168.1.123"
TARGET_USER = "nvidia"

def run_ssh(cmd):
    full_cmd = ['ssh', f'{TARGET_USER}@{TARGET_HOST}', cmd]
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    return result

# 更新 diagnose.sh
script = '''#!/bin/bash
cd "$(dirname "$0")"
./run.sh "$@"
'''
encoded = base64.b64encode(script.encode()).decode()
cmd = f'echo "{encoded}" | base64 -d > ~/nastool/diagnose.sh && chmod +x ~/nastool/diagnose.sh'
run_ssh(cmd)
print("diagnose.sh 已更新")
