"""
nastool/checks/ — 全部检测项

导入本包即完成注册（@check 装饰器把元信息写入注册表）。
新增一项检查 = 在对应分类文件里加一个函数，其它地方都不用改。
"""
from __future__ import annotations

# 导入即注册（顺序只影响 --list-checks 的分组内顺序，最终会按分类排序）
from . import ai, network, security, services, storage, system, usb  # noqa: F401,E402

__all__ = ["ai", "network", "security", "services", "storage", "system", "usb"]
