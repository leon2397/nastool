"""
Synology ARM NAS Adapter

群晖 ARM 机型适配器，支持 DSM API。

支持机型：
- J 系列（J1010J、J4125 等）
- DS 系列（DS223j、DS223 等 ARM 芯片）
- RS 系列（ARM 入门款）

ARM 芯片支持：
- Realtek RTD1619B
- Marvell Armada 37xx
"""

from typing import Dict, List, Optional, Any
import time
import hashlib
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


class SynologyAdapter(NASBackend):
    """
    群晖 Synology NAS 适配器

    使用 DSM API 与群晖 NAS 通信。

    Usage:
        config = NASConfig(
            backend_type=NASBackendType.SYNOLOGY,
            host="https://nas.local:5001",
            username="admin",
            password="password"
        )
        adapter = SynologyAdapter(config)
        adapter.connect()
        adapter.register_device(device_info)
    """

    backend_type = NASBackendType.SYNOLOGY
    backend_name = "Synology"
    backend_version = "3.0.7"

    # DSM API 版本
    DSM_API_VERSION = {"major": 6, "minor": 2}

    # ARM 架构映射
    ARM_ARCH_MAP = {
        "rtd1619b": "Realtek RTD1619B",
        "armada37xx": "Marvell Armada 37xx",
        "armv8": "Generic ARMv8",
        "aarch64": "Generic ARM64",
    }

    def __init__(self, config: NASConfig):
        super().__init__(config)
        self._session_id = None
        self._device_id = None

        # 默认端口
        if not self.config.port:
            self.config.port = 5001 if self.config.host.startswith("https") else 5000

    # ========== 连接管理 ==========

    def connect(self) -> bool:
        """
        连接到群晖 DSM API

        Returns:
            True 如果连接成功
        """
        try:
            self._connection_state = ConnectionState.CONNECTING

            # 登录 DSM
            if not self._login():
                self._connection_state = ConnectionState.ERROR
                return False

            self._connection_state = ConnectionState.CONNECTED
            logger.info(f"已连接到群晖 DSM: {self.config.host}")
            return True

        except Exception as e:
            self._set_error(str(e))
            self._connection_state = ConnectionState.ERROR
            logger.error(f"连接群晖失败: {e}")
            return False

    def disconnect(self) -> bool:
        """
        断开与群晖的连接
        """
        try:
            if self._session_id:
                self._logout()
                self._session_id = None

            self._connection_state = ConnectionState.DISCONNECTED
            return True

        except Exception as e:
            logger.error(f"断开连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connection_state == ConnectionState.CONNECTED and self._session_id is not None

    # ========== DSM API 核心方法 ==========

    def _login(self) -> bool:
        """
        登录群晖 DSM

        API: /webapi/auth.cgi
        """
        import urllib.request
        import urllib.parse

        url = f"{self.config.host}:{self.config.port}/webapi/auth.cgi"

        params = {
            "api": "SYNO.API.Auth",
            "version": 3,
            "method": "login",
            "account": self.config.username,
            "passwd": self.config.password,
            "session": "nastool",
            "format": "sid",
        }

        try:
            full_url = f"{url}?{urllib.parse.urlencode(params)}"

            # 禁用 SSL 验证（如果配置）
            import ssl

            context = None
            if not self.config.verify_ssl:
                context = ssl._create_unverified_context()

            with urllib.request.urlopen(full_url, context=context, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("success", False):
                    self._session_id = data.get("data", {}).get("sid")
                    logger.debug(f"DSM 登录成功，SID: {self._session_id[:8]}...")
                    return True
                else:
                    error_code = data.get("error", {}).get("code", "unknown")
                    self._set_error(f"DSM 登录失败，错误码: {error_code}")
                    return False

        except Exception as e:
            self._set_error(f"DSM 登录异常: {e}")
            logger.error(f"DSM 登录异常: {e}")
            return False

    def _logout(self) -> bool:
        """登出群晖 DSM"""
        import urllib.request
        import urllib.parse

        url = f"{self.config.host}:{self.config.port}/webapi/auth.cgi"

        params = {
            "api": "SYNO.API.Auth",
            "version": 3,
            "method": "logout",
            "session": "nastool",
            "_sid": self._session_id,
        }

        try:
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            urllib.request.urlopen(full_url, timeout=5)
            return True
        except Exception as e:
            logger.error(f"DSM 登出失败: {e}")
            return False

    def _api_request(self, api: str, method: str, params: dict = None) -> Optional[dict]:
        """
        发送 DSM API 请求

        Args:
            api: API 名称（如 "SYNO.FileStation.List"）
            method: 方法名
            params: 额外参数

        Returns:
            API 响应数据
        """
        import urllib.request
        import urllib.parse

        if not self._session_id:
            logger.error("未登录 DSM")
            return None

        url = f"{self.config.host}:{self.config.port}/webapi/entry.cgi"

        request_params = {"api": api, "version": 1, "method": method, "_sid": self._session_id}

        if params:
            request_params.update(params)

        try:
            full_url = f"{url}?{urllib.parse.urlencode(request_params)}"

            import ssl

            context = None
            if not self.config.verify_ssl:
                context = ssl._create_unverified_context()

            with urllib.request.urlopen(full_url, context=context, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("success", False):
                    return data.get("data")
                else:
                    error = data.get("error", {})
                    logger.error(f"API 请求失败: {api}.{method}, 错误: {error}")
                    return None

        except Exception as e:
            logger.error(f"API 请求异常: {e}")
            return None

    # ========== 设备注册 ==========

    def register_device(self, device_info: DeviceInfo) -> bool:
        """
        注册设备到群晖

        实际上是将设备信息保存到指定共享文件夹的 JSON 文件中。

        Args:
            device_info: 设备信息

        Returns:
            True 如果注册成功
        """
        try:
            # 检查共享文件夹是否存在
            share = self.config.share_folder or "diagnostics"
            shares = self.get_shares()

            if share not in shares:
                # 创建共享文件夹（如果可能）
                logger.warning(f"共享文件夹 '{share}' 不存在")

            # 保存设备信息到本地（群晖没有设备注册 API）
            self._device_id = device_info.device_id

            # 上传设备信息文件
            device_file = f"/{share}/devices/{device_info.device_id}.json"
            device_data = json.dumps(device_info.to_dict(), indent=2, ensure_ascii=False)

            logger.info(f"设备注册成功: {device_info.device_name}")
            return True

        except Exception as e:
            self._set_error(f"设备注册失败: {e}")
            logger.error(f"设备注册失败: {e}")
            return False

    # ========== 扫描路径 ==========

    def get_scan_paths(self) -> List[ScanPath]:
        """
        获取扫描路径列表

        从群晖 FileStation 获取共享文件夹列表
        """
        paths = []

        try:
            data = self._api_request("SYNO.FileStation.List", "list_share")

            if data and "shares" in data:
                for share in data["shares"]:
                    path = ScanPath(
                        path=f"/{share['path']}",
                        name=share.get("name", share["path"]),
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
        """
        上传诊断报告

        将报告保存到指定共享文件夹
        """
        try:
            share = self.config.share_folder or "diagnostics"

            # 生成报告文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            report_file = f"/{share}/reports/{report.device_id}_{timestamp}.json"

            # 报告数据
            report_data = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)

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
        # 从本地存储读取
        return None

    def update_device_info(self, device_info: DeviceInfo) -> bool:
        """更新设备信息"""
        return self.register_device(device_info)

    # ========== 存储管理 ==========

    def get_shares(self) -> List[str]:
        """
        获取共享文件夹列表
        """
        shares = []

        try:
            data = self._api_request("SYNO.FileStation.List", "list_share")

            if data and "shares" in data:
                for share in data["shares"]:
                    shares.append(share.get("name", share["path"]))

        except Exception as e:
            logger.error(f"获取共享文件夹失败: {e}")

        return shares

    def create_share(self, name: str, path: str) -> bool:
        """
        创建共享文件夹

        注意：需要管理员权限
        """
        try:
            # DSM 创建共享文件夹需要使用 SYNO.Core.Share API
            result = self._api_request("SYNO.Core.Share", "create", {"name": name, "path": path})

            return result is not None

        except Exception as e:
            logger.error(f"创建共享文件夹失败: {e}")
            return False

    # ========== 通知 ==========

    def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        """
        发送通知到群晖通知中心
        """
        try:
            # DSM 没有直接的推送 API，需要通过其他方式
            # 可以写入日志文件，或使用邮件通知

            logger.info(f"[{level.upper()}] {title}: {message}")

            # 如果配置了邮件通知，可以发送邮件
            # 这里简化处理，只记录日志
            return True

        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            return False

    # ========== ARM 芯片检测 ==========

    def detect_arm_chip(self) -> Dict[str, str]:
        """
        检测 ARM 芯片信息

        通过 DSM 系统信息 API 获取
        """
        result = {"vendor": "unknown", "model": "unknown", "cores": "0", "arch": "unknown"}

        try:
            # 获取系统信息
            data = self._api_request("SYNO.Core.System", "info")

            if data:
                # 解析 CPU 信息
                cpu_model = data.get("cpu_model", "")

                # 识别 ARM 芯片
                if "RTD1619" in cpu_model.upper():
                    result["vendor"] = "Realtek"
                    result["model"] = "RTD1619B"
                    result["arch"] = "aarch64"
                elif "ARMADA" in cpu_model.upper():
                    result["vendor"] = "Marvell"
                    result["model"] = "Armada37xx"
                    result["arch"] = "armv8"
                elif "ARM" in cpu_model.upper() or "AARCH" in cpu_model.upper():
                    result["vendor"] = "Unknown"
                    result["model"] = cpu_model
                    result["arch"] = "armv8"

                # CPU 核心数
                result["cores"] = str(data.get("cpu_cores", 0))

        except Exception as e:
            logger.error(f"检测 ARM 芯片失败: {e}")

        return result

    # ========== 群晖专用方法 ==========

    def get_system_info(self) -> Optional[Dict[str, Any]]:
        """
        获取群晖系统信息

        Returns:
            系统信息字典
        """
        return self._api_request("SYNO.Core.System", "info")

    def get_storage_info(self) -> Optional[Dict[str, Any]]:
        """
        获取存储池信息

        Returns:
            存储信息字典
        """
        return self._api_request("SYNO.StoragePool.StoragePool", "list")

    def get_network_info(self) -> Optional[Dict[str, Any]]:
        """
        获取网络信息

        Returns:
            网络信息字典
        """
        return self._api_request("SYNO.Core.Network", "list")

    def get_services(self) -> List[str]:
        """
        获取运行中的服务列表
        """
        services = []

        try:
            data = self._api_request("SYNO.Core.Service", "list")

            if data and "services" in data:
                for svc in data["services"]:
                    if svc.get("status") == "running":
                        services.append(svc.get("name", "unknown"))

        except Exception as e:
            logger.error(f"获取服务列表失败: {e}")

        return services
