# -*- coding: utf-8 -*-
"""
异步数据采集和融合引擎 - 性能优化模块

提供异步数据采集、并行处理和融合功能，显著提升检测性能。
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import List, Any, Dict, Tuple, Optional, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field

from .data_source import DataSourceResult, DataFusionEngine, DataFusionConfig, FusionMethod


@dataclass
class AsyncDataSourceTask:
    """异步数据源任务"""
    name: str
    task: Callable[..., Any] | Awaitable[Any]
    args: Tuple = ()
    kwargs: Dict = field(default_factory=dict)
    confidence: float = 1.0
    enabled: bool = True


class AsyncDataFusionEngine:
    """
    异步数据融合引擎
    
    支持：
    - 异步数据采集
    - 并行处理多个数据源
    - 超时控制
    - 异常处理和降级
    - 结果缓存
    """
    
    def __init__(self, config: Optional[DataFusionConfig] = None):
        self.config = config or DataFusionConfig()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.max_parallel_sources or 5
        )
        self._results_cache = {}
        self._cache_ttl = 30  # 缓存有效期(秒)
    
    async def _fetch_data_async(self, task: AsyncDataSourceTask) -> Optional[DataSourceResult]:
        """异步获取单个数据源"""
        try:
            if asyncio.iscoroutine(task.task):
                # 协程任务
                value = await asyncio.wait_for(task.task, timeout=self.config.timeout or 30)
            elif asyncio.iscoroutinefunction(task.task):
                # 异步函数
                value = await asyncio.wait_for(
                    task.task(*task.args, **task.kwargs),
                    timeout=self.config.timeout or 30
                )
            else:
                # 同步函数，在线程池中执行
                loop = asyncio.get_event_loop()
                value = await asyncio.wait_for(
                    loop.run_in_executor(self._executor, task.task, *task.args),
                    timeout=self.config.timeout or 30
                )
            
            return DataSourceResult(
                value=value,
                source=task.name,
                timestamp=datetime.now().timestamp(),
                confidence=task.confidence
            )
        except asyncio.TimeoutError:
            return DataSourceResult(
                value=None,
                source=task.name,
                timestamp=datetime.now().timestamp(),
                confidence=0.0,
                error="Timeout"
            )
        except Exception as e:
            return DataSourceResult(
                value=None,
                source=task.name,
                timestamp=datetime.now().timestamp(),
                confidence=0.0,
                error=str(e)
            )
    
    async def fetch_all_sources_async(self, tasks: List[AsyncDataSourceTask]) -> List[DataSourceResult]:
        """
        异步并行获取所有数据源
        
        Args:
            tasks: 数据源任务列表
            
        Returns:
            数据源结果列表（已过滤无效结果）
        """
        # 过滤禁用的任务
        enabled_tasks = [t for t in tasks if t.enabled]
        
        if not enabled_tasks:
            return []
        
        # 并行执行所有任务
        coroutines = [self._fetch_data_async(task) for task in enabled_tasks]
        results = await asyncio.gather(*coroutines)
        
        # 过滤无效结果（置信度>0或值不为None）
        valid_results = [r for r in results if r.confidence > 0 or r.value is not None]
        
        return valid_results
    
    def fetch_all_sources_sync(self, tasks: List[AsyncDataSourceTask]) -> List[DataSourceResult]:
        """
        同步并行获取所有数据源（内部使用线程池）
        
        Args:
            tasks: 数据源任务列表
            
        Returns:
            数据源结果列表
        """
        return asyncio.run(self.fetch_all_sources_async(tasks))
    
    async def fuse_data_async(
        self,
        results: List[DataSourceResult],
        method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        异步融合数据
        
        Args:
            results: 数据源结果列表
            method: 融合方法
            
        Returns:
            (融合值, 元数据)
        """
        if not results:
            return None, {
                "sources": [],
                "source_count": 0,
                "confidence": 0.0,
                "fusion_method": method.value,
                "error": "No valid data sources"
            }
        
        # 使用同步融合引擎进行融合
        sync_engine = DataFusionEngine(config=self.config)
        return sync_engine.fuse_data(results, method)
    
    async def execute_and_fuse_async(
        self,
        tasks: List[AsyncDataSourceTask],
        method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE
    ) -> Tuple[Any, Dict[str, Any], List[DataSourceResult]]:
        """
        完整的异步执行流程：采集 -> 融合
        
        Args:
            tasks: 数据源任务列表
            method: 融合方法
            
        Returns:
            (融合值, 元数据, 原始数据源结果)
        """
        # 异步采集数据
        results = await self.fetch_all_sources_async(tasks)
        
        # 异步融合
        fused_value, metadata = await self.fuse_data_async(results, method)
        
        return fused_value, metadata, results
    
    def execute_and_fuse_sync(
        self,
        tasks: List[AsyncDataSourceTask],
        method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE
    ) -> Tuple[Any, Dict[str, Any], List[DataSourceResult]]:
        """
        同步版本的完整执行流程
        
        Args:
            tasks: 数据源任务列表
            method: 融合方法
            
        Returns:
            (融合值, 元数据, 原始数据源结果)
        """
        return asyncio.run(self.execute_and_fuse_async(tasks, method))
    
    def close(self):
        """关闭线程池"""
        self._executor.shutdown(wait=True)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AsyncDataCollector:
    """
    异步数据收集器
    
    提供便捷的数据源注册和采集接口
    """
    
    def __init__(self):
        self._tasks: List[AsyncDataSourceTask] = []
    
    def add_source(
        self,
        name: str,
        task: Callable[..., Any] | Awaitable[Any],
        *args,
        confidence: float = 1.0,
        enabled: bool = True,
        **kwargs
    ):
        """
        注册数据源
        
        Args:
            name: 数据源名称
            task: 数据采集任务（同步函数、异步函数或协程）
            args: 位置参数
            confidence: 置信度
            enabled: 是否启用
            kwargs: 关键字参数
        """
        self._tasks.append(AsyncDataSourceTask(
            name=name,
            task=task,
            args=args,
            kwargs=kwargs,
            confidence=confidence,
            enabled=enabled
        ))
    
    def add_coroutine(self, name: str, coro: Awaitable[Any], confidence: float = 1.0):
        """添加协程数据源"""
        self._tasks.append(AsyncDataSourceTask(
            name=name,
            task=coro,
            confidence=confidence
        ))
    
    def add_sync_function(self, name: str, func: Callable[..., Any], *args, confidence: float = 1.0, **kwargs):
        """添加同步函数数据源"""
        self._tasks.append(AsyncDataSourceTask(
            name=name,
            task=func,
            args=args,
            kwargs=kwargs,
            confidence=confidence
        ))
    
    def get_tasks(self) -> List[AsyncDataSourceTask]:
        """获取所有任务"""
        return self._tasks
    
    async def collect_async(self) -> List[DataSourceResult]:
        """异步采集所有数据"""
        engine = AsyncDataFusionEngine()
        try:
            return await engine.fetch_all_sources_async(self._tasks)
        finally:
            engine.close()
    
    def collect_sync(self) -> List[DataSourceResult]:
        """同步采集所有数据"""
        engine = AsyncDataFusionEngine()
        try:
            return engine.fetch_all_sources_sync(self._tasks)
        finally:
            engine.close()
    
    async def collect_and_fuse_async(
        self,
        method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE
    ) -> Tuple[Any, Dict[str, Any], List[DataSourceResult]]:
        """采集并融合数据（异步）"""
        engine = AsyncDataFusionEngine()
        try:
            return await engine.execute_and_fuse_async(self._tasks, method)
        finally:
            engine.close()
    
    def collect_and_fuse_sync(
        self,
        method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE
    ) -> Tuple[Any, Dict[str, Any], List[DataSourceResult]]:
        """采集并融合数据（同步）"""
        engine = AsyncDataFusionEngine()
        try:
            return engine.execute_and_fuse_sync(self._tasks, method)
        finally:
            engine.close()


# 便捷函数
async def async_collect_and_fuse(
    sources: List[Tuple[str, Callable[..., Any], Dict]],
    method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE
) -> Tuple[Any, Dict[str, Any]]:
    """
    便捷函数：异步采集多源数据并融合
    
    Args:
        sources: [(name, func, kwargs), ...]
        method: 融合方法
        
    Returns:
        (融合值, 元数据)
    """
    collector = AsyncDataCollector()
    for name, func, kwargs in sources:
        collector.add_source(name, func, **kwargs)
    
    fused_value, metadata, _ = await collector.collect_and_fuse_async(method)
    return fused_value, metadata


def sync_collect_and_fuse(
    sources: List[Tuple[str, Callable[..., Any], Dict]],
    method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE
) -> Tuple[Any, Dict[str, Any]]:
    """
    便捷函数：同步采集多源数据并融合（内部使用线程池并行）
    
    Args:
        sources: [(name, func, kwargs), ...]
        method: 融合方法
        
    Returns:
        (融合值, 元数据)
    """
    collector = AsyncDataCollector()
    for name, func, kwargs in sources:
        collector.add_source(name, func, **kwargs)
    
    fused_value, metadata, _ = collector.collect_and_fuse_sync(method)
    return fused_value, metadata
