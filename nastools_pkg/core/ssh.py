# -*- coding: utf-8 -*-
"""
nastools SSH 连接封装 — 线程安全
"""

import socket
import time
import paramiko

# ── 全局 socket 超时：防止设备 IP 不存在时系统级阻塞 ─────────────────
# socket.create_connection() 默认无超时（可等 75s+），
# 设置全局默认值后，所有 socket 操作默认最多等 10s。
socket.setdefaulttimeout(10)


class SSHConnection:
    """SSH/SFTP 连接，所有方法可在子线程调用"""

    def __init__(self):
        self.client = None
        self.sftp = None

    def connect(self, host, port, user, password):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.client.connect(
                host,
                port=int(port),
                username=user,
                password=password,
                timeout=15,
                banner_timeout=15,
            )
            self.sftp = self.client.open_sftp()
            return True, "连接成功 ✓"
        except Exception as e:
            return False, str(e)

    def exec(self, cmd, timeout=60):
        """执行命令，返回 (returncode, stdout, stderr)"""
        if not self.client:
            return -1, "", "未连接"
        try:
            _, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
            ec = stdout.channel.recv_exit_status()
            return (
                ec,
                stdout.read().decode("utf-8", errors="replace"),
                stderr.read().decode("utf-8", errors="replace"),
            )
        except Exception as e:
            return -1, "", str(e)

    def exec_script(self, script, timeout=120):
        """上传脚本到 /tmp/，执行，返回 (ok, output)"""
        path = f"/tmp/_nastool_{int(time.time())}.sh"
        try:
            with self.sftp.open(path, "w") as f:
                f.write(script)
            self.sftp.chmod(path, 0o755)
        except Exception as e:
            return False, f"上传脚本失败: {e}"
        ec, out, err = self.exec(f"bash {path} 2>&1", timeout=timeout)
        try:
            self.sftp.remove(path)
        except Exception:
            pass
        return ec == 0, out if ec == 0 else (err or out)

    def upload_file(self, local_path, remote_path):
        """SFTP 上传文件"""
        if not self.sftp:
            return False, "SFTP 未连接"
        try:
            self.sftp.put(local_path, remote_path)
            return True, f"上传成功: {remote_path}"
        except Exception as e:
            return False, str(e)

    def close(self):
        try:
            if self.sftp:
                self.sftp.close()
        except Exception:
            pass
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass
        self.client = None
        self.sftp = None
