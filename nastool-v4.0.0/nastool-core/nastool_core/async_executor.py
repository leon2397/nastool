"""
async_executor.py - 异步检测执行器

提供并行检测能力，替换原有的顺序执行。

特性：
- 并发执行多个检测项
- 超时控制（默认30秒）
- 优雅降级（单个失败不影响整体）
- 进度回调
- 重试机制
- 详细的错误分类
"""

import asyncio
import time
import functools
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum

from nastool_common.logger import get_logger

logger = get_logger(__name__)


class CheckErrorType(Enum):
    """检测错误类型枚举"""
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    CHECK_NOT_FOUND = "check_not_found"
    CHECK_CLASS_INIT_ERROR = "check_class_init_error"
    CHECK_RUN_ERROR = "check_run_error"
    CANCELLED = "cancelled"
    SEMAPHORE_FULL = "semaphore_full"
    SYSTEM_ERROR = "system_error"


@dataclass
class CheckError:
    """检测错误详情"""
    error_type: CheckErrorType = CheckErrorType.UNKNOWN
    message: str = ""
    original_error: Optional[Exception] = None
    retry_count: int = 0
    stack_trace: Optional[str] = None


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避倍数
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}, retrying in {current_delay}s...")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} all {max_retries} retries failed")

            raise last_error
        return wrapper
    return decorator


