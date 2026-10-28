#!/usr/bin/env python3
"""
隔离安装冒烟：把 wheel 装进一个干净的虚拟环境，确认装出来的真能跑。

**为什么必须隔离装**：源码目录下 `import nastool` 命中的永远是工作区那份代码，
装没装对、入口脚本有没有生成、依赖有没有漏，都验不出来。
装进空 venv 才代表用户 `pip install` 之后拿到的东西。

跨平台：venv 里的可执行文件在 Windows 是 `Scripts/nastool.exe`，
在 POSIX 是 `bin/nastool`。这里按 `sys.platform` 分别处理，
所以同一份脚本在本地 Windows 和 CI 的 ubuntu 上都能跑。

用法：
    python tools/verify_install.py [dist目录]
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _utf8_stdio import force_utf8_stdio

force_utf8_stdio()


def fail(msg: str) -> None:
    print(f"✗ 隔离安装冒烟失败：{msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    dist = sys.argv[1] if len(sys.argv) > 1 else "dist"
    wheels = glob.glob(os.path.join(dist, "*.whl"))
    if not wheels:
        fail(f"{dist}/ 里没有 wheel")

    with tempfile.TemporaryDirectory() as tmp:
        venv = os.path.join(tmp, "verify")
        subprocess.run([sys.executable, "-m", "venv", venv],
                       check=True, capture_output=True, timeout=300)

        if sys.platform == "win32":
            vpy = os.path.join(venv, "Scripts", "python.exe")
        else:
            vpy = os.path.join(venv, "bin", "python")

        r = subprocess.run([vpy, "-m", "pip", "install", "--quiet", wheels[0]],
                           capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            fail(f"pip install 失败：\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")

        # 装出来的包要能 import，版本要对
        r = subprocess.run(
            [vpy, "-c", "import nastool; print(nastool.__version__)"],
            capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            fail(f"import nastool 失败：{r.stderr[-1500:]}")
        version = r.stdout.strip()

        # 装出来的命令行入口要能跑完整体检
        if sys.platform == "win32":
            exe = os.path.join(venv, "Scripts", "nastool.exe")
        else:
            exe = os.path.join(venv, "bin", "nastool")
        if not os.path.exists(exe):
            fail(f"命令入口没装出来：{exe}")

        r = subprocess.run(
            [exe, "--no-speed-test", "--no-smart", "--no-internet", "--no-color"],
            capture_output=True, text=True, timeout=600)
        # 退出码 1 = 检测到严重问题，是正常的体检结果，不是安装失败
        if r.returncode == 2:
            fail(f"装出来的 nastool 运行错误：\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
        if r.returncode not in (0, 1):
            fail(f"装出来的 nastool 退出码异常：{r.returncode}")

    print(f"✓ 隔离安装冒烟通过：安装版本 {version}，命令行可跑完整体检")
    return 0


if __name__ == "__main__":
    sys.exit(main())
