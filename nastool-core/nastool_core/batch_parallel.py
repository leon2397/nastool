"""
batch_parallel.py - 批量检测并行优化

优化目标：
- 设备间完全并行（当前是半并行）
- 结果流式输出（检测完一个输出一个）
- 进度条实时更新
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from nastool_common.logger import get_logger
from nastool_core.device_manager import DeviceManager
from nastool_core.async_executor import AsyncCheckExecutor
from nastool_core.check_timeouts import CHECK_TIMEOUTS

logger = get_logger(__name__)


@dataclass
class BatchDeviceResult:
    """单个设备的批量检测结果"""
    device_id: str
    success: bool
    results: List[Dict[str, Any]]
    elapsed: float
    error: Optional[str] = None


class BatchParallelExecutor:
    """
    批量检测并行执行器。
    
    特性：
    - 设备间完全并行
    - 结果流式输出
    - 实时进度更新
    - 资源控制（并发设备数、每设备并发检测数）
    """
    
    def __init__(
        self,
        max_concurrent_devices: int = 5,
        max_concurrent_checks_per_device: int = 10,
        default_timeout: float = 30.0
    ):
        self.max_concurrent_devices = max_concurrent_devices
        self.max_concurrent_checks_per_device = max_concurrent_checks_per_device
        self.default_timeout = default_timeout
        
    async def diagnose_device(
        self,
        device_id: str,
        check_ids: List[str],
        on_device_complete: Optional[Callable[[BatchDeviceResult], None]] = None
    ) -> BatchDeviceResult:
        """
        对单个设备进行并行检测。
        
        Args:
            device_id: 设备ID
            check_ids: 检测项列表
            on_device_complete: 设备检测完成回调
            
        Returns:
            BatchDeviceResult
        """
        start = time.perf_counter()
        
        try:
            # 创建设备专用的执行器
            executor = AsyncCheckExecutor(
                max_concurrent=self.max_concurrent_checks_per_device,
                default_timeout=self.default_timeout
            )
            
            # 并行执行所有检测项
            results = await executor.run_checks_parallel(
                check_ids,
                timeouts=CHECK_TIMEOUTS
            )
            
            elapsed = time.perf_counter() - start
            
            result = BatchDeviceResult(
                device_id=device_id,
                success=True,
                results=results,
                elapsed=elapsed
            )
            
        except Exception as e:
            elapsed = time.perf_counter() - start
            result = BatchDeviceResult(
                device_id=device_id,
                success=False,
                results=[],
                elapsed=elapsed,
                error=str(e)
            )
        
        # 流式回调
        if on_device_complete:
            on_device_complete(result)
        
        return result
    
    async def batch_diagnose(
        self,
        device_ids: List[str],
        check_ids: List[str],
        on_device_complete: Optional[Callable[[BatchDeviceResult], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[BatchDeviceResult]:
        """
        批量检测（设备间完全并行）。
        
        Args:
            device_ids: 设备ID列表
            check_ids: 检测项列表
            on_device_complete: 单个设备完成回调（流式输出）
            on_progress: 进度回调 (current, total)
            
        Returns:
            所有设备的检测结果列表
        """
        total = len(device_ids)
        completed = 0
        
        # 使用信号量控制并发设备数
        semaphore = asyncio.Semaphore(self.max_concurrent_devices)
        
        async def diagnose_with_limit(device_id: str) -> BatchDeviceResult:
            async with semaphore:
                result = await self.diagnose_device(
                    device_id, check_ids, on_device_complete
                )
                
                nonlocal completed
                completed += 1
                if on_progress:
                    on_progress(completed, total)
                
                return result
        
        # 并行执行所有设备
        tasks = [diagnose_with_limit(did) for did in device_ids]
        results = await asyncio.gather(*tasks)
        
        return results


# 便捷函数
def batch_diagnose_parallel(
    device_ids: List[str],
    check_ids: List[str],
    max_concurrent_devices: int = 5,
    max_concurrent_checks_per_device: int = 10,
    on_device_complete: Optional[Callable[[BatchDeviceResult], None]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None
) -> List[BatchDeviceResult]:
    """
    同步接口：批量检测并行执行。
    
    使用示例：
        def on_device_done(result):
            print(f"{result.device_id}: {result.elapsed:.2f}s")
        
        results = batch_diagnose_parallel(
            ["device1", "device2", "device3"],
            ["network_latency", "cpu_temperature"],
            max_concurrent_devices=3,
            on_device_complete=on_device_done
        )
    """
    executor = BatchParallelExecutor(
        max_concurrent_devices=max_concurrent_devices,
        max_concurrent_checks_per_device=max_concurrent_checks_per_device
    )
    
    return asyncio.run(executor.batch_diagnose(
        device_ids, check_ids, on_device_complete, on_progress
    ))


class BatchProgressTracker:
    """
    批量检测进度跟踪器（支持Rich进度条）。
    """
    
    def __init__(self, total_devices: int, total_checks: int):
        self.total_devices = total_devices
        self.total_checks = total_checks
        self.completed_devices = 0
        self.completed_checks = 0
        self.device_results: Dict[str, BatchDeviceResult] = {}
        
    def on_device_complete(self, result: BatchDeviceResult):
        """设备完成回调"""
        self.completed_devices += 1
        self.device_results[result.device_id] = result
        
        # 流式输出结果
        status = "✓" if result.success else "✗"
        print(f"[{status}] {result.device_id}: "
              f"{len(result.results)} checks in {result.elapsed:.2f}s")
        
    def on_check_progress(self, device_id: str, check_id: str, elapsed: float):
        """单个检测项完成回调"""
        self.completed_checks += 1
        # 可选：实时更新进度条
        
    def get_summary(self) -> Dict[str, Any]:
        """获取批量检测摘要"""
        total_elapsed = sum(r.elapsed for r in self.device_results.values())
        success_count = sum(1 for r in self.device_results.values() if r.success)
        
        return {
            "total_devices": self.total_devices,
            "completed_devices": self.completed_devices,
            "success_devices": success_count,
            "failed_devices": self.total_devices - success_count,
            "total_elapsed": total_elapsed,
            "avg_time_per_device": total_elapsed / self.total_devices if self.total_devices > 0 else 0
        }
