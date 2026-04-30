"""
memory_optimizer.py - 内存优化模块

优化目标：
- 检测结果流式处理（不全部加载到内存）
- 大报告分块生成（避免OOM）
- LRU缓存检测结果
- 资源及时释放
"""

import gc
import weakref
from typing import Iterator, List, Dict, Any, Optional, Generator
from functools import lru_cache
from dataclasses import dataclass
import threading

from nastool_common.logger import get_logger

logger = get_logger(__name__)


class StreamingResultProcessor:
    """
    流式结果处理器。
    
    特性：
    - 不保存全部结果，处理完即释放
    - 支持大报告分块生成
    - 内存占用恒定（不随检测项增长）
    """
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self._processed_count = 0
        
    def process_streaming(
        self,
        results: Iterator[Dict[str, Any]],
        processor: callable
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式处理结果。
        
        Args:
            results: 结果迭代器
            processor: 处理函数
            
        Yields:
            处理后的结果
        """
        batch = []
        
        for result in results:
            batch.append(result)
            
            if len(batch) >= self.batch_size:
                # 处理批次
                for item in batch:
                    processed = processor(item)
                    if processed:
                        yield processed
                
                # 清空批次，释放内存
                self._processed_count += len(batch)
                batch.clear()
                
                # 主动触发GC
                if self._processed_count % 1000 == 0:
                    gc.collect()
        
        # 处理剩余
        for item in batch:
            processed = processor(item)
            if processed:
                yield processed
        
        batch.clear()
        gc.collect()


class ReportChunkGenerator:
    """
    大报告分块生成器。
    
    避免一次性生成大报告导致OOM。
    """
    
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
        
    def generate_json_report(
        self,
        results: Iterator[Dict],
        output_path: str
    ) -> Dict[str, Any]:
        """
        分块生成JSON报告。
        
        直接写入文件，不保留全部数据在内存。
        """
        import json
        
        total_items = 0
        chunk_files = []
        current_chunk = []
        chunk_index = 0
        
        for result in results:
            current_chunk.append(result)
            total_items += 1
            
            if len(current_chunk) >= self.chunk_size:
                # 写入分块文件
                chunk_path = f"{output_path}.chunk_{chunk_index}.json"
                with open(chunk_path, 'w', encoding='utf-8') as f:
                    json.dump(current_chunk, f)
                chunk_files.append(chunk_path)
                
                # 清空当前分块
                current_chunk.clear()
                chunk_index += 1
                
                logger.debug(f"Generated chunk {chunk_index}, total {total_items} items")
        
        # 写入最后一个分块
        if current_chunk:
            chunk_path = f"{output_path}.chunk_{chunk_index}.json"
            with open(chunk_path, 'w', encoding='utf-8') as f:
                json.dump(current_chunk, f)
            chunk_files.append(chunk_path)
            current_chunk.clear()
        
        # 合并分块（可选，或保持分块格式）
        self._merge_chunks(chunk_files, output_path)
        
        return {
            "output_path": output_path,
            "total_items": total_items,
            "chunks": len(chunk_files),
            "chunk_size": self.chunk_size
        }
    
    def _merge_chunks(self, chunk_files: List[str], output_path: str):
        """合并分块文件为单个报告"""
        import json
        import os
        
        # 流式合并
        with open(output_path, 'w', encoding='utf-8') as out:
            out.write('[')
            first = True
            
            for chunk_file in chunk_files:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                
                for item in chunk_data:
                    if not first:
                        out.write(',')
                    json.dump(item, out)
                    first = False
                
                # 删除分块文件
                os.remove(chunk_file)
            
            out.write(']')


class ResultCache:
    """
    检测结果LRU缓存。
    
    避免重复检测相同设备。
    """
    
    def __init__(self, max_size: int = 100, ttl: int = 300):
        """
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Dict] = {}
        self._access_time: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Dict]:
        """获取缓存结果"""
        with self._lock:
            if key in self._cache:
                import time
                # 检查过期
                if time.time() - self._access_time[key] > self.ttl:
                    del self._cache[key]
                    del self._access_time[key]
                    return None
                
                # 更新访问时间
                self._access_time[key] = time.time()
                return self._cache[key]
            return None
    
    def set(self, key: str, value: Dict):
        """设置缓存结果"""
        with self._lock:
            import time
            
            # LRU淘汰
            if len(self._cache) >= self.max_size:
                # 淘汰最久未访问的
                oldest_key = min(self._access_time, key=self._access_time.get)
                del self._cache[oldest_key]
                del self._access_time[oldest_key]
            
            self._cache[key] = value
            self._access_time[key] = time.time()
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_time.clear()
            gc.collect()


class ResourceMonitor:
    """
    资源监控器。
    
    监控内存使用，及时释放资源。
    """
    
    def __init__(self, memory_threshold_mb: int = 500):
        self.memory_threshold = memory_threshold_mb * 1024 * 1024
        self._check_interval = 100  # 每处理100项检查一次
        self._processed = 0
    
    def check_memory(self) -> bool:
        """检查内存使用，超过阈值返回True"""
        import psutil
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return memory_info.rss > self.memory_threshold
    
    def maybe_gc(self):
        """可能需要垃圾回收"""
        self._processed += 1
        
        if self._processed % self._check_interval == 0:
            if self.check_memory():
                logger.warning("Memory threshold exceeded, forcing GC")
                gc.collect()
                return True
        return False
    
    def get_memory_usage(self) -> Dict[str, float]:
        """获取内存使用情况"""
        import psutil
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }


# 便捷函数
def optimize_memory():
    """立即执行内存优化"""
    gc.collect()
    
    # 强制释放未引用对象
    for _ in range(3):
        gc.collect()
    
    logger.info("Memory optimization completed")


def get_memory_usage() -> Dict[str, float]:
    """获取当前内存使用情况"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2)
        }
    except ImportError:
        return {"error": "psutil not installed"}
