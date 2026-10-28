"""connectors/ainas.py — AINAS 接入（可选连接器）

AINAS 是另一款产品（家庭 AI 媒体 NAS）。本连接器让 nastool 的检测结果
可以登记到 AINAS 的设备列表并归档诊断报告，仅此而已：

  接口契约（AINAS master 实测确认）：
    GET  /health                        → {"status": "healthy"}
    POST /api/devices/register          查询参数（device_id/device_name/ip_address/port/npu_type/...）
    POST /api/devices/heartbeat         查询参数（device_id/cpu_usage/npu_usage/storage_usage）
    POST /api/devices/{id}/diagnosis    JSON（诊断报告归档）
    GET  /api/devices/{id}/info         查询设备

  不使用 AINAS 时，本文件完全不会被 import。
"""
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from .base import BaseConnector


def _sanitize_id(value: str) -> str:
    cleaned = "".join(c if (c.isalnum() or c in "-_.") else "-" for c in (value or ""))
    return cleaned.strip("-.")[:128] or "device"


class AinasConnector(BaseConnector):
    name = "ainas"

    def __init__(self, host: str = "127.0.0.1", port: int = 8000,
                 device_name: str = "", device_id: str = "",
                 timeout: int = 8, **kwargs):
        self.host = host
        self.port = int(port)
        self.device_name = device_name or socket.gethostname()
        self.device_id = _sanitize_id(device_id or self.device_name)
        self.timeout = timeout

    # ── HTTP ────────────────────────────────────────────────
    def _url(self, path: str, params: dict = None) -> str:
        url = f"http://{self.host}:{self.port}{path}"
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            url += "?" + urllib.parse.urlencode(clean)
        return url

    @staticmethod
    def _read(resp) -> dict:
        raw = resp.read().decode("utf-8", errors="replace")
        if not raw.strip():
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}

    def _post(self, path: str, params: dict, timeout: int = None) -> dict:
        try:
            req = urllib.request.Request(self._url(path, params), data=b"", method="POST")
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return self._read(resp)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def _post_json(self, path: str, data: dict, timeout: int = None) -> dict:
        try:
            req = urllib.request.Request(
                self._url(path), data=json.dumps(data).encode(), method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return self._read(resp)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def _get(self, path: str, timeout: int = None) -> dict:
        try:
            with urllib.request.urlopen(self._url(path), timeout=timeout or self.timeout) as resp:
                return self._read(resp)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    # ── 工具 ────────────────────────────────────────────────
    @staticmethod
    def local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
            finally:
                s.close()
        except Exception:  # noqa: BLE001
            return "127.0.0.1"

    # ── 主流程 ──────────────────────────────────────────────
    def push(self, payload: dict) -> tuple:
        health = self._get("/health", timeout=4)
        if "error" in health:
            return False, f"AINAS 不可达（{self.host}:{self.port}）：{health['error']}"
        if health.get("status") not in ("healthy", "ok", None):
            return False, f"AINAS 健康检查异常：{health.get('status')}"

        # 报告格式 3.0：事实数据在 payload["facts"]，平台信息在 payload["platform"]
        facts = payload.get("facts", {}) or {}
        storage = facts.get("storage", {}) or {}
        ai = facts.get("ai", {}) or {}
        platform = payload.get("platform", {}) or {}
        score = payload.get("score", {}) or {}

        reg = self._post("/api/devices/register", {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "ip_address": self.local_ip(),
            "port": self.port,
            "npu_type": ai.get("best_chip_type", "unknown") or "unknown",
            "cpu_usage": 0.0,
            "npu_usage": 0.0,
            "storage_usage": float(storage.get("use_percent", 0) or 0),
        })
        if "error" in reg:
            return False, f"注册失败：{reg['error']}"

        self.device_id = reg.get("device_id") or self.device_id
        diag_path = f"/api/devices/{urllib.parse.quote(self.device_id, safe='')}/diagnosis"
        saved = self._post_json(diag_path, {
            "score": score.get("total"),
            "grade": score.get("grade"),
            "chip_type": ai.get("best_chip_type", ""),
            "os": platform.get("pretty_name") or platform.get("product", ""),
            "arch": platform.get("arch", ""),
            "storage_path": storage.get("target_path", ""),
            "report": payload,
        })
        if "error" in saved:
            return True, (f"已注册到 AINAS（id={self.device_id}），"
                          f"但诊断报告归档失败：{saved['error']}")
        return True, f"已注册到 AINAS（id={self.device_id}）并归档诊断报告"
