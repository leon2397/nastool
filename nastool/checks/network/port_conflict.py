"""
checks/network/port_conflict.py - Port conflict check
"""

import socket
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class PortConflictCheck(Check):
    """Check for port conflicts"""

    check_id = "port_conflict"
    category = CheckCategory.NETWORK
    title = "Port Conflict"
    description = "Check if required ports are available"

    CHECK_PORTS = [9999, 8000]  # Default ports for NAS

    def _port_in_use(self, port: int) -> tuple:
        """Check if port is in use, return (in_use, process_info)"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()

            if result == 0:
                # Port is in use, try to get process info
                process_info = self._run_command(
                    f"netstat -tlnp 2>/dev/null | grep :{port} || ss -tlnp 2>/dev/null | grep :{port}"
                )
                return True, process_info.strip()
            return False, ""
        except Exception as e:
            return False, ""

    def run(self) -> CheckResult:
        conflicts = []
        available = []

        for port in self.CHECK_PORTS:
            in_use, process_info = self._port_in_use(port)
            if in_use:
                conflicts.append({"port": port, "info": process_info})
            else:
                available.append(port)

        if not conflicts:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"All required ports available: {available}"
        else:
            conflict_ports = [c["port"] for c in conflicts]
            severity = CheckSeverity.WARNING
            passed = True  # Warning, not critical - maybe intentional
            message = f"Ports in use: {conflict_ports}. May need to stop conflicting service or use different port."

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current=f"{len(available)} available, {len(conflicts)} in use",
            expected="all available",
            message=message,
            fix_available=len(conflicts) > 0,
            fix_id="stop_port_process",
            fix_description="Stop conflicting process or change port configuration",
            fix_risk="medium",
            details={"conflicts": conflicts, "available": available},
        )
