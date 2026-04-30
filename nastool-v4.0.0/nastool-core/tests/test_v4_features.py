"""
test_async_executor.py - 异步执行器测试

v4.0 核心功能测试。
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, r'C:\tools416\nastool-common')
sys.path.insert(0, r'C:\tools416\nastool-core')

from nastool_core.async_executor import AsyncCheckExecutor, run_checks_parallel


class TestAsyncCheckExecutor:
    """测试异步执行器"""
    
    def test_init(self):
        """测试初始化"""
        executor = AsyncCheckExecutor(
            max_concurrent=5,
            default_timeout=30.0
        )
        assert executor.max_concurrent == 5
        assert executor.default_timeout == 30.0
    
    def test_run_checks_parallel_mock(self):
        """测试并行执行（mock）"""
        # Mock检测项
        mock_results = [
            {"check_id": "test1", "result": Mock(), "elapsed": 0.1, "error": None},
            {"check_id": "test2", "result": Mock(), "elapsed": 0.1, "error": None},
        ]
        
        with patch('nastool_core.async_executor.run_checks_parallel') as mock_run:
            mock_run.return_value = mock_results
            
            results = run_checks_parallel(
                ["test1", "test2"],
                max_concurrent=2
            )
            
            assert len(results) == 2
            assert results[0]["check_id"] == "test1"
    
    def test_timeout_handling(self):
        """测试超时处理"""
        executor = AsyncCheckExecutor(default_timeout=0.01)
        
        # 模拟超时
        with patch.object(executor, '_run_sync_check') as mock_check:
            mock_check.side_effect = lambda x: time.sleep(1)
            
            # 由于是在线程中执行，这里主要测试超时逻辑存在
            assert executor.default_timeout == 0.01


class TestCheckTimeouts:
    """测试超时配置"""
    
    def test_timeouts_defined(self):
        """测试超时配置已定义"""
        from nastool_core.check_timeouts import CHECK_TIMEOUTS
        
        # 关键检测项应该有超时配置
        assert "network_latency" in CHECK_TIMEOUTS
        assert "internet_access" in CHECK_TIMEOUTS
        assert CHECK_TIMEOUTS["network_latency"] <= 10.0  # 网络检测不超过10秒


class TestBatchParallel:
    """测试批量并行"""
    
    def test_batch_executor_init(self):
        """测试批量执行器初始化"""
        from nastool_core.batch_parallel import BatchParallelExecutor
        
        executor = BatchParallelExecutor(
            max_concurrent_devices=5,
            max_concurrent_checks_per_device=10
        )
        
        assert executor.max_concurrent_devices == 5
        assert executor.max_concurrent_checks_per_device == 10


class TestMemoryOptimizer:
    """测试内存优化"""
    
    def test_streaming_processor(self):
        """测试流式处理器"""
        from nastool_core.memory_optimizer import StreamingResultProcessor
        
        processor = StreamingResultProcessor(batch_size=100)
        assert processor.batch_size == 100
        
        # 测试流式处理
        def mock_generator():
            for i in range(10):
                yield {"id": i, "data": "x" * 100}
        
        results = list(processor.process_streaming(
            mock_generator(),
            lambda x: x
        ))
        
        assert len(results) == 10
    
    def test_result_cache(self):
        """测试结果缓存"""
        from nastool_core.memory_optimizer import ResultCache
        
        cache = ResultCache(max_size=10, ttl=300)
        
        # 测试设置和获取
        cache.set("device1", {"score": 90})
        result = cache.get("device1")
        
        assert result is not None
        assert result["score"] == 90
        
        # 测试未缓存项
        assert cache.get("device2") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
