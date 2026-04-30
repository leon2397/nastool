#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)

# 直接执行测试
cmd = """
cd /tmp/nastool_test/nastool-cli/nastool_cli && \
PYTHONPATH="/tmp/nastool_test/nastool-cli:/tmp/nastool_test/nastool-common:/tmp/nastool_test/nastool-core:/tmp/nastool_test/nastool-adapters:/tmp/nastool_test/nastool-reporters:/tmp/nastool_test/nastool-fixes" \
python3 main.py --full --no-color
"""

print("执行命令:", cmd[:100], "...")
stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
output = stdout.read().decode('utf-8')
error = stderr.read().decode('utf-8')

print("\n输出:")
print(output[:2000])
if error:
    print("\n错误:", error[:1000])

client.close()
