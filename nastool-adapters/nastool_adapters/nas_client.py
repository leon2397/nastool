"""
nas_integration/client.py -- NAS 后端 API 客户端
负责：注册设备 -> 上报状态 -> 触发 AI 分类全流程
"""

import json
import socket
import subprocess
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class NASClient:
    host: str = "120.77.249.3"
    port: int = 8000
    device_id: str = ""
    device_name: str = ""

    # ── 底层 HTTP ────────────────────────────────────────────
    def _url(self, path: str) -> str:
        return f"http://{self.host}:{self.port}{path}"

    def _get(self, path: str, timeout: int = 5) -> Dict:
        try:
            req = urllib.request.Request(self._url(path))
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}

    def _post(self, path: str, data: Dict, timeout: int = 5) -> Dict:
        try:
            body = json.dumps(data).encode()
            req = urllib.request.Request(
                self._url(path), data=body, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            try:
                return {"error": f"HTTP {e.code}: {e.read().decode()}"}
            except Exception as e:
                return {"error": f"HTTP {e.code}"}
        except Exception as e:
            return {"error": str(e)}

    def is_alive(self) -> bool:
        r = self._get("/health", timeout=3)
        return r.get("status") == "ok" or r.get("status") == "healthy"

    # ── 1. 设备注册 ──────────────────────────────────────────
    def register(
        self,
        chip_type: str = "",
        storage_path: str = "/home/nvidia",
        os_name: str = "",
        arch: str = "",
        extra: Optional[Dict] = None,
    ) -> Dict:
        """
        向 NAS 后端注册此 ARM 设备
        成功后返回 {"id": "...", "status": "registered"}
        """
        payload = {
            "name": self.device_name or socket.gethostname(),
            "device_type": "arm",
            "chip_type": chip_type,
            "storage_path": storage_path,
            "os": os_name,
            "arch": arch,
        }
        if extra:
            payload.update(extra)
        return self._post("/api/devices/register", payload)

    # ── 2. 心跳上报 ──────────────────────────────────────────
    def heartbeat(
        self, status: str = "online", cpu_temp: float = 0, mem_used_pct: float = 0
    ) -> Dict:
        """定期向 NAS 报告设备存活状态"""
        return self._post(
            f"/api/devices/{self.device_id}/heartbeat",
            {
                "status": status,
                "cpu_temp_c": cpu_temp,
                "mem_used_pct": mem_used_pct,
            },
        )

    # ── 3. 查询相册列表 ──────────────────────────────────────
    def list_albums(self) -> Dict:
        return self._get("/api/albums/")

    # ── 4. 触发 AI 分类（全量）────────────────────────────────
    def trigger_classify_all(self) -> Dict:
        """触发对所有图片的 AI 分类"""
        return self._post("/api/ai/classify", {"scope": "all", "device_id": self.device_id})

    # ── 5. 查询 AI 任务状态 ──────────────────────────────────
    def ai_task_status(self) -> Dict:
        return self._get("/api/ai/status")

    # ── 6. 上报诊断报告 ──────────────────────────────────────
    def report_diagnosis(self, diagnosis: Dict) -> Dict:
        """将诊断报告发送给 NAS 后端存档"""
        return self._post(
            "/api/devices/diagnosis",
            {
                "device_id": self.device_id,
                "report": diagnosis,
            },
        )

    # ── 一键注册 + 检测流程 ──────────────────────────────────
    def diagnose_and_register(
        self,
        chip_type: str,
        storage_path: str,
        os_name: str,
        arch: str,
        report: Optional[Dict] = None,
    ) -> tuple:
        """
        主流程：NAS 连通性 -> 注册 -> 上报诊断
        返回 (registered: bool, message: str)
        """
        # Step 1: NAS 可达性
        if not self.is_alive():
            return False, f"NAS 后端 ({self.host}:{self.port}) 不可达，请检查网络"

        # Step 2: 注册设备
        reg = self.register(
            chip_type=chip_type,
            storage_path=storage_path,
            os_name=os_name,
            arch=arch,
            extra={"diagnosis_report": report} if report else None,
        )
        if "error" in reg:
            return False, f"注册失败: {reg['error']}"

        self.device_id = reg.get("id", "")
        return True, f"设备注册成功 (id={self.device_id})"
