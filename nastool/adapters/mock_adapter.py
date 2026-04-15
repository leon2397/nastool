# -*- coding: utf-8 -*-
"""
Mock 适配器包装器 - 用于测试和开发环境

将 mock 数据注入适配器，模拟真实设备行为。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from adapters.base import BaseAdapter, AdapterResult, ErrorCode


class MockAdapter(BaseAdapter):
    """Mock 适配器 - 使用预定义数据模拟设备"""

    def __init__(self, mock_data: Dict[str, Any]):
        super().__init__()
        self.mock_data = mock_data
        self._setup_from_mock()

    def _setup_from_mock(self):
        """从 mock 数据初始化结果"""
        self.result.device_family = self.mock_data.get("device_family")
        self.result.device_model = self.mock_data.get("device_model")
        
        # 昂腾/Jetson mock 数据结构：expected 字段
        expected = self.mock_data.get("expected", {})
        if expected:
            self.result.npu_status = {
                "count": expected.get("device_count", 1),
                "utilization": expected.get("utilization", 0),
                "temperature": expected.get("temperature", 40),
                "memory_used": expected.get("memory_used_mb", 0),
                "memory_total": expected.get("memory_total_mb", 1),
            }
            # GPU 数据（Jetson）
            if "gpu_util" in expected:
                self.result.gpu_status = {
                    "utilization": expected.get("gpu_util", 0),
                    "temperature": expected.get("gpu_temp", 40),
                }
            # 系统数据
            self.result.system = {
                "cpu_util": expected.get("cpu_util", 30),
                "cpu_temp": expected.get("cpu_temp", 45),
                "memory_used": expected.get("mem_used_mb", 0),
                "memory_total": expected.get("mem_total_mb", 8192),
            }
        else:
            # 备用：直接读取 npu/system 字段
            npu_data = self.mock_data.get("npu", {})
            if npu_data:
                self.result.npu_status = npu_data
            
            sys_data = self.mock_data.get("system", {})
            if sys_data:
                self.result.system = sys_data

    def identify(self) -> Optional[str]:
        """返回 mock 设备族"""
        family = self.mock_data.get("device_family")
        if not family:
            self.result.add_error(ErrorCode.DEVICE_UNKNOWN, "Mock 数据缺少 device_family")
        return family

    def check_tools(self) -> Dict[str, bool]:
        """返回 mock 工具状态"""
        return self.mock_data.get("tools", {})

    def detect_npu(self) -> None:
        """NPU 数据已从 mock 初始化"""
        pass

    def detect_gpu(self) -> None:
        """GPU 数据已从 mock 初始化"""
        pass

    def detect_system(self) -> None:
        """系统数据已从 mock 初始化"""
        pass

    def calc_score(self) -> int:
        """计算健康评分"""
        # 从 mock 数据读取评分，或根据指标计算
        if "score" in self.mock_data:
            self.result.score = self.mock_data["score"]
            self.result.score_breakdown = self.mock_data.get("score_breakdown", {})
            return self.result.score
        
        # 从 npu_status / system 读取
        npu = self.result.npu_status or {}
        sys_ = self.result.system or {}
        
        npu_util = npu.get("utilization", 0)
        npu_temp = npu.get("temperature", 40)
        npu_mem = 0
        if npu.get("memory_total", 0) > 0:
            npu_mem = int(100 * npu.get("memory_used", 0) / npu["memory_total"])
        
        # 简单评分：利用率 30% + 温度 25% + 内存 25% + 系统 20%
        util_score = min(npu_util, 100)
        temp_score = max(0, 100 - npu_temp)  # 温度越低越好
        mem_score = 100 - npu_mem  # 内存使用率越低越好
        sys_score = 80  # 默认系统分
        
        self.result.score = int(
            util_score * 0.3 + temp_score * 0.25 + mem_score * 0.25 + sys_score * 0.2
        )
        self.result.score_breakdown = {
            "npu_util": int(util_score * 0.3),
            "npu_temp": int(temp_score * 0.25),
            "npu_mem": int(mem_score * 0.25),
            "sys_mem": int(sys_score * 0.2),
        }
        
        return self.result.score

    def run_benchmark(self) -> None:
        """运行 mock 基准测试"""
        # 从 mock 数据读取
        if "benchmark" in self.mock_data:
            self.result.benchmark = self.mock_data["benchmark"]
            return
        
        # 启发式估算
        from adapters.benchmark import run_heuristic_benchmark
        result = run_heuristic_benchmark()
        result["model"] = "MobileNetV2 (mock)"
        self.result.benchmark = result

    def get_model_name(self) -> str:
        """返回 mock 设备型号"""
        return self.mock_data.get("device_model", "Unknown Mock Device")
