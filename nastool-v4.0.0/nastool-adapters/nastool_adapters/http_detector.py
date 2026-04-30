# -*- coding: utf-8 -*-
"""
HTTP Remote Detector

支持通过 HTTP API 远程检测设备。
用于跨网段设备检测和 relay_server 集成。

Usage:
    detector = RemoteHTTPDetector("http://192.168.1.100:8000")
    results = detector.run_diagnosis()
"""

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from nastool_core.checks import CheckResult, CheckSeverity, CheckCategory
from nastool_adapters.utils.retry import retry_on_network_error, RetryConfig, DEFAULT_RETRY_CONFIG
from nastool_adapters.utils.pool import ConnectionPoolManager, PoolConfig, DEFAULT_POOL_CONFIG, get_pool_manager


@dataclass
class RemoteDeviceInfo:
    """远程设备信息"""
    device_id: str
    device_name: str
    hostname: str
    ip_address: str
    backend_type: str
    backend_version: str
    cpu_model: str
    cpu_cores: int
    memory_total: int


class RemoteHTTPDetector:
    """
    HTTP 远程检测器

    通过 HTTP API 与远程设备通信，执行诊断检测。
    支持连接池、重试机制。
    """

    ENDPOINTS = {
        "health": "/api/health",
        "device_info": "/api/device/info",
        "diagnose": "/api/diagnose",
        "diagnose_full": "/api/diagnose/full",
        "checks": "/api/checks",
        "benchmark": "/api/benchmark",
    }

    def __init__(self, target_url: str, api_key: Optional[str] = None, timeout: int = 30,
                 retry_config: Optional[RetryConfig] = None,
                 pool_config: Optional[PoolConfig] = None,
                 use_pool: bool = True):
        """
        初始化远程检测器

        Args:
            target_url: 目标 URL，如 http://192.168.1.100:8000
            api_key: API 密钥（可选）
            timeout: 请求超时（秒）
            retry_config: 重试配置（可选，默认使用 DEFAULT_RETRY_CONFIG）
            pool_config: 连接池配置（可选，默认使用 DEFAULT_POOL_CONFIG）
            use_pool: 是否使用连接池（默认 True）
        """
        self.target_url = target_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.retry_config = retry_config or DEFAULT_RETRY_CONFIG
        self.pool_config = pool_config or DEFAULT_POOL_CONFIG
        self.use_pool = use_pool and self.pool_config.enable_pool

        self._connected = False
        self._device_info: Optional[RemoteDeviceInfo] = None
        self._pool_manager: Optional[ConnectionPoolManager] = None

        if self.use_pool:
            self._pool_manager = ConnectionPoolManager(
                pool_size=self.pool_config.pool_size,
                max_pool_size=self.pool_config.max_pool_size,
                timeout=self.pool_config.timeout,
                max_retries=self.pool_config.max_retries,
                pool_block=self.pool_config.pool_block
            )

    def _url(self, path: str) -> str:
        """构建完整 URL"""
        return f"{self.target_url}{path}"

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NASTool-Remote/4.0"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request_with_pool(self, method: str, path: str,
                          data: Optional[Dict] = None) -> Optional[Dict]:
        """使用连接池发送 HTTP 请求"""
        url = self._url(path)
        headers = self._get_headers()

        try:
            if method == "GET":
                response = self._pool_manager.get(url, headers=headers, timeout=self.timeout)
            else:
                body = json.dumps(data).encode('utf-8') if data else b'{}'
                response = self._pool_manager.post(url, headers=headers, body=body, timeout=self.timeout)

            if response:
                return json.loads(response.data.decode('utf-8'))
            return None

        except Exception as e:
            print(f"[POOL ERROR] 请求失败: {e}")
            return None

    def _request_no_pool(self, method: str, path: str,
                        data: Optional[Dict] = None) -> Optional[Dict]:
        """不使用连接池发送 HTTP 请求（使用 urllib）"""
        import urllib.request
        import urllib.error

        url = self._url(path)
        headers = self._get_headers()

        try:
            if method == "GET":
                req = urllib.request.Request(url, headers=headers)
            else:
                body = json.dumps(data).encode('utf-8') if data else b'{}'
                req = urllib.request.Request(url, data=body, headers=headers, method=method)

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))

        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
                print(f"HTTP {e.code}: {error_body}")
            except Exception:
                print(f"HTTP {e.code}")
            return None

        except (ConnectionError, TimeoutError, urllib.error.URLError) as e:
            print(f"[RETRY] 网络错误: {e}")
            raise

        except Exception as e:
            print(f"请求异常: {e}")
            return None

    @retry_on_network_error(max_retries=3, delay=1.0)
    def _request_with_retry(self, method: str, path: str,
                            data: Optional[Dict] = None) -> Optional[Dict]:
        """发送 HTTP 请求（带重试机制）"""
        if self.use_pool:
            return self._request_with_pool(method, path, data)
        else:
            return self._request_no_pool(method, path, data)

    def _request(self, method: str, path: str, data: Optional[Dict] = None,
                 use_retry: bool = True) -> Optional[Dict]:
        """
        发送 HTTP 请求

        Args:
            method: 请求方法 (GET, POST, etc.)
            path: API 路径
            data: 请求数据
            use_retry: 是否使用重试机制

        Returns:
            响应数据或 None
        """
        if use_retry and self.retry_config.enable:
            return self._request_with_retry(method, path, data)
        else:
            if self.use_pool:
                return self._request_with_pool(method, path, data)
            else:
                return self._request_no_pool(method, path, data)

    def connect(self, use_retry: bool = True) -> bool:
        """
        连接到远程设备

        Args:
            use_retry: 是否使用重试机制
        """
        result = self._request("GET", self.ENDPOINTS["health"], use_retry=use_retry)

        if result:
            self._connected = True
            print(f"[OK] 已连接到 {self.target_url}")
            if self.use_pool:
                print(f"[POOL] 使用连接池: pool_size={self.pool_config.pool_size}, max_pool_size={self.pool_config.max_pool_size}")
            return True
        else:
            print(f"[X] 无法连接到 {self.target_url}")
            return False

    def disconnect(self):
        """断开连接"""
        self._connected = False
        if self._pool_manager:
            self._pool_manager.clear()

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected

    def get_device_info(self, use_retry: bool = True) -> Optional[RemoteDeviceInfo]:
        """
        获取远程设备信息

        Args:
            use_retry: 是否使用重试机制
        """
        if not self._connected:
            print("请先调用 connect()")
            return None

        result = self._request("GET", self.ENDPOINTS["device_info"], use_retry=use_retry)

        if result:
            self._device_info = RemoteDeviceInfo(
                device_id=result.get("device_id", ""),
                device_name=result.get("device_name", ""),
                hostname=result.get("hostname", ""),
                ip_address=result.get("ip_address", ""),
                backend_type=result.get("backend_type", ""),
                backend_version=result.get("backend_version", ""),
                cpu_model=result.get("cpu_model", ""),
                cpu_cores=result.get("cpu_cores", 0),
                memory_total=result.get("memory_total", 0),
            )
            return self._device_info

        return None

    def run_diagnosis(self, full_mode: bool = False,
                      use_retry: bool = True) -> List[CheckResult]:
        """
        运行远程诊断

        Args:
            full_mode: 是否运行完整诊断（含基准测试）
            use_retry: 是否使用重试机制

        Returns:
            检测结果列表
        """
        if not self._connected:
            print("请先调用 connect()")
            return []

        endpoint = self.ENDPOINTS["diagnose_full"] if full_mode else self.ENDPOINTS["diagnose"]
        result = self._request("GET", endpoint, use_retry=use_retry)

        if not result:
            print("诊断请求失败")
            return []

        results = []
        for item in result.get("results", []):
            try:
                sev = CheckSeverity(item.get("severity", "info").lower())
            except ValueError:
                sev = CheckSeverity.INFO
            try:
                cat = CheckCategory(item.get("category", "system").lower())
            except ValueError:
                cat = CheckCategory.SYSTEM

            check = CheckResult(
                check_id=item.get("check_id", ""),
                title=item.get("title") or item.get("name", ""),
                category=cat,
                severity=sev,
                passed=item.get("passed", True),
                current=str(item.get("value") or item.get("current", "")),
                expected=str(item.get("threshold") or item.get("expected", "")),
                message=item.get("message") or item.get("summary", ""),
                details=item.get("details") or {},
            )
            results.append(check)

        return results

    def run_checks(self, categories: Optional[List[str]] = None,
                  use_retry: bool = True) -> List[CheckResult]:
        """
        运行特定类别的检测

        Args:
            categories: 检测类别列表，如 ["ai", "nas", "network"]
            use_retry: 是否使用重试机制

        Returns:
            检测结果列表
        """
        if not self._connected:
            print("请先调用 connect()")
            return []

        params = {}
        if categories:
            params["categories"] = ",".join(categories)

        query = "&".join([f"{k}={v}" for k, v in params.items()])
        endpoint = self.ENDPOINTS["checks"]
        if query:
            endpoint += f"?{query}"

        result = self._request("GET", endpoint, use_retry=use_retry)

        if not result:
            return []

        results = []
        for item in result.get("checks", []):
            try:
                sev = CheckSeverity(item.get("severity", "info").lower())
            except ValueError:
                sev = CheckSeverity.INFO
            try:
                cat = CheckCategory(item.get("category", "system").lower())
            except ValueError:
                cat = CheckCategory.SYSTEM

            check = CheckResult(
                check_id=item.get("check_id", ""),
                title=item.get("title") or item.get("name", ""),
                category=cat,
                severity=sev,
                passed=item.get("passed", True),
                current=str(item.get("value") or item.get("current", "")),
                expected=str(item.get("threshold") or item.get("expected", "")),
                message=item.get("message") or item.get("summary", ""),
                details=item.get("details") or {},
            )
            results.append(check)

        return results

    def run_benchmark(self, model: str = "mobilenetv2",
                    use_retry: bool = True) -> Dict[str, Any]:
        """
        运行远程基准测试

        Args:
            model: 基准测试模型
            use_retry: 是否使用重试机制

        Returns:
            基准测试结果
        """
        if not self._connected:
            print("请先调用 connect()")
            return {}

        result = self._request("POST", self.ENDPOINTS["benchmark"],
                              {"model": model}, use_retry=use_retry)

        return result or {}

    def quick_diagnosis(self, use_retry: bool = True) -> Dict[str, Any]:
        """
        快速诊断（连接 + 设备信息 + 诊断）

        Args:
            use_retry: 是否使用重试机制

        Returns:
            诊断结果字典
        """
        if not self.connect(use_retry=use_retry):
            return {"error": "连接失败"}

        device_info = self.get_device_info(use_retry=use_retry)
        results = self.run_diagnosis(full_mode=False, use_retry=use_retry)

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        return {
            "device": device_info.__dict__ if device_info else {},
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
            },
            "results": [r.__dict__ for r in results]
        }

    def close(self):
        """关闭连接池"""
        if self._pool_manager:
            self._pool_manager.close()
            self._pool_manager = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
        self.disconnect()


def detect_remote_target(target: str,
                        retry_config: Optional[RetryConfig] = None,
                        pool_config: Optional[PoolConfig] = None) -> RemoteHTTPDetector:
    """
    自动检测目标类型并返回对应的检测器

    Args:
        target: 目标地址 (http://host:port 或 user@host)
        retry_config: 重试配置（可选）
        pool_config: 连接池配置（可选）

    Returns:
        对应的检测器实例
    """
    if target.startswith("http://") or target.startswith("https://"):
        return RemoteHTTPDetector(target, retry_config=retry_config,
                                 pool_config=pool_config)
    elif "@" in target:
        raise NotImplementedError("SSH 目标需要通过 relay_server 中转")
    else:
        return RemoteHTTPDetector(f"http://{target}", retry_config=retry_config,
                                 pool_config=pool_config)
