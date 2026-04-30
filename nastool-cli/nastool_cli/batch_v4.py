"""
batch_v4.py - v4.0 批量检测（完全并行优化版）

替换原有的 BatchDiagnosis，使用设备间完全并行。
"""

import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict

from nastool_core.device_manager import DeviceManager
from nastool_core.batch_parallel import (
    batch_diagnose_parallel,
    BatchParallelExecutor,
    BatchProgressTracker
)
from nastool_core.async_executor import run_checks_parallel
from nastool_core.check_timeouts import CHECK_TIMEOUTS
from nastool_common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BatchResultV4:
    """v4.0 批量检测结果"""
    device_id: str
    success: bool
    score: Optional[int] = None
    critical_count: int = 0
    warning_count: int = 0
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: str = ""


class BatchDiagnosisV4:
    """
    v4.0 批量检测（完全并行优化）。
    
    相比 v3.0 改进：
    - 设备间完全并行（Semaphore控制并发）
    - 结果流式输出（检测完一个输出一个）
    - 实时进度更新
    - 更好的资源控制
    """
    
    def __init__(
        self,
        device_manager: Optional[DeviceManager] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        self.device_manager = device_manager or DeviceManager()
        self.progress_callback = progress_callback
        
    def run(
        self,
        device_ids: List[str],
        parallel_devices: int = 5,
        parallel_checks: int = 10,
        timeout: int = 300,
        full_mode: bool = False
    ) -> Dict[str, Any]:
        """
        运行批量检测（v4.0 完全并行）。
        
        Args:
            device_ids: 设备ID列表
            parallel_devices: 最大并发设备数
            parallel_checks: 每设备最大并发检测数
            timeout: 单设备超时（秒）
            full_mode: 完整检测模式
            
        Returns:
            批量检测结果摘要
        """
        start_time = time.time()
        
        # 获取检测项列表
        from nastool_core.checks import list_checks
        check_ids = list_checks()
        
        if not full_mode:
            # 快速模式：排除耗时检测
            slow_checks = {'benchmark_cpu', 'benchmark_disk', 'benchmark_memory'}
            check_ids = [c for c in check_ids if c not in slow_checks]
        
        print(f"\n  批量检测 v4.0")
        print(f"  设备数: {len(device_ids)}")
        print(f"  检测项: {len(check_ids)}")
        print(f"  设备并发: {parallel_devices}")
        print(f"  检测并发: {parallel_checks}\n")
        
        # 进度跟踪
        tracker = BatchProgressTracker(
            total_devices=len(device_ids),
            total_checks=len(check_ids) * len(device_ids)
        )
        
        # 执行批量检测
        device_results = batch_diagnose_parallel(
            device_ids=device_ids,
            check_ids=check_ids,
            max_concurrent_devices=parallel_devices,
            max_concurrent_checks_per_device=parallel_checks,
            on_device_complete=tracker.on_device_complete,
            on_progress=lambda c, t: print(f"  进度: {c}/{t} 设备", end="\r")
        )
        
        # 计算分数
        batch_results = []
        for dr in device_results:
            if dr.success:
                score = self._calculate_score(dr.results)
                critical = sum(1 for r in dr.results 
                             if r.get('result') and r['result'].severity.value == 'critical')
                warning = sum(1 for r in dr.results 
                            if r.get('result') and r['result'].severity.value == 'warning')
            else:
                score = 0
                critical = 0
                warning = 0
            
            batch_results.append(BatchResultV4(
                device_id=dr.device_id,
                success=dr.success,
                score=score,
                critical_count=critical,
                warning_count=warning,
                error=dr.error,
                duration_ms=int(dr.elapsed * 1000),
                timestamp=datetime.now().isoformat()
            ))
        
        # 汇总
        duration_ms = int((time.time() - start_time) * 1000)
        success = sum(1 for r in batch_results if r.success)
        failed = len(batch_results) - success
        
        summary = {
            "total": len(device_ids),
            "success": success,
            "failed": failed,
            "results": [asdict(r) for r in batch_results],
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
            "config": {
                "parallel_devices": parallel_devices,
                "parallel_checks": parallel_checks,
                "full_mode": full_mode
            }
        }
        
        # 打印汇总
        print(f"\n  {'='*50}")
        print(f"  批量检测完成")
        print(f"  {'='*50}")
        print(f"  总设备: {summary['total']}")
        print(f"  成功:   {summary['success']}")
        print(f"  失败:   {summary['failed']}")
        print(f"  耗时:   {duration_ms/1000:.2f}s")
        print(f"  {'='*50}\n")
        
        return summary
    
    def _calculate_score(self, results: List[Dict]) -> int:
        """计算健康分数"""
        if not results:
            return 0
        
        passed = sum(1 for r in results 
                    if r.get('result') and r['result'].passed)
        total = len(results)
        
        if total == 0:
            return 0
        
        score = int((passed / total) * 100)
        
        # 扣分
        critical = sum(1 for r in results 
                      if r.get('result') and r['result'].severity.value == 'critical')
        warning = sum(1 for r in results 
                     if r.get('result') and r['result'].severity.value == 'warning')
        
        score -= critical * 10
        score -= warning * 3
        
        return max(0, min(100, score))


# 便捷函数
def run_batch_v4(
    device_ids: List[str],
    parallel_devices: int = 5,
    parallel_checks: int = 10,
    full_mode: bool = False
) -> Dict[str, Any]:
    """v4.0 批量检测便捷函数"""
    batch = BatchDiagnosisV4()
    return batch.run(
        device_ids=device_ids,
        parallel_devices=parallel_devices,
        parallel_checks=parallel_checks,
        full_mode=full_mode
    )
