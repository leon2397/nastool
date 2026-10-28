#!/usr/bin/env python3
"""
端到端冒烟：真跑一次 nastool，校验产出的报告完整可用。

**为什么它是独立脚本而不是 CI 里的一段 YAML**：CI 在 Windows runner 上的默认
shell 是 PowerShell，而 bash 的 heredoc（`python - <<'PY'`）在 PowerShell 里是
语法错误（实测报 `ParserError: .ps1:4`，5 个 Windows 格子全挂在这）。
把校验逻辑放进仓库里的 Python 文件，CI、本地、任何 shell 下跑的都是同一份
代码——顺带让「冒烟」变成一件本地随时可做的事，不必依赖 CI 才能验证。

**退出码语义**（重要）：nastool 的退出码是三态的——
    0 = 健康 / 1 = 检测到严重问题 / 2 = 运行错误
检测到问题返回 1 是**正常的体检结果**，不是错误。所以这里只把 2 当失败。

用法：
    python tools/smoke.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _utf8_stdio import force_utf8_stdio

force_utf8_stdio()

def fail(msg: str) -> None:
    print(f"✗ 冒烟失败：{msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    # 用 sys.executable：CI 里是当前解释器（可能是 venv 里的），保证跑的是
    # 刚装上的那个包，而不是 PATH 上碰巧存在的另一个。
    with tempfile.TemporaryDirectory() as tmp:
        report_path = os.path.join(tmp, "report.json")
        cmd = [
            sys.executable, "-m", "nastool",
            "--no-speed-test", "--no-smart", "--no-internet", "--no-color",
            "-o", "json", "--output-file", report_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if proc.returncode == 2:
            fail(f"nastool 运行错误（退出码 2）\n"
                 f"--- stdout ---\n{proc.stdout[-2000:]}\n"
                 f"--- stderr ---\n{proc.stderr[-2000:]}")
        if proc.returncode not in (0, 1):
            fail(f"nastool 退出码异常：{proc.returncode}"
                 f"（应为 0 健康 / 1 有问题 / 2 错误）\n"
                 f"--- stdout ---\n{proc.stdout[-2000:]}\n"
                 f"--- stderr ---\n{proc.stderr[-2000:]}")
        if not os.path.exists(report_path):
            # stderr 一定要打出来——崩溃的真正原因都在那儿。
            # （曾经只打 stdout，排查时看到一片空白，白花半小时找原因。）
            fail(f"没有产出报告文件：{report_path}\n"
                 f"--- stdout ---\n{proc.stdout[-2000:]}\n"
                 f"--- stderr ---\n{proc.stderr[-2000:]}")

        with open(report_path, encoding="utf-8") as f:
            d = json.load(f)

    # ── 报告内容校验 ──
    meta = d.get("meta", {})
    rv = str(meta.get("report_version", ""))
    if not rv.startswith("4."):
        fail(f"report_version 应为 4.x，实际 {rv!r}")

    checks = d.get("checks")
    if not checks:
        fail("报告里没有检查项")

    cov = d.get("coverage", {})
    total = cov.get("total")
    judged = cov.get("judged")
    unknown = cov.get("unknown")
    skipped = cov.get("skipped")
    low_conf = cov.get("low_confidence")

    if total != len(checks):
        fail(f"覆盖度 total 与检查项数不一致：{total} vs {len(checks)}")

    # 三种「不确定」要能分开计数（DEBT-009）：
    #   skipped = 不适用 / unknown = 没测到 / low_confidence = 测到了但不可信
    # 把它们混为一谈正是 DEBT-009 要修的病根。
    if total != judged + unknown + skipped:
        fail(f"覆盖度三类之和对不上：{total} != {judged} + {unknown} + {skipped}")

    # trustworthy = 有可信结论的项数（ADR-0011）
    if cov.get("trustworthy") != judged - low_conf:
        fail(f"trustworthy 应等于 judged - low_confidence："
             f"{cov.get('trustworthy')} != {judged} - {low_conf}")

    # 分类侧的分母必须与实际打分分母一致（低置信 FAIL 保留、低置信 PASS 剔除）
    for cat in d.get("score", {}).get("categories", []):
        if cat.get("score") is None:
            continue
        if cat.get("usable") != cat.get("judged") - cat.get("low_confidence"):
            fail(f"分类 {cat.get('category')} 的 usable 与 judged/low_confidence 对不上："
                 f"{cat.get('usable')} != {cat.get('judged')} - {cat.get('low_confidence')}")

    print(f"✓ 冒烟通过：{len(checks)} 项检查，"
          f"覆盖 {cov.get('percent')}%，"
          f"可信结论 {cov.get('trustworthy')} 项，"
          f"存疑 {low_conf} 项，"
          f"退出码 {proc.returncode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
