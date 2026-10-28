"""
adapters/__init__.py — 厂商/设备专用适配层
每个适配器处理特定硬件平台的特殊路径和驱动
"""
from .base import BaseAdapter
from .nvidia_jetson import NvidiaJetsonAdapter
from .rockchip import RockchipAdapter
from .generic import GenericAdapter

ADAPTERS = {
    "nvidia_gpu": NvidiaJetsonAdapter,
    "rockchip_npu": RockchipAdapter,
    # 后续添加：huawei_ascend, intel_npu, sophgo_tpu
}


def get_adapter(chip_type: str) -> BaseAdapter:
    """根据芯片类型返回对应适配器"""
    cls = ADAPTERS.get(chip_type, GenericAdapter)
    return cls()
