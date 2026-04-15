# -*- coding: utf-8 -*-
"""
nastools_pkg.main — 入口点
用法：
    python main.py           # 双击 / 命令行
    python -m nastools_pkg   # 模块方式
"""

import sys
import os

# ── 路径设置（关键：顺序决定 import 优先级）───────────────────────
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(THIS_DIR)  # = arm/

# 1. nastools_pkg/ 自身（确保 package import 正确）
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

# 2. nastool/（供 integration/remote.py 使用）—— 放最后，避免遮住 nastools_pkg.config
NASTOOL = os.path.join(PARENT, "nastool")
if NASTOOL not in sys.path:
    sys.path.append(NASTOOL)


def main():
    import tkinter as tk

    # 从当前包内部导入（两种运行方式都兼容）
    try:
        from nastools_pkg.gui.app import NastoolsApp
    except ModuleNotFoundError:
        from gui.app import NastoolsApp
    root = tk.Tk()
    app = NastoolsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
