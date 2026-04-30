"""
utils/registry.py - 通用注册器模式

提供可复用的注册器基类，减少重复代码。

Usage:
    # 创建注册器
    my_registry = Registry[MyBaseClass]("my_registry")

    # 注册
    @my_registry.register
    class MyImpl(MyBaseClass):
        pass

    # 获取
    impl = my_registry.get("my_impl")
"""

from typing import Dict, Type, Optional, List, Generic, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Registry(Generic[T]):
    """
    通用注册器

    用法:
        registry = Registry[BaseClass]("my_registry")

        @registry.register
        class MyImpl(BaseClass):
            name = "my_impl"

        impl = registry.get("my_impl")
        all_impls = registry.list_all()
    """

    def __init__(self, name: str):
        self.name = name
        self._items: Dict[str, Type[T]] = {}

    def register(self, item_class: Type[T]) -> Type[T]:
        """
        装饰器：注册类

        类必须有 `name` 或 `check_id` 或 `fix_id` 属性作为键。
        """
        # 尝试多种命名属性
        key = (
            getattr(item_class, "name", None)
            or getattr(item_class, "check_id", None)
            or getattr(item_class, "fix_id", None)
            or item_class.__name__.lower()
        )

        if key in self._items:
            logger.warning(f"[{self.name}] '{key}' 已存在，将被覆盖")

        self._items[key] = item_class
        logger.debug(f"[{self.name}] 注册: {key}")
        return item_class

    def get(self, key: str) -> Optional[Type[T]]:
        """获取注册的类"""
        return self._items.get(key)

    def list_all(self) -> List[Type[T]]:
        """列出所有注册的类"""
        return list(self._items.values())

    def list_names(self) -> List[str]:
        """列出所有注册的名称"""
        return list(self._items.keys())

    def exists(self, key: str) -> bool:
        """检查是否已注册"""
        return key in self._items

    def clear(self) -> None:
        """清空注册表（测试用）"""
        self._items.clear()


class InstanceRegistry(Generic[T]):
    """
    实例注册器（注册实例而非类）

    用法:
        registry = InstanceRegistry[MyClass]("instances")
        registry.register("key", instance)
        inst = registry.get("key")
    """

    def __init__(self, name: str):
        self.name = name
        self._instances: Dict[str, T] = {}

    def register(self, key: str, instance: T) -> bool:
        """注册实例"""
        if key in self._instances:
            logger.warning(f"[{self.name}] '{key}' 已存在，将被覆盖")
        self._instances[key] = instance
        return True

    def get(self, key: str) -> Optional[T]:
        """获取实例"""
        return self._instances.get(key)

    def list_all(self) -> List[T]:
        """列出所有实例"""
        return list(self._instances.values())

    def remove(self, key: str) -> bool:
        """移除实例"""
        if key in self._instances:
            del self._instances[key]
            return True
        return False
