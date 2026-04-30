# -*- coding: utf-8 -*-
"""
HTTP Connection Pool Manager

提供 HTTP 连接池功能，复用连接，提高性能。

Usage:
    from nastool_adapters.utils.pool import ConnectionPoolManager, get_pool_manager

    # 获取全局连接池管理器
    pool_manager = get_pool_manager()

    # 或者创建专用连接池
    pool = ConnectionPoolManager(pool_size=10, timeout=30, max_retries=3)
"""

import urllib3
from typing import Optional, Dict, Any
from urllib3 import PoolManager, Retry
from urllib3.exceptions import HTTPError, ConnectTimeoutError, NewConnectionError


class ConnectionPoolManager:
    """
    HTTP 连接池管理器

    使用 urllib3 PoolManager 管理 HTTP 连接池，
    支持连接复用、超时配置和自动重试。
    """

    def __init__(
        self,
        pool_size: int = 10,
        max_pool_size: int = 20,
        timeout: float = 30.0,
        max_retries: int = 3,
        pool_block: bool = False
    ):
        """
        初始化连接池管理器

        Args:
            pool_size: 每个主机的初始连接池大小
            max_pool_size: 每个主机的最大连接池大小
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            pool_block: 连接池满时是否阻塞
        """
        self.pool_size = pool_size
        self.max_pool_size = max_pool_size
        self.timeout = timeout
        self.max_retries = max_retries
        self.pool_block = pool_block

        self._pool_manager: Optional[PoolManager] = None
        self._init_pool_manager()

    def _init_pool_manager(self):
        """初始化连接池"""
        retry_config = Retry(
            total=self.max_retries,
            connect=self.max_retries,
            read=self.max_retries,
            redirect=self.max_retries,
            status=self.max_retries,
            raise_on_status=False,
            backoff_factor=0.5
        )

        self._pool_manager = PoolManager(
            num_pools=self.pool_size,
            maxsize=self.max_pool_size,
            block=self.pool_block,
            timeout=self.timeout,
            retries=retry_config,
            headers={
                "User-Agent": "NASTool-HTTPClient/4.0"
            }
        )

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None
    ) -> Optional[urllib3.response.HTTPResponse]:
        """
        发送 HTTP 请求（使用连接池）

        Args:
            method: 请求方法 (GET, POST, etc.)
            url: 请求 URL
            headers: 请求头
            body: 请求体
            timeout: 请求超时（秒），覆盖默认超时
            retries: 最大重试次数，覆盖默认重试次数

        Returns:
            HTTP 响应或 None
        """
        if not self._pool_manager:
            raise RuntimeError("连接池未初始化")

        try:
            response = self._pool_manager.request(
                method=method,
                url=url,
                headers=headers,
                body=body,
                timeout=timeout or self.timeout,
                retries=retries if retries is not None else self.max_retries,
                redirect=True,
                preload_content=False
            )
            return response
        except (ConnectTimeoutError, NewConnectionError) as e:
            print(f"[CONNECTION ERROR] 连接失败: {e}")
            raise
        except HTTPError as e:
            print(f"[HTTP ERROR] HTTP 请求错误: {e}")
            raise
        except Exception as e:
            print(f"[ERROR] 请求异常: {e}")
            raise

    def get(self, url: str, headers: Optional[Dict[str, str]] = None,
            timeout: Optional[float] = None) -> Optional[urllib3.response.HTTPResponse]:
        """
        发送 GET 请求

        Args:
            url: 请求 URL
            headers: 请求头
            timeout: 请求超时（秒）

        Returns:
            HTTP 响应或 None
        """
        return self.request("GET", url, headers=headers, timeout=timeout)

    def post(self, url: str, body: Optional[Any] = None,
             headers: Optional[Dict[str, str]] = None,
             timeout: Optional[float] = None) -> Optional[urllib3.response.HTTPResponse]:
        """
        发送 POST 请求

        Args:
            url: 请求 URL
            body: 请求体
            headers: 请求头
            timeout: 请求超时（秒）

        Returns:
            HTTP 响应或 None
        """
        return self.request("POST", url, headers=headers, body=body, timeout=timeout)

    def put(self, url: str, body: Optional[Any] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[float] = None) -> Optional[urllib3.response.HTTPResponse]:
        """
        发送 PUT 请求

        Args:
            url: 请求 URL
            body: 请求体
            headers: 请求头
            timeout: 请求超时（秒）

        Returns:
            HTTP 响应或 None
        """
        return self.request("PUT", url, headers=headers, body=body, timeout=timeout)

    def delete(self, url: str, headers: Optional[Dict[str, str]] = None,
               timeout: Optional[float] = None) -> Optional[urllib3.response.HTTPResponse]:
        """
        发送 DELETE 请求

        Args:
            url: 请求 URL
            headers: 请求头
            timeout: 请求超时（秒）

        Returns:
            HTTP 响应或 None
        """
        return self.request("DELETE", url, headers=headers, timeout=timeout)

    def clear(self):
        """清空连接池"""
        if self._pool_manager:
            self._pool_manager.clear()

    def close(self):
        """关闭连接池"""
        if self._pool_manager:
            self._pool_manager.clear()
            self._pool_manager = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


