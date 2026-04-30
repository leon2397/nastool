"""
nastool_api_client.py - NASTool Relay Server API Client (Python SDK)

A clean Python SDK for the NASTool Relay Server REST API + WebSocket.

Usage:
    from nastool_adapters.nastool_api_client import NASToolAPIClient

    client = NASToolAPIClient("http://120.77.249.3:18888", api_key="ak_xxx")

    # Devices
    devices = client.list_devices()
    info = client.get_device("nvidia-01")

    # Commands
    cmd = client.send_command("nvidia-01", "nastool --json --full")
    result = client.get_command_result(cmd["command_id"])

    # Reports
    report = client.get_latest_report("nvidia-01")
    history = client.get_reports("nvidia-01", limit=20)

    # Batch
    batch = client.batch_command(["device1", "device2"], "nastool --json")

    # WebSocket
    ws = client.ws_connect(on_message=handler)
"""

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from urllib.parse import urljoin


# ─── Data Classes ───────────────────────────────────────

@dataclass
class Device:
    """Device entity."""
    id: str
    name: str
    type: str
    status: str  # "online" | "offline"
    version: str = ""
    ip_local: str = ""
    ip_public: str = ""
    last_seen: str = ""
    registered_at: str = ""
    group: str = "default"
    hostname: str = ""

    @classmethod
    @classmethod
    def from_dict(cls, d):
        ip = {}
        try:
            ip = d.get("ip", {}) or {}
        except Exception:
            pass
        return cls(
            id=d.get("device_id") or d.get("id") or "",
            name=d.get("device_name") or d.get("name") or "",
            type=d.get("device_type") or d.get("type") or "",
            status=d.get("status", "unknown"),
            version=d.get("version", ""),
            ip_local=d.get("ip_local") or ip.get("local") or "",
            ip_public=d.get("ip_public") or ip.get("public") or "",
            last_seen=d.get("last_seen", ""),
            registered_at=d.get("registered_at", ""),
            group=d.get("group", "default"),
            hostname=d.get("hostname", ""),
        )




@dataclass
class CommandResult:
    """Command execution result."""
    command_id: str
    device_id: str
    status: str  # "queued" | "sent" | "completed" | "failed" | "timeout"
    cmd: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_ms: int = 0
    created_at: str = ""
    completed_at: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "CommandResult":
        return cls(
            command_id=d.get("command_id", ""),
            device_id=d.get("device_id", ""),
            status=d.get("status", "unknown"),
            cmd=d.get("cmd", ""),
            stdout=d.get("stdout", ""),
            stderr=d.get("stderr", ""),
            exit_code=d.get("exit_code", -1),
            duration_ms=d.get("duration_ms", 0),
            created_at=d.get("created_at", ""),
            completed_at=d.get("completed_at", ""),
        )


