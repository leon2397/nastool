# -*- coding: utf-8 -*-
"""
nastool adapters.jetson - Jetson 适配器模块

模块：
- common: 通用适配器（6类设备检测）
- power: 功耗模式管理（nvpmodel）
- fan: 风扇控制
- jetpack: JetPack 版本映射
"""

from adapters.jetson.common import JetsonAdapter
from adapters.jetson.power import (
    detect_power_mode,
    set_power_mode,
    get_power_info,
)
from adapters.jetson.fan import (
    detect_fan_status,
    set_fan_pwm,
    get_fan_info,
)
from adapters.jetson.jetpack import (
    get_jetpack_info,
    get_latest_jetpack,
    check_version_compatibility,
    l4t_to_jetpack,
)

__all__ = [
    # 适配器
    "JetsonAdapter",
    # 功耗模式
    "detect_power_mode",
    "set_power_mode",
    "get_power_info",
    # 风扇控制
    "detect_fan_status",
    "set_fan_pwm",
    "get_fan_info",
    # JetPack 版本
    "get_jetpack_info",
    "get_latest_jetpack",
    "check_version_compatibility",
    "l4t_to_jetpack",
]
