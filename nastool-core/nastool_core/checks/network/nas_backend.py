"""
checks/network/nas_backend.py - NAS backend connectivity check
"""

import socket
import os
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class NASBackendCheck(Check):
    """Check NAS backend connectivity"""

    check_id = "nas_backend"
    category = CheckCategory.NETWORK
    title = "NAS Backend"
    description = "Check if NAS backend is reachable"

    DEFAULT_HOST = os.environ.get("NAS_HOST", "120.77.249.3")
    DEFAULT_PORT = int(os.environ.get("NAS_PORT", "8000"))

    def _http_get(
        self, host: str, port: int, path: str = "/health", timeout: float = 10.0
    ) -> tuple:
        """Simple HTTP GET without external dependencies"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))

            request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
            sock.send(request.encode())

            response = b""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                response += data

            sock.close()

            response_str = response.decode("utf-8", errors="ignore")
            status_line = response_str.split("\n")[0]
            status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 0

            return status_code, response_str
        except Exception as e:
            return 0, str(e)

    def run(self) -> CheckResult:
        host = self.DEFAULT_HOST
        port = self.DEFAULT_PORT

        # Test TCP connection
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex((host, port))
            sock.close()
            tcp_ok = result == 0
        except Exception as e:
            tcp_ok = False

        # Test HTTP health endpoint
        status_code, response = self._http_get(host, port, "/health")
        http_ok = status_code == 200

        if http_ok:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"NAS backend {host}:{port} reachable, health check passed"
        elif tcp_ok:
            severity = CheckSeverity.WARNING
            passed = True
            message = f"NAS backend {host}:{port} reachable but /health returned {status_code}"
        else:
            severity = CheckSeverity.WARNING
            passed = False
            message = f"NAS backend {host}:{port} not reachable"

        return self._enhance_result_with_accuracy(CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current=f"{host}:{port}",
            expected="reachable",
            message=message,
            fix_available=False,  # Usually requires manual firewall/security group fix
            fix_description="Check security group rules or firewall settings",
            fix_risk="none",
            details={
                "host": host,
                "port": port,
                "tcp_ok": tcp_ok,
                "http_status": status_code,
            },
        ))
