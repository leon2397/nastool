#!/usr/bin/env python3
import paramiko

HOST = "192.168.1.103"
PORT = 22
USERNAME = "root"
PASSWORD = "linaro123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, port=PORT, username=USERNAME, password=PASSWORD)

stdin, stdout, stderr = client.exec_command("find /tmp/nastool_test -name '*.py' | head -20")
print(stdout.read().decode())

client.close()