@dataclass
class DiagnosisReport:
    """Diagnosis report."""
    device_id: str
    report_id: str
    reported_at: str = ""
    overall_score: int = 0
    categories: Dict[str, int] = field(default_factory=dict)
    items: List[Dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "DiagnosisReport":
        cats = d.get("categories", {})
        if isinstance(cats, str):
            import json as _json
            cats = _json.loads(cats)
        return cls(
            device_id=d.get("device_id", ""),
            report_id=d.get("report_id", ""),
            reported_at=d.get("reported_at", ""),
            overall_score=int(d.get("overall_score", 0)),
            categories=cats,
            items=d.get("items", []),
        )


# ─── API Client ───────────────────────────────────────

class NASToolAPIClient:
    """
    Python SDK for NASTool Relay Server.

    Supports:
    - Device management
    - Command execution
    - Diagnosis reports
    - Batch operations
    - API key authentication
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize API client.

        Args:
            base_url: Relay Server URL (e.g. "http://120.77.249.3:18888")
            api_key: API key for authentication (optional)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        # Build API v2 base URL
        self._api_url = self.base_url  # routes use root path

    # ── HTTP helpers ──────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Make an HTTP request to the Relay Server."""
        url = urljoin(self.base_url, path.lstrip("/"))

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NASTool-Python-SDK/2.0",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            if method == "GET":
                if params:
                    qs = "&".join(f"{k}={v}" for k, v in params.items())
                    url = f"{url}?{qs}"
                req = urllib.request.Request(url, headers=headers)
            else:
                body = json.dumps(data).encode("utf-8") if data else b"{}"
                req = urllib.request.Request(
                    url, data=body, headers=headers, method=method
                )

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:200]
            raise APIError(f"HTTP {e.code}: {body}", status=e.code)
        except urllib.error.URLError as e:
            raise APIError(f"Connection failed: {e.reason}", status=0)
        except Exception as e:
            raise APIError(f"Request error: {e}", status=0)

        return None

    def get(self, path: str, params: Optional[Dict] = None) -> Optional[Dict]:
        return self._request("GET", path, params=params)

    def post(self, path: str, data: Optional[Dict] = None) -> Optional[Dict]:
        return self._request("POST", path, data=data)

    def put(self, path: str, data: Optional[Dict] = None) -> Optional[Dict]:
        return self._request("PUT", path, data=data)

    def delete(self, path: str) -> Optional[Dict]:
        return self._request("DELETE", path)

    # ── Device Management ─────────────────────────────

    def list_devices(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Device]:
        """
        List all devices.

        Args:
            status: Filter by "online" or "offline"
            limit: Max results
            offset: Pagination offset

        Returns:
            List of Device objects
        """
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status

        result = self.get("/devices", params=params)
        if not result:
            return []

        devices = result.get("devices", [])
        if isinstance(devices, dict) and "agents" in devices:
            # API v2 response format
            devices = devices["agents"]

        return [Device.from_dict(d) for d in devices]

    def get_device(self, device_id: str) -> Optional[Device]:
        """Get a single device by ID."""
        result = self.get(f"/devices/{device_id}")
        if not result or result.get("error"):
            return None
        return Device.from_dict(result)

    def delete_device(self, device_id: str) -> bool:
        """Delete a device."""
        result = self.delete(f"/devices/{device_id}")
        return result is not None

    # ── Command Execution ────────────────────────────

    def send_command(
        self,
        device_id: str,
        cmd: str,
        timeout_ms: int = 30000,
    ) -> CommandResult:
        """
        Send a command to a device.

        Args:
            device_id: Target device ID
            cmd: Command string
            timeout_ms: Timeout in milliseconds

        Returns:
            CommandResult with command_id and initial status
        """
        result = self.post(f"/devices/{device_id}/commands", {
            "cmd": cmd,
            "timeout_ms": timeout_ms,
        })

        if not result or result.get("error"):
            raise APIError(f"Failed to send command: {result}", status=500)

        return CommandResult.from_dict(result)

    def get_command_result(
        self,
        device_id: str,
        command_id: str,
    ) -> Optional[CommandResult]:
        """Get the result of a command."""
        result = self.get(f"/devices/{device_id}/commands/{command_id}")
        if not result or result.get("error"):
            return None
        return CommandResult.from_dict(result)

    def wait_command(
        self,
        device_id: str,
        command_id: str,
        poll_interval: float = 2.0,
        max_wait: float = 120.0,
    ) -> Optional[CommandResult]:
        """
        Wait for a command to complete (polling).

        Args:
            device_id: Target device ID
            command_id: Command ID
            poll_interval: Polling interval in seconds
            max_wait: Max wait time in seconds

        Returns:
            Final CommandResult or None if timeout
        """
        deadline = time.time() + max_wait

        while time.time() < deadline:
            result = self.get_command_result(device_id, command_id)
            if not result:
                time.sleep(poll_interval)
                continue

            if result.status in ("completed", "failed", "timeout"):
                return result

            time.sleep(poll_interval)

        return None  # Timeout

    def get_command_history(
        self,
        device_id: str,
        limit: int = 50,
    ) -> List[CommandResult]:
        """Get command history for a device."""
        result = self.get(
            f"/devices/{device_id}/commands",
            params={"limit": limit}
        )
        if not result:
            return []

        commands = result.get("commands", [])
        return [CommandResult.from_dict(c) for c in commands]

    # ── Diagnosis Reports ────────────────────────────

    def get_latest_report(self, device_id: str) -> Optional[DiagnosisReport]:
        """Get the latest diagnosis report for a device."""
        result = self.get(f"/devices/{device_id}/reports/latest")
        if not result or result.get("error"):
            return None
        return DiagnosisReport.from_dict(result)

    def get_reports(
        self,
        device_id: str,
        limit: int = 20,
    ) -> List[DiagnosisReport]:
        """Get diagnosis report history."""
        result = self.get(
            f"/devices/{device_id}/reports",
            params={"limit": limit}
        )
        if not result:
            return []

        reports = result.get("reports", [])
        return [
            DiagnosisReport(device_id=device_id, report_id=r.get("report_id", ""),
                            reported_at=r.get("reported_at", ""),
                            overall_score=int(r.get("overall_score", 0)),
                            categories=r.get("categories", {}))
            for r in reports
        ]

    # ── Batch Operations ────────────────────────────

    def batch_command(
        self,
        device_ids: List[str],
        cmd: str,
        timeout_ms: int = 30000,
    ) -> Dict[str, Any]:
        """
        Send a command to multiple devices at once.

        Args:
            device_ids: List of device IDs
            cmd: Command string

        Returns:
            Batch result dict with batch_id and per-device results
        """
        # Try API v2 batch endpoint first
        result = self.post("/api/v2/agents/batch/commands", {
            "device_ids": device_ids,
            "cmd": cmd,
            "timeout_ms": timeout_ms,
        })

        if result and result.get("data"):
            return result["data"]

        # Fallback: send individually
        results = []
        for device_id in device_ids:
            try:
                cmd_result = self.send_command(device_id, cmd, timeout_ms)
                results.append({
                    "device_id": device_id,
                    **cmd_result.__dict__,
                })
            except APIError as e:
                results.append({"device_id": device_id, "error": str(e)})

        return {
            "batch_id": f"batch_{int(time.time())}",
            "total": len(device_ids),
            "success": sum(1 for r in results if "error" not in r),
            "failed": sum(1 for r in results if "error" in r),
            "results": results,
        }

    # ── System ─────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get Relay Server status."""
        result = self.get("/relay/status")
        return result or {}

    def get_api_status(self) -> Dict[str, Any]:
        """Get API v2 status."""
        result = self.get("/api/v2/status")
        return result.get("data", {}) if result else {}


# ─── API Error ───────────────────────────────────────

class APIError(Exception):
    """API request error."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status
        self.message = message


# ─── Convenience functions ───────────────────────────

def create_client(
    base_url: str = "http://120.77.249.3:18888",
    api_key: Optional[str] = None,
) -> NASToolAPIClient:
    """Create a pre-configured API client."""
    return NASToolAPIClient(base_url, api_key)
