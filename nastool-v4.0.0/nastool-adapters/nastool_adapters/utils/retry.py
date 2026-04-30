# -*- coding: utf-8 -*-
"""
Network Retry Utilities

提供网络请求的重试机制，处理临时网络故障。

Usage:
    from nastool_adapters.utils.retry import retry_on_network_error

    @retry_on_network_error(max_retries=3, delay=1.0)
    def my_network_request():
        ...
"""

import time
import functools
from typing import Callable, Any, Optional, Tuple, Type


class NetworkRetryError(Exception):
    """网络重试错误（所有重试都失败后）"""
    pass


def retry_on_network_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    error_message: Optional[str] = None
) -> Callable:
    """
    网络请求重试装饰器

    Args:
        max_retries: 最大重试次数（默认 3 次）
        delay: 初始重试延迟（秒，默认 1.0 秒）
        backoff: 退避系数（默认 2.0，每次重试延迟翻倍）
        exceptions: 需要捕获的异常类型元组（默认捕获网络相关异常）
        error_message: 自定义错误消息

    Returns:
        装饰器函数

    Example:
        @retry_on_network_error(max_retries=3, delay=1.0)
        def fetch_data():
            return requests.get("http://example.com")

        # 或在类方法中使用
        class MyClass:
            @retry_on_network_error(max_retries=3)
            def fetch_data(self):
                return requests.get("http://example.com")
    """
    if exceptions is None:
        exceptions = (
            ConnectionError,
            TimeoutError,
            IOError,
            OSError,
        )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # 不是最后一次重试，显示重试信息
                        print(f"[RETRY] {func.__name__} 失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                        print(f"[RETRY] {current_delay:.1f} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff  # 指数退避
                    else:
                        # 所有重试都失败
                        error_msg = error_message or f"{func.__name__} 在 {max_retries + 1} 次尝试后仍然失败"
                        print(f"[FAIL] {error_msg}: {e}")
                        raise NetworkRetryError(error_msg) from e

            # 理论上不会执行到这里，但以防万一
            if last_exception:
                raise NetworkRetryError(
                    error_message or f"{func.__name__} 重试失败",
                    original_error=last_exception
                )

        return wrapper
    return decorator


def retry_with_result_check(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    result_check: Optional[Callable[[Any], bool]] = None,
    error_message: Optional[str] = None
) -> Callable:
    """
    带结果检查的重试装饰器

    当请求成功但返回无效结果时（如 None、空字典等），自动重试。

    Args:
        max_retries: 最大重试次数（默认 3 次）
        delay: 初始重试延迟（秒，默认 1.0 秒）
        backoff: 退避系数（默认 2.0，每次重试延迟翻倍）
        result_check: 结果检查函数，返回 True 表示结果有效，False 需要重试
        error_message: 自定义错误消息

    Returns:
        装饰器函数

    Example:
        @retry_with_result_check(max_retries=3, result_check=lambda x: x is not None)
        def fetch_data():
            return some_api_call()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_result = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # 检查结果是否有效
                    if result_check is None or result_check(result):
                        return result

                    # 结果无效，但不是最后一次重试
                    if attempt < max_retries:
                        print(f"[RETRY] {func.__name__} 返回无效结果 (尝试 {attempt + 1}/{max_retries + 1})")
                        print(f"[RETRY] {current_delay:.1f} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        # 所有重试都失败
                        error_msg = error_message or f"{func.__name__} 在 {max_retries + 1} 次尝试后仍然返回无效结果"
                        print(f"[FAIL] {error_msg}")
                        return result  # 返回最后一次结果，不抛出异常

                except Exception as e:
                    last_result = None
                    if attempt < max_retries:
                        print(f"[RETRY] {func.__name__} 异常 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                        print(f"[RETRY] {current_delay:.1f} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        error_msg = error_message or f"{func.__name__} 在 {max_retries + 1} 次尝试后仍然失败"
                        print(f"[FAIL] {error_msg}: {e}")
                        raise

            return last_result

        return wrapper
    return decorator


class RetryConfig:
    """重试配置类"""

    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        max_delay: float = 60.0,
        enable: bool = True
    ):
        """
        初始化重试配置

        Args:
            max_retries: 最大重试次数
            delay: 初始重试延迟（秒）
            backoff: 退避系数
            max_delay: 最大重试延迟（秒）
            enable: 是否启用重试
        """
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.max_delay = max_delay
        self.enable = enable

    def get_delay(self, attempt: int) -> float:
        """计算指定尝试次数的延迟"""
        delay = self.delay * (self.backoff ** attempt)
        return min(delay, self.max_delay)


# 默认重试配置
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    delay=1.0,
    backoff=2.0,
    max_delay=30.0
)

# 快速重试配置（用于需要快速响应的场景）
FAST_RETRY_CONFIG = RetryConfig(
    max_retries=2,
    delay=0.5,
    backoff=2.0,
    max_delay=5.0
)

# 慢速重试配置（用于需要稳定连接的场景）
SLOW_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    delay=2.0,
    backoff=2.0,
    max_delay=60.0
)