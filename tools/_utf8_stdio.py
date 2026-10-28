"""
tools/_utf8_stdio.py —— 让脚本在**任何**控制台编码下都能输出中文。

**为什么需要它**：Windows 标准输出的默认编码由**系统 locale** 决定——
英文系统是 cp1252，中文是 cp936，两者都编不了中文和 `✓` 这类符号。
脚本里一句 `print("✓ 冒烟通过")` 就会抛 `UnicodeEncodeError`，
在 CI 的英文 Windows runner 上直接崩掉。

中文 Windows 恰好能编中文，所以本地永远看不到这个问题——
**只有英文 Windows 会中招**，包括 GitHub Actions 的 Windows runner。

`nastool` 库自身在 `cli.py` 的 `main()` 入口处理了这个问题；
本模块是给 `tools/` 下的脚本用的，两边是同一个道理。
"""
from __future__ import annotations

import sys


def force_utf8_stdio() -> None:
    """把 stdout / stderr 切到 UTF-8，编不出来的字符用 � 替换。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError, AttributeError):
            pass  # 改不了就算了，不能因为编码问题让脚本起不来
