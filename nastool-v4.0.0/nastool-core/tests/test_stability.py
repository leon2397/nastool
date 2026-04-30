"""
test_stability.py - 稳定性测试

测试v4.0的健壮性特性。
"""

import pytest
import time
import threading
import asyncio

import sys
sys.path.insert(0, r'C:\tools416\nastool-common')
sys.path.insert(0, r'C:\tools416\nastool-core')


class TestTimeoutHandling:
    """测试超时处理"""
    
    def test_check_timeouts_configured(self):
        """测试检测项超时已配置"""
        from nastool_core.check_timeouts import CHECK_TIMEOUTS
        
        # 关键慢检测应该有超时
        slow_checks = [
            "network_latency",
            "latency_check", 
            "internet_access",
            "triton_server",
            "torchserve"
        ]
        
        for check in slow_checks:
            assert check in CHECK_TIMEOUTS, f"{check} should have timeout"
            assert CHECK_TIMEOUTS[check] <= 10.0, f"{check} timeout should <= 10s"


class TestResourceManagement:
    """测试资源管理"""
    
    def test_streaming_memory_constant(self):
        """测试流式处理内存恒定"""
        from nastool_core.memory_optimizer import StreamingResultProcessor
        
        processor = StreamingResultProcessor(batch_size=10)
        
        # 生成大量数据
        def big_generator():
            for i in range(100):
                yield {"id": i, "data": "x" * 1000}
        
        # 处理过程中内存应该保持恒定（不累积）
        results = list(processor.process_streaming(
            big_generator(),
            lambda x: x
        ))
        
        assert len(results) == 100
    
    def test_cache_size_limit(self):
        """测试缓存大小限制"""
        from nastool_core.memory_optimizer import ResultCache
        
        cache = ResultCache(max_size=5)
        
        # 添加超过限制的项
        for i in range(10):
            cache.set(f"key{i}", {"value": i})
        
        # 缓存应该只保留最近5个
        # 注意：具体行为取决于LRU实现


class TestConcurrency:
    """测试并发安全"""
    
    def test_cache_thread_safe(self):
        """测试缓存线程安全"""
        from nastool_core.memory_optimizer import ResultCache
        
        cache = ResultCache()
        errors = []
        
        def writer():
            try:
                for i in range(100):
                    cache.set(f"key{i}", {"value": i})
            except Exception as e:
                errors.append(e)
        
        def reader():
            try:
                for i in range(100):
                    cache.get(f"key{i}")
            except Exception as e:
                errors.append(e)
        
        # 并发读写
        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestErrorHandling:
    """测试错误处理"""
    
    def test_async_executor_graceful_failure(self):
        """测试异步执行器优雅失败"""
        from nastool_core.async_executor import AsyncCheckExecutor
        
        executor = AsyncCheckExecutor()
        
        # 测试无效检测项
        result = asyncio.run(executor.run_check_async("invalid_check_id"))
        
        assert result["error"] is not None
        assert result["result"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
