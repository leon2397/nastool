#!/usr/bin/env python3
"""
校验构建产物（wheel / sdist）的内容是否符合预期。

**为什么是独立脚本**：CI 的 build job 里原本用 bash heredoc 写校验逻辑，
在 Windows 上会直接语法错误（PowerShell 解析不了 `<<'PY'`）。抽成脚本后，
同一份校验逻辑在本地也能跑——发版前的最后一道关不必依赖 CI 才能过。

检查项：
  · LICENSE 必须在 wheel 和 sdist 里（没有许可证的包不能分发）
  · `reference/` 不该进产物（那是历史归档，不是运行时依赖）
  · 运行时模块数量下限（防止 MANIFEST.in 写错把代码漏掉）
  · sdist 里要包含 pyproject.toml（否则装不上）

用法：
    python tools/verify_dist.py [dist目录]
"""
from __future__ import annotations

import glob
import os
import sys
import tarfile
import zipfile

MIN_RUNTIME_MODULES = 30


def fail(msg: str) -> None:
    print(f"✗ 产物校验失败：{msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    dist = sys.argv[1] if len(sys.argv) > 1 else "dist"

    wheels = glob.glob(os.path.join(dist, "*.whl"))
    sdists = glob.glob(os.path.join(dist, "*.tar.gz"))
    if not wheels:
        fail(f"{dist}/ 里没有 wheel")
    if not sdists:
        fail(f"{dist}/ 里没有 sdist")

    whl = wheels[0]
    sdist = sdists[0]

    names = zipfile.ZipFile(whl).namelist()

    if not any("LICENSE" in n for n in names):
        fail("LICENSE 未进 wheel")
    if any(n.startswith("reference/") for n in names):
        fail("reference/ 不该进产物（历史归档，不是运行时依赖）")

    modules = [n for n in names if n.startswith("nastool/") and n.endswith(".py")]
    if len(modules) < MIN_RUNTIME_MODULES:
        fail(f"wheel 里运行时模块不全：{len(modules)} < {MIN_RUNTIME_MODULES}")

    tar_names = tarfile.open(sdist).getnames()
    if not any(n.endswith("LICENSE") for n in tar_names):
        fail("LICENSE 未进 sdist")
    if not any(n.endswith("pyproject.toml") for n in tar_names):
        fail("sdist 里没有 pyproject.toml（装不上）")

    print(f"✓ 产物校验通过：wheel {len(names)} 条目 / "
          f"运行时模块 {len(modules)} 个 / sdist {len(tar_names)} 条目")
    return 0


if __name__ == "__main__":
    sys.exit(main())
