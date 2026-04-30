"""
async_executor.py - 异步检测执行器

提供并行检测能力，替换原有的顺序执行。
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from nastool_common.logger import get_logger
from nastool_core.checks import get_check

logger = get_logger(__name__)


class AsyncCheckExecutor:
    """
    异步检测执行器。
    
    特性：
    - 并发执行多个检测项
    - 超时控制（默认30秒）
    - 优雅降级（单个失败不影响整体）
    - 进度回调
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        default_timeout: float = 30.0,
        progress_callback: Optional[callable] = None
    ):
        """
        初始化执行器。
        
        Args:
            max_concurrent: 最大并发数
            default_timeout: 默认超时时间（秒）
            progress_callback: 进度回调函数(current, total)
        """
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.progress_callback = progress_callback
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    async def run_check_async(
        self,
        check_id: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        异步执行单个检测项。
        
        Args:
            check_id: 检测项ID
            timeout: 超时时间（秒），None则使用默认值
            
        Returns:
            检测结果字典，包含check_id、result、error等
        """
        async with self._semaphore:
            timeout = timeout or self.default_timeout
            start_time = time.perf_counter()
            
            try:
                # 在线程池中执行同步检测（避免阻塞事件循环）
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,  # 使用默认线程池
                        self._run_sync_check,
                        check_id
                    ),
                    timeout=timeout
                )
                
                elapsed = time.perf_counter() - start_time
                logger.debug(f"Check {check_id} completed in {elapsed:.2f}s")
                
                return {
                    "check_id": check_id,
                    "result": result,
                    "elapsed": elapsed,
                    "error": None
                }
                
            except asyncio.TimeoutError:
                elapsed = time.perf_counter() - start_time
                logger.warning(f"Check {check_id} timeout after {elapsed:.2f}s")
                return {
                    "check_id": check_id,
                    "result": None,
                    "elapsed": elapsed,
                    "error": f"Timeout after {timeout}s"
                }
                
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.error(f"Check {check_id} failed: {e}")
                return {
                    "check_id": check_id,
                    "result": None,
                    "elapsed": elapsed,
                    "error": str(e)
                }
    
    def _run_sync_check(self, check_id: str):
        """在线程中运行同步检测"""
        check_class = get_check(check_id)
        if not check_class:
            raise ValueError(f"Unknown check: {check_id}")
        
        check = check_class()
        return check.run()
    
    async def run_checks_parallel(
        self,
        check_ids: List[str],
        timeouts: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        并行执行多个检测项。
        
        Args:
            check_ids: 检测项ID列表
            timeouts: 各检测项的超时时间字典 {check_id: timeout}
            
        Returns:
            检测结果列表（顺序与check_ids一致）
        """
        timeouts = timeouts or {}
        total = len(check_ids)
        completed = 0
        
        # 创建任务
        tasks = []
        for check_id in check_ids:
            timeout = timeouts.get(check_id)
            task = self.run_check_async(check_id, timeout)
            tasks.append(task)
        
        # 执行并收集结果
        results = []
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            
            # 进度回调
            completed += 1
            if self.progress_callback:
                self.progress_callback(completed, total)
        
        # 按check_id排序（保持输入顺序）
        result_map = {r["check_id"]: r for r in results}
        ordered_results = [result_map[check_id] for check_id in check_ids]
        
        return ordered_results


# 便捷函数
def run_checks_parallel(
    check_ids: List[str],
    max_concurrent: int = 10,
    default_timeout: float = 30.0,
    progress_callback: Optional[callable] = None,
    timeouts: Optional[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    """
    同步接口：并行执行检测项。
    
    使用示例：
        results = run_checks_parallel(
            ["network_latency", "latency_check", "internet_access"],
            max_concurrent=5,
            timeouts={"network_latency": 5.0}  # 网络检测5秒超时
        )
    """
    executor = AsyncCheckExecutor(
        max_concurrent=max_concurrent,
        default_timeout=default_timeout,
        progress_callback=progress_callback
    )
    
    return asyncio.run(executor.run_checks_parallel(check_ids, timeouts))
