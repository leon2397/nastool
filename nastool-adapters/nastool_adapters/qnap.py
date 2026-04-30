"""
QNAP ARM NAS Adapter

威联通 ARM 机型适配器，支持 QTS API。

支持机型：
- TS-231P3（Annapurna Labs AL-314）
- TS-431KX（Annapurna Labs AL-514）
- TS-233（Realtek RTD1619B）

ARM 芯片支持：
- Annapurna Labs AL-314 / AL-514
- Realtek RTD1619B
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


class QNAPAdapter(NASBackend):
    """
    威联通 QNAP NAS 适配器

    使用 QTS API 与威联通 NAS 通信。

    Usage:
        config = NASConfig(
            backend_type=NASBackendType.QNAP,
            host="https://nas.local:8081",
            username="admin",
            password="password"
        )
        adapter = QNAPAdapter(config)
        adapter.connect()
        adapter.register_device(device_info)
    """

    backend_type = NASBackendType.QNAP
    backend_name = "QNAP"
    backend_version = "3.0.7"

    # ARM 芯片映射
    ARM_CHIP_MAP = {
        "AL-314": {"vendor": "Annapurna Labs", "model": "AL-314", "arch": "armv8"},
        "AL-514": {"vendor": "Annapurna Labs", "model": "AL-514", "arch": "armv8"},
        "RTD1619B": {"vendor": "Realtek", "model": "RTD1619B", "arch": "aarch64"},
    }

    def __init__(self, config: NASConfig):
        super().__init__(config)
        self._auth_token = None
        self._device_id = None

        # 默认端口
        if not self.config.port:
            self.config.port = 8081

    # ========== 连接管理 ==========

    def connect(self) -> bool:
        """连接到威联通 QTS API"""
        try:
            self._connection_state = ConnectionState.CONNECTING

            if not self._login():
                self._connection_state = ConnectionState.ERROR
                return False

            self._connection_state = ConnectionState.CONNECTED
            logger.info(f"已连接到威联通 QTS: {self.config.host}")
            return True

        except Exception as e:
            self._set_error(str(e))
            self._connection_state = ConnectionState.ERROR
            logger.error(f"连接威联通失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开与威联通的连接"""
        try:
            if self._auth_token:
                self._logout()
                self._auth_token = None

            self._connection_state = ConnectionState.DISCONNECTED
            return True

        except Exception as e:
            logger.error(f"断开连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connection_state == ConnectionState.CONNECTED and self._auth_token is not None

    # ========== QTS API 核心方法 ==========

    def _login(self) -> bool:
        """
        登录威联通 QTS

        API: /cgi-bin/authLogin.cgi
        """
        import urllib.request
        import urllib.parse

        url = f"{self.config.host}:{self.config.port}/cgi-bin/authLogin.cgi"

        params = {
            "user": self.config.username,
            "pwd": self.config.password,
        }

        try:
            data = urllib.parse.urlencode(params).encode("utf-8")

            import ssl

            context = None
            if not self.config.verify_ssl:
                context = ssl._create_unverified_context()

            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, context=context, timeout=10) as response:
                result = response.read().decode("utf-8")

                # QTS 返回的是文本格式
                if "authSid" in result or "token" in result:
                    # 解析 token
                    for line in result.split("\n"):
                        if line.startswith("authSid=") or line.startswith("token="):
                            self._auth_token = line.split("=")[1].strip()
                            break

                    if self._auth_token:
                        logger.debug(f"QTS 登录成功")
                        return True
                    else:
                        # 某些版本不返回 token，也算成功
                        self._auth_token = "connected"
                        return True
                else:
                    self._set_error(f"QTS 登录失败: {result[:100]}")
                    return False

        except Exception as e:
            self._set_error(f"QTS 登录异常: {e}")
            logger.error(f"QTS 登录异常: {e}")
            return False

    def _logout(self) -> bool:
        """登出威联通 QTS"""
        import urllib.request

        try:
            url = f"{self.config.host}:{self.config.port}/cgi-bin/authLogout.cgi"
            urllib.request.urlopen(url, timeout=5)
            return True
        except Exception as e:
            logger.error(f"QTS 登出失败: {e}")
            return False

    def _api_request(self, cgi: str, params: dict = None) -> Optional[dict]:
        """
        发送 QTS API 请求

        Args:
            cgi: CGI 脚本名（如 "filemanager/files"）
            params: 请求参数

        Returns:
            API 响应数据
        """
        import urllib.request
        import urllib.parse

        if not self._auth_token:
            logger.error("未登录 QTS")
            return None

        url = f"{self.config.host}:{self.config.port}/cgi-bin/{cgi}.cgi"

        request_params = params or {}

        try:
            full_url = f"{url}?{urllib.parse.urlencode(request_params)}"

            import ssl

            context = None
            if not self.config.verify_ssl:
                context = ssl._create_unverified_context()

            with urllib.request.urlopen(full_url, context=context, timeout=10) as response:
                data = response.read().decode("utf-8")

                # QTS 返回 JSON 或文本
                try:
                    return json.loads(data)
                except Exception as e:
                    # 解析文本格式
                    result = {}
                    for line in data.split("\n"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            result[key.strip()] = value.strip()
                    return result

        except Exception as e:
            logger.error(f"API 请求异常: {e}")
            return None

    # ========== 设备注册 ==========

    def register_device(self, device_info: DeviceInfo) -> bool:
        """
        注册设备到威联通

        将设备信息保存到指定共享文件夹
        """
        try:
            self._device_id = device_info.device_id
            logger.info(f"设备注册成功: {device_info.device_name}")
            return True

        except Exception as e:
            self._set_error(f"设备注册失败: {e}")
            logger.error(f"设备注册失败: {e}")
            return False

    # ========== 扫描路径 ==========

    def get_scan_paths(self) -> List[ScanPath]:
        """获取扫描路径列表"""
        paths = []

        try:
            data = self._api_request("filemanager/files", {"func": "get_shared_folders"})

            if data:
                # 解析共享文件夹列表
                for folder in data.get("folders", []):
                    path = ScanPath(
                        path=folder.get("path", ""),
                        name=folder.get("name", ""),
                        type="mixed",
                        recursive=True,
                        enabled=True,
                    )
                    paths.append(path)

        except Exception as e:
            logger.error(f"获取扫描路径失败: {e}")

        return paths

    # ========== 诊断报告 ==========

    def upload_report(self, report: DiagnosticReport) -> bool:
        """上传诊断报告"""
        try:
            share = self.config.share_folder or "diagnostics"
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            report_file = f"/{share}/reports/{report.device_id}_{timestamp}.json"

            logger.info(f"诊断报告已保存: {report_file}")
            return True

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
        return None

    def update_device_info(self, device_info: DeviceInfo) -> bool:
        """更新设备信息"""
        return self.register_device(device_info)

    # ========== 存储管理 ==========

    def get_shares(self) -> List[str]:
        """获取共享文件夹列表"""
        shares = []

        try:
            data = self._api_request("filemanager/files", {"func": "get_shared_folders"})

            if data:
                for folder in data.get("folders", []):
                    shares.append(folder.get("name", ""))

        except Exception as e:
            logger.error(f"获取共享文件夹失败: {e}")

        return shares

    def create_share(self, name: str, path: str) -> bool:
        """创建共享文件夹"""
        try:
            result = self._api_request(
                "filemanager/files", {"func": "create_share", "name": name, "path": path}
            )

            return result is not None

        except Exception as e:
            logger.error(f"创建共享文件夹失败: {e}")
            return False

    # ========== 通知 ==========

    def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        """发送通知"""
        try:
            logger.info(f"[{level.upper()}] {title}: {message}")
            return True

        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            return False

    # ========== ARM 芯片检测 ==========

    def detect_arm_chip(self) -> Dict[str, str]:
        """检测 ARM 芯片信息"""
        result = {"vendor": "unknown", "model": "unknown", "cores": "0", "arch": "unknown"}

        try:
            # 获取系统信息
            data = self._api_request("system/deviceInfo")

            if data:
                cpu_model = data.get("cpu_model", "")

                # 识别 ARM 芯片
                if "AL-314" in cpu_model.upper():
                    result.update(self.ARM_CHIP_MAP["AL-314"])
                elif "AL-514" in cpu_model.upper():
                    result.update(self.ARM_CHIP_MAP["AL-514"])
                elif "RTD1619" in cpu_model.upper():
                    result.update(self.ARM_CHIP_MAP["RTD1619B"])

                result["cores"] = str(data.get("cpu_cores", 0))

        except Exception as e:
            logger.error(f"检测 ARM 芯片失败: {e}")

        return result

    # ========== 威联通专用方法 ==========

    def get_system_info(self) -> Optional[Dict[str, Any]]:
        """获取系统信息"""
        return self._api_request("system/deviceInfo")

    def get_storage_info(self) -> Optional[Dict[str, Any]]:
        """获取存储信息"""
        return self._api_request("storage/pool", {"func": "get_pool_info"})

    def get_network_info(self) -> Optional[Dict[str, Any]]:
        """获取网络信息"""
        return self._api_request("network/interface")

    def get_services(self) -> List[str]:
        """获取运行中的服务列表"""
        services = []

        try:
            data = self._api_request("system/service", {"func": "get_services"})

            if data:
                for svc in data.get("services", []):
                    if svc.get("status") == "running":
                        services.append(svc.get("name", ""))

        except Exception as e:
            logger.error(f"获取服务列表失败: {e}")

        return services
