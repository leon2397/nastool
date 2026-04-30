# -*- coding: utf-8 -*-
"""SSH test runner for Jetson Xavier NX"""
import paramiko
import sys
import json
import time
import os

HOST = "192.168.1.123"
USER = "nvidia"
PASS = "nvidia"

def ssh_run(cmd, timeout=30):
    """Execute command on Jetson and return output"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, username=USER, password=PASS, timeout=15, banner_timeout=200)
        chan = client.get_transport().open_session()
        chan.settimeout(timeout)
        chan.exec_command(cmd)
        # Read output with timeout handling
        import select
        out_chunks = []
        err_chunks = []
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                break
            if chan.exit_status_ready():
                # Read remaining data
                while chan.recv_stderr_ready():
                    err_chunks.append(chan.recv_stderr(4096).decode('utf-8', errors='replace'))
                while chan.recv_ready():
                    out_chunks.append(chan.recv(4096).decode('utf-8', errors='replace'))
                break
            # Poll for data
            if chan.recv_ready():
                out_chunks.append(chan.recv(4096).decode('utf-8', errors='replace'))
            if chan.recv_stderr_ready():
                err_chunks.append(chan.recv_stderr(4096).decode('utf-8', errors='replace'))
            time.sleep(0.1)
        out = ''.join(out_chunks)
        err = ''.join(err_chunks)
        code = chan.exit_status if chan.exit_status_ready() else -1
        return {"output": out, "error": err, "exit_code": code}
    except Exception as e:
        return {"output": "", "error": str(e), "exit_code": -1}
    finally:
        client.close()

def ssh_upload(local_path, remote_path):
    """Upload file to Jetson via SFTP"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, username=USER, password=PASS, timeout=15)
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        return True
    except Exception as e:
        return False
    finally:
        client.close()

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--upload" and len(sys.argv) >= 4:
            # Upload mode: python ssh_jetson.py --upload local_path remote_path
            local = sys.argv[2]
            remote = sys.argv[3]
            ok = ssh_upload(local, remote)
            print(f"Upload: {local} -> {remote}: {'OK' if ok else 'FAILED'}")
        else:
            # Command mode
            cmd = sys.argv[1]
            result = ssh_run(cmd)
            print(result["output"])
            if result["error"]:
                print("ERROR:", result["error"], file=sys.stderr)
    else:
        # Test connection
        result = ssh_run("uname -a && python3 --version")
        print(result["output"])