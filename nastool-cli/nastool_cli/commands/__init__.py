"""
main_refactor.py - v4.0 CLI 重构计划

将 4330+ 行的 main.py 拆分为模块化结构。

目标结构：
```
nastool_cli/
├── __init__.py
├── main.py              # 入口，仅200行
├── commands/
│   ├── __init__.py      # 命令注册中心
│   ├── base.py          # 命令基类
│   ├── diagnose.py      # 诊断命令
│   ├── device.py        # 设备管理
│   ├── batch.py         # 批量检测
│   ├── compare.py       # 对比分析
│   ├── monitor.py       # 实时监控
│   └── plugin.py        # 插件管理
├── options.py           # 参数解析
├── output.py            # 输出格式化
└── utils.py             # 工具函数
```
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import argparse


class Command(ABC):
    """命令基类"""
    
    name: str = ""
    help: str = ""
    aliases: List[str] = []
    
    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser):
        """添加命令参数"""
        pass
    
    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """执行命令，返回退出码"""
        pass


class CommandRegistry:
    """命令注册中心"""
    
    _commands: Dict[str, Command] = {}
    
    @classmethod
    def register(cls, command: Command):
        """注册命令"""
        cls._commands[command.name] = command
        for alias in command.aliases:
            cls._commands[alias] = command
    
    @classmethod
    def get(cls, name: str) -> Optional[Command]:
        """获取命令"""
        return cls._commands.get(name)
    
    @classmethod
    def list_commands(cls) -> List[str]:
        """列出所有命令"""
        return sorted(set(cls._commands.keys()))


# 命令注册装饰器
def register_command(name: str, help: str = "", aliases: List[str] = None):
    """命令注册装饰器"""
    def decorator(cls):
        cls.name = name
        cls.help = help
        cls.aliases = aliases or []
        CommandRegistry.register(cls())
        return cls
    return decorator
