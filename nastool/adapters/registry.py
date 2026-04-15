"""
NAS Backend Adapter Registry

管理和注册所有 NAS 后端适配器。

Usage:
    from adapters import register_adapter, get_adapter, list_adapters

    # 注册适配器
    register_adapter("synology", SynologyAdapter)

    # 获取适配器实例
    adapter = get_adapter("synology", config)

    # 列出所有适配器
    adapters = list_adapters()
"""

from typing import Dict, Type, Optional, List
from .base import NASBackend, NASConfig, NASBackendType
import logging

logger = logging.getLogger(__name__)


# 适配器注册表
_ADAPTERS: Dict[str, Type[NASBackend]] = {}


def register_adapter(name: str, adapter_class: Type[NASBackend]) -> bool:
    """
    注册 NAS 后端适配器

    Args:
        name: 适配器名称（如 "synology", "qnap"）
        adapter_class: 适配器类

    Returns:
        True 如果注册成功
    """
    if name in _ADAPTERS:
        logger.warning(f"适配器 '{name}' 已存在，将被覆盖")

    if not issubclass(adapter_class, NASBackend):
        raise TypeError(f"{adapter_class} 必须继承自 NASBackend")

    _ADAPTERS[name] = adapter_class
    logger.info(f"已注册适配器: {name} ({adapter_class.__name__})")
    return True


def get_adapter(name: str, config: NASConfig = None) -> Optional[NASBackend]:
    """
    获取 NAS 后端适配器实例

    Args:
        name: 适配器名称
        config: NAS 配置（可选）

    Returns:
        适配器实例，如果不存在则返回 None
    """
    if name not in _ADAPTERS:
        logger.error(f"适配器 '{name}' 未注册")
        return None

    adapter_class = _ADAPTERS[name]

    try:
        # 如果没有提供配置，使用默认配置
        if config is None:
            config = NASConfig(backend_type=_get_backend_type(name))

        return adapter_class(config)
    except Exception as e:
        logger.error(f"创建适配器实例失败: {e}")
        return None


def list_adapters() -> List[Dict[str, str]]:
    """
    列出所有已注册的适配器

    Returns:
        适配器信息列表
    """
    result = []
    for name, adapter_class in _ADAPTERS.items():
        result.append(
            {
                "name": name,
                "type": adapter_class.backend_type.value
                if hasattr(adapter_class, "backend_type")
                else "unknown",
                "class": adapter_class.__name__,
                "version": getattr(adapter_class, "backend_version", "unknown"),
            }
        )
    return result


def has_adapter(name: str) -> bool:
    """
    检查适配器是否已注册

    Args:
        name: 适配器名称

    Returns:
        True 如果已注册
    """
    return name in _ADAPTERS


def unregister_adapter(name: str) -> bool:
    """
    注销适配器

    Args:
        name: 适配器名称

    Returns:
        True 如果注销成功
    """
    if name in _ADAPTERS:
        del _ADAPTERS[name]
        logger.info(f"已注销适配器: {name}")
        return True
    return False


def _get_backend_type(name: str) -> NASBackendType:
    """根据名称获取后端类型"""
    type_map = {
        "synology": NASBackendType.SYNOLOGY,
        "qnap": NASBackendType.QNAP,
        "ai_nas": NASBackendType.AI_NAS,
        "hikvision": NASBackendType.HIKVISION,
        "asustor": NASBackendType.ASUSTOR,
        "standalone": NASBackendType.STANDALONE,
    }
    return type_map.get(name, NASBackendType.STANDALONE)


# ========== 自动注册内置适配器 ==========


def _auto_register():
    """自动注册内置适配器"""
    from .base import StandaloneAdapter

    # 注册独立模式适配器
    register_adapter("standalone", StandaloneAdapter)

    # 尝试注册其他适配器（如果存在）
    try:
        from .http_backend import AI_NASAdapter

        register_adapter("ai_nas", AI_NASAdapter)
    except ImportError:
        pass

    try:
        from .synology import SynologyAdapter

        register_adapter("synology", SynologyAdapter)
    except ImportError:
        pass

    try:
        from .qnap import QNAPAdapter

        register_adapter("qnap", QNAPAdapter)
    except ImportError:
        pass

    # ADB USB 直连（V3.0-alpha）
    try:
        from .adb_adapter import ADBClient

        logger.info("ADB adapter loaded (V3.0 USB direct-connect)")
    except ImportError:
        pass


# 模块加载时自动注册
_auto_register()