class AsyncCheckExecutor:
    """
    异步检测执行器。

    特性：
    - 并发执行多个检测项
    - 超时控制（默认30秒）
    - 优雅降级（单个失败不影响整体）
    - 进度回调
    - 重试机制
    - 详细的错误分类
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        default_timeout: float = 30.0,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        max_retries: int = 0,
        retry_delay: float = 1.0
    ):
        """
        初始化执行器。

        Args:
            max_concurrent: 最大并发数
            default_timeout: 默认超时时间（秒）
            progress_callback: 进度回调函数(current, total)
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.progress_callback = progress_callback
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._check_get_check_exists()

    def _check_get_check_exists(self):
        """检查get_check函数是否存在"""
        try:
            from nastool_core.checks import get_check
            self._get_check = get_check
        except ImportError:
            logger.warning("nastool_core.checks.get_check not found, using alternative lookup")
            self._get_check = self._get_check_alternative

    def _get_check_alternative(self, check_id: str):
        """备选的检查获取方式"""
        from nastool_core.checks import ALL_CHECKS
        return ALL_CHECKS.get(check_id)

    def _run_sync_check(self, check_id: str, retry_count: int = 0) -> Any:
        """
        在线程中运行同步检测

        Args:
            check_id: 检测项ID
            retry_count: 当前重试次数

        Returns:
            检测结果

        Raises:
            ValueError: 检查不存在
            Exception: 检查执行错误
        """
        check_class = self._get_check(check_id)
        if not check_class:
            raise ValueError(f"Check not found: {check_id}")

        try:
            check = check_class()
        except Exception as e:
            logger.error(f"Failed to initialize check {check_id}: {e}")
            raise ValueError(f"Check class init error: {check_id}") from e

        try:
            return check.run()
        except Exception as e:
            logger.error(f"Failed to run check {check_id}: {e}")
            raise

    async def run_check_async(
        self,
        check_id: str,
        timeout: Optional[float] = None,
        retry_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        异步执行单个检测项。

        Args:
            check_id: 检测项ID
            timeout: 超时时间（秒），None则使用默认值
            retry_count: 重试次数，None则使用默认值

        Returns:
            检测结果字典，包含check_id、result、error等
        """
        retry_count = retry_count if retry_count is not None else self.max_retries
        async with self._semaphore:
            timeout = timeout or self.default_timeout
            start_time = time.perf_counter()

            last_error = None
            current_delay = self.retry_delay

            for attempt in range(retry_count + 1):
                try:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            self._run_sync_check,
                            check_id
                        ),
                        timeout=timeout
                    )

                    elapsed = time.perf_counter() - start_time
                    logger.debug(f"Check {check_id} completed in {elapsed:.2f}s (attempt {attempt + 1})")

                    return {
                        "check_id": check_id,
                        "result": result,
                        "elapsed": elapsed,
                        "error": None,
                        "error_type": None,
                        "attempts": attempt + 1
                    }

                except asyncio.TimeoutError:
                    elapsed = time.perf_counter() - start_time
                    error_msg = f"Timeout after {timeout}s"
                    logger.warning(f"Check {check_id} {error_msg} (attempt {attempt + 1})")
                    last_error = CheckError(
                        error_type=CheckErrorType.TIMEOUT,
                        message=error_msg,
                        retry_count=attempt
                    )

                except ValueError as e:
                    elapsed = time.perf_counter() - start_time
                    error_type = CheckErrorType.CHECK_NOT_FOUND if "not found" in str(e) else CheckErrorType.CHECK_CLASS_INIT_ERROR
                    logger.error(f"Check {check_id} initialization error: {e}")
                    last_error = CheckError(
                        error_type=error_type,
                        message=str(e),
                        original_error=e,
                        retry_count=attempt
                    )
                    break

                except Exception as e:
                    elapsed = time.perf_counter() - start_time
                    logger.error(f"Check {check_id} failed (attempt {attempt + 1}): {e}")
                    last_error = CheckError(
                        error_type=CheckErrorType.CHECK_RUN_ERROR,
                        message=str(e),
                        original_error=e,
                        retry_count=attempt
                    )

                if attempt < retry_count:
                    logger.info(f"Retrying {check_id} in {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= 2

            elapsed = time.perf_counter() - start_time
            return {
                "check_id": check_id,
                "result": None,
                "elapsed": elapsed,
                "error": last_error.message if last_error else "Unknown error",
                "error_type": last_error.error_type.value if last_error else CheckErrorType.UNKNOWN.value,
                "attempts": retry_count + 1
            }

    async def run_checks_parallel(
        self,
        check_ids: List[str],
        timeouts: Optional[Dict[str, float]] = None,
        retry_counts: Optional[Dict[str, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        并行执行多个检测项。

        Args:
            check_ids: 检测项ID列表
            timeouts: 各检测项的超时时间字典 {check_id: timeout}
            retry_counts: 各检测项的重试次数字典 {check_id: retry_count}

        Returns:
            检测结果列表（顺序与check_ids一致）
        """
        timeouts = timeouts or {}
        retry_counts = retry_counts or {}
        total = len(check_ids)
        completed = 0

        tasks = []
        for check_id in check_ids:
            timeout = timeouts.get(check_id)
            retry_count = retry_counts.get(check_id, self.max_retries)
            task = self.run_check_async(check_id, timeout, retry_count)
            tasks.append(task)

        results = []
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)

            completed += 1
            if self.progress_callback:
                try:
                    self.progress_callback(completed, total)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")

        result_map = {r["check_id"]: r for r in results}
        ordered_results = [result_map[check_id] for check_id in check_ids]

        return ordered_results

    def get_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取检测结果统计

        Args:
            results: 检测结果列表

        Returns:
            统计信息字典
        """
        total = len(results)
        success = sum(1 for r in results if r.get("error") is None)
        failed = total - success

        error_types = {}
        for r in results:
            error_type = r.get("error_type", CheckErrorType.UNKNOWN.value)
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": success / total if total > 0 else 0,
            "error_types": error_types,
            "total_elapsed": sum(r.get("elapsed", 0) for r in results),
            "avg_elapsed": sum(r.get("elapsed", 0) for r in results) / total if total > 0 else 0
        }


def run_checks_parallel(
    check_ids: List[str],
    max_concurrent: int = 10,
    default_timeout: float = 30.0,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    timeouts: Optional[Dict[str, float]] = None,
    max_retries: int = 0
) -> List[Dict[str, Any]]:
    """
    同步接口：并行执行检测项。

    使用示例：
        results = run_checks_parallel(
            ["network_latency", "latency_check", "internet_access"],
            max_concurrent=5,
            timeouts={"network_latency": 5.0},
            max_retries=2
        )
    """
    executor = AsyncCheckExecutor(
        max_concurrent=max_concurrent,
        default_timeout=default_timeout,
        progress_callback=progress_callback,
        max_retries=max_retries
    )

    return asyncio.run(executor.run_checks_parallel(check_ids, timeouts))