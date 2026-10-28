"""
adapters/base.py — 适配器基类
所有厂商适配器必须继承 BaseAdapter 并实现对应方法
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class AdapterReport:
    name: str = ""
    chip_type: str = ""
    specific_checks: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    ok: bool = False


class BaseAdapter(ABC):
    """厂商适配器基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称，如 'NVIDIA Jetson'"""
        pass

    @property
    @abstractmethod
    def chip_type(self) -> str:
        """芯片类型，与 core/ai_accel.py ChipType 对应"""
        pass

    def health_check(self) -> AdapterReport:
        """
        执行厂商特有的健康检查
        子类重写此方法添加专项检查
        """
        return AdapterReport(
            name=self.name,
            chip_type=self.chip_type,
            ok=True,
        )

    def benchmark(self) -> Dict[str, Any]:
        """
        执行厂商特有的性能基准测试
        子类可选重写
        """
        return {}

    def apply_tuning(self, profile: str = "default") -> List[str]:
        """
        应用性能调优配置
        profile: 'default' | 'performance' | 'power_save'
        返回操作记录
        """
        return []