class PoolConfig:
    """连接池配置类"""

    def __init__(
        self,
        pool_size: int = 10,
        max_pool_size: int = 20,
        timeout: float = 30.0,
        max_retries: int = 3,
        pool_block: bool = False,
        enable_pool: bool = True
    ):
        """
        初始化连接池配置

        Args:
            pool_size: 每个主机的初始连接池大小
            max_pool_size: 每个主机的最大连接池大小
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            pool_block: 连接池满时是否阻塞
            enable_pool: 是否启用连接池
        """
        self.pool_size = pool_size
        self.max_pool_size = max_pool_size
        self.timeout = timeout
        self.max_retries = max_retries
        self.pool_block = pool_block
        self.enable_pool = enable_pool


DEFAULT_POOL_CONFIG = PoolConfig(
    pool_size=10,
    max_pool_size=20,
    timeout=30.0,
    max_retries=3,
    pool_block=False,
    enable_pool=True
)

SMALL_POOL_CONFIG = PoolConfig(
    pool_size=5,
    max_pool_size=10,
    timeout=10.0,
    max_retries=2,
    pool_block=False,
    enable_pool=True
)

LARGE_POOL_CONFIG = PoolConfig(
    pool_size=20,
    max_pool_size=50,
    timeout=60.0,
    max_retries=5,
    pool_block=False,
    enable_pool=True
)


_pool_manager_instance: Optional[ConnectionPoolManager] = None
_pool_config_instance: Optional[PoolConfig] = None


def get_pool_manager(pool_config: Optional[PoolConfig] = None) -> ConnectionPoolManager:
    """
    获取全局连接池管理器实例

    Args:
        pool_config: 连接池配置（可选，使用默认配置）

    Returns:
        连接池管理器实例
    """
    global _pool_manager_instance, _pool_config_instance

    config = pool_config or _pool_config_instance or DEFAULT_POOL_CONFIG

    if _pool_manager_instance is None or pool_config is not None:
        if _pool_manager_instance:
            _pool_manager_instance.close()

        _pool_manager_instance = ConnectionPoolManager(
            pool_size=config.pool_size,
            max_pool_size=config.max_pool_size,
            timeout=config.timeout,
            max_retries=config.max_retries,
            pool_block=config.pool_block
        )
        _pool_config_instance = config

    return _pool_manager_instance


def set_pool_config(pool_config: PoolConfig):
    """
    设置全局连接池配置

    Args:
        pool_config: 连接池配置
    """
    global _pool_config_instance
    _pool_config_instance = pool_config


def clear_pool_manager():
    """清空全局连接池管理器"""
    global _pool_manager_instance
    if _pool_manager_instance:
        _pool_manager_instance.close()
        _pool_manager_instance = None
