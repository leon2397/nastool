# -*- coding: utf-8 -*-
"""
nastools_pkg — nastools v1.1 模块化包
=====================================
从 nastools.py (921行) 重构而来。

目录结构：
    nastools_pkg/
    ├── main.py              ← 入口
    ├── config/
    │   └── theme.py        ← 主题颜色 + CHECK_DEFS
    ├── core/
    │   ├── ssh.py           ← SSHConnection
    │   └── parser.py       ← 结果解析
    ├── scripts/
    │   └── deploy.py        ← 部署脚本字符串（v1.1 后由 nastool fixes/ 接管）
    ├── integration/          ← 🆕 nastool 胶水层
    │   ├── bridge.py        ← CheckResult → JSON 转换
    │   └── remote.py        ← 三种执行模式
    └── gui/
        └── app.py           ← 主窗口（~430行，无嵌入式脚本）

调用方式：
    python -m nastools_pkg          # 完整 GUI
    python -m nastools_pkg.main     # 同上
"""

from .gui.app import NastoolsApp, main
from .integration import RemoteExecutor, to_json
from .core import SSHConnection, parse_results

__all__ = [
    "NastoolsApp",
    "main",
    "RemoteExecutor",
    "to_json",
    "SSHConnection",
    "parse_results",
]
