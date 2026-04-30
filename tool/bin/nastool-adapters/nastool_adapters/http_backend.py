"""
AI-NAS HTTP Backend Adapter

AI-NAS HTTP 后端适配器，向后兼容现有 AI-NAS 用户。

支持：
- 设备注册到 AI-NAS 后端
- 上传诊断报告
- 获取扫描路径配置
"""

from typing import Dict, List, Optional, Any
import time
import json
import logging

from .base import (
    NASBackend,
    NASConfig,
    NASBackendType,
    DeviceInfo,
    ScanPath,
    DiagnosticReport,
    ConnectionState,
)

logger = logging.getLogger(__name__)


class AI_NASAdapter(NASBackend):
    """
    AI-NAS HTTP 后端适配器

    与 AI-NAS 后端 API 通信。

    Usage:
        config = NASConfig(
            backend_type=NASBackendType.AI_NAS,
            host="https://qizhiainas.com",
            api_key="your-api-key"
        )
        adapter = AI_NASAdapter(config)
        adapter.connect()
        adapter.register_device(device_info)
    """

    backend_type = NASBackendType.AI_NAS
    backend_name = "AI-NAS"
    backend_version = "3.0.7"

    # API 端点
    API_ENDPOINTS = {
        "register": "/api/devices/register",
        "device_info": "/api/devices/{device_id}",
        "scan_paths": "/api/devices/{device_id}/paths",
        "upload_report": "/api/reports",
        "health": "/health",
    }

    def __init__(self, config: NASConfig):
        super().__init__(config)
        self._device_id = None

        # 默认端口
        if not self.config.port:
            if self.config.host.startswith("https"):
                self.config.port = 443
            else:
                self.config.port = 8000

    # ========== 连接管理 ==========

    def connect(self) -> bool:
        """连接到 AI-NAS 后端"""
        try:
            self._connection_state = ConnectionState.CONNECTING

            # 检查后端健康状态
            if not self._check_health():
                self._connection_state = ConnectionState.ERROR
                return False

            self._connection_state = ConnectionState.CONNECTED
            logger.info(f"已连接到 AI-NAS 后端: {self.config.host}")
            return True

        except Exception as e:
            self._set_error(str(e))
            self._connection_state = ConnectionState.ERROR
            logger.error(f"连接 AI-NAS 失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开连接"""
        self._connection_state = ConnectionState.DISCONNECTED
        return True

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connection_state == ConnectionState.CONNECTED

    # ========== API 核心方法 ==========

    def _check_health(self) -> bool:
        """检查后端健康状态"""
        import urllib.request

        url = f"{self.config.host}:{self.config.port}{self.API_ENDPOINTS['health']}"

        try:
            import ssl

            context = None
            if not self.config.verify_ssl:
                context = ssl._create_unverified_context()

            with urllib.request.urlopen(url, context=context, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("status") == "healthy"

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False

    def _api_request(self, method: str, endpoint: str, data: dict = None) -> Optional[dict]:
        """
        发送 API 请求

        Args:
            method: HTTP 方法（GET, POST, PUT, DELETE）
            endpoint: API 端点
            data: 请求数据

        Returns:
            API 响应数据
        """
        import urllib.request
        import urllib.parse

        # 替换路径参数
        if self._device_id:
            endpoint = endpoint.replace("{device_id}", self._device_id)

        url = f"{self.config.host}:{self.config.port}{endpoint}"

        try:
            import ssl

            context = None
            if not self.config.verify_ssl:
                context = ssl._create_unverified_context()

            headers = {"Content-Type": "application/json", "User-Agent": "nastool/3.0.7"}

            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"

            if method == "GET":
                req = urllib.request.Request(url, headers=headers)
            else:
                body = json.dumps(data).encode("utf-8") if data else b"{}"
                req = urllib.request.Request(url, data=body, headers=headers, method=method)

            with urllib.request.urlopen(req, context=context, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            logger.error(f"API 请求失败: {e.code} - {error_body}")
            return None

        except Exception as e:
            logger.error(f"API 请求异常: {e}")
            return None

    # ========== 设备注册 ==========

    def register_device(self, device_info: DeviceInfo) -> bool:
        """
        注册设备到 AI-NAS 后端

        Args:
            device_info: 设备信息

        Returns:
            True 如果注册成功
        """
        try:
            result = self._api_request(
                "POST", self.API_ENDPOINTS["register"], device_info.to_dict()
            )

            if result:
                self._device_id = result.get("device_id", device_info.device_id)
                logger.info(f"设备注册成功: {device_info.device_name} (ID: {self._device_id})")
                return True
            else:
                self._set_error("设备注册失败")
                return False

        except Exception as e:
            self._set_error(f"设备注册失败: {e}")
            logger.error(f"设备注册失败: {e}")
            return False

    # ========== 扫描路径 ==========

    def get_scan_paths(self) -> List[ScanPath]:
        """获取扫描路径列表"""
        paths = []

        try:
            result = self._api_request("GET", self.API_ENDPOINTS["scan_paths"])

            if result and "paths" in result:
                for path_data in result["paths"]:
                    path = ScanPath(
                        path=path_data.get("path", ""),
                        name=path_data.get("name", ""),
                        type=path_data.get("type", "mixed"),
                        recursive=path_data.get("recursive", True),
                        enabled=path_data.get("enabled", True),
                    )
                    paths.append(path)

        except Exception as e:
            logger.error(f"获取扫描路径失败: {e}")

        return paths

    # ========== 诊断报告 ==========

    def upload_report(self, report: DiagnosticReport) -> bool:
        """上传诊断报告"""
        try:
            result = self._api_request(
                "POST", self.API_ENDPOINTS["upload_report"], report.to_dict()
            )

            if result:
                logger.info(f"诊断报告已上传: {report.report_id}")
                return True
            else:
                return False

        except Exception as e:
            self._set_error(f"上传报告失败: {e}")
            logger.error(f"上传报告失败: {e}")
            return False

    # ========== 配置管理 ==========

    def get_config(self) -> NASConfig:
        """获取当前配置"""
        return self.config

    def update_config(self, config: NASConfig) -> bool:
        """更新配置"""
        self.config = config
        return True

    # ========== 设备信息 ==========

    def get_device_info(self) -> Optional[DeviceInfo]:
        """获取当前设备信息"""
        try:
            result = self._api_request("GET", self.API_ENDPOINTS["device_info"])

            if result:
                return DeviceInfo(
                    device_id=result.get("device_id", ""),
                    device_name=result.get("device_name", ""),
                    hostname=result.get("hostname", ""),
                    cpu_model=result.get("cpu_model", ""),
                    cpu_cores=result.get("cpu_cores", 0),
                    memory_total=result.get("memory_total", 0),
                    ip_address=result.get("ip_address", ""),
                )

        except Exception as e:
            logger.error(f"获取设备信息失败: {e}")

        return None

    def update_device_info(self, device_info: DeviceInfo) -> bool:
        """更新设备信息"""
        try:
            result = self._api_request(
                "PUT", self.API_ENDPOINTS["device_info"], device_info.to_dict()
            )

            return result is not None

        except Exception as e:
            logger.error(f"更新设备信息失败: {e}")
            return False

    # ========== 存储管理 ==========

    def get_shares(self) -> List[str]:
        """获取共享文件夹列表（AI-NAS 不支持，返回空列表）"""
        return []

    def create_share(self, name: str, path: str) -> bool:
        """创建共享文件夹（AI-NAS 不支持）"""
        return False

    # ========== 通知 ==========

    def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        """发送通知（AI-NAS 通过其他方式推送）"""
        logger.info(f"[{level.upper()}] {title}: {message}")
        return True

    # ========== ARM 芯片检测 ==========

    def detect_arm_chip(self) -> Dict[str, str]:
        """检测 ARM 芯片信息（从设备信息获取）"""
        device_info = self.get_device_info()

        if device_info:
            return {
                "vendor": device_info.arm_chip_vendor,
                "model": device_info.arm_chip_model,
                "cores": str(device_info.arm_chip_cores),
                "arch": device_info.cpu_arch,
            }

        return {"vendor": "unknown", "model": "unknown", "cores": "0", "arch": "unknown"}
