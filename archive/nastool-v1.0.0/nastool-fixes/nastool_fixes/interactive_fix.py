"""
fixes/interactive_fix.py - 交互式修复 UI（v5.1.0）

在已有 check 结果的基础上，提供分类引导的修复交互界面。
"""

from __future__ import annotations

import sys
from typing import Dict, List, TYPE_CHECKING, Tuple

from .fix_recommendations import (
    FIX_RECOMMENDATIONS,
    MANUAL_CATEGORIES,
    get_recommendations,
    get_manual_category,
    has_fix,
    summarize_check,
)
from .registry import run_fix
from .base import FixResult

if TYPE_CHECKING:
    from nastool_core.checks.base import CheckResult
else:
    from nastool_core.checks.base import CheckResult, CheckSeverity


# ─────────────────────────────────────────────────────────────────────────────
# 颜色输出（跨平台）
# ─────────────────────────────────────────────────────────────────────────────

try:
    from colorama import init as _colorama_init
    _colorama_init(autoreset=True)
    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    RED = "\x1b[31m"
    YEL = "\x1b[33m"
    GRN = "\x1b[32m"
    CYN = "\x1b[36m"
    MAG = "\x1b[35m"
    DIM = "\x1b[2m"
except ImportError:
    RESET = BOLD = RED = YEL = GRN = CYN = MAG = DIM = ""


# ─────────────────────────────────────────────────────────────────────────────
# 分组映射（按 fix 所属分类显示）
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_EMOJI = {
    "system":    "[S] 系统类",
    "storage":   "[D] 存储类",
    "network":   "[N] 网络类",
    "ai":        "[A] AI加速",
    "security":  "[X] 安全类",
    "nas":       "[Z] NAS类",
}

CATEGORY_FIX_MAP = {
    # fix_id -> category（与 fixes/__init__.py 目录结构一致）
    "install_python":         "system",
    "install_docker":         "system",
    "setup_logrotate":        "system",
    "cleanup_logs":           "storage",
    "cleanup_docker_images":  "storage",
    "cleanup_tmp_space":      "storage",
    "create_paths":           "storage",
    "config_raid_recovery":  "storage",
    "config_dns":            "network",
    "install_cuda":           "ai",
    "disable_root_login":     "security",
    "enable_fail2ban":        "security",
    "enforce_password_policy":"security",
    "renew_ssl_cert":         "security",
    "config_ups_shutdown":    "nas",
}


# ─────────────────────────────────────────────────────────────────────────────
# 核心交互函数
# ─────────────────────────────────────────────────────────────────────────────

def interactive_fix_flow(results: List[CheckResult], auto: bool = False) -> None:
    """
    主入口：接收 check 结果列表，启动交互式修复引导。

    Args:
        results:  所有检查结果（包含 WARNING 和 CRITICAL）
        auto:     True 则跳过确认直接执行（对应 --fix --auto）
    """
    failed = [r for r in results if r.severity in (CheckSeverity.WARNING, CheckSeverity.CRITICAL)]

    if not failed:
        print(f"{GRN}[OK] 没有检测到需要修复的问题{RESET}")
        return

    # 按"有 fix"和"无 fix"分组
    fixable, manual = _categorize(failed)

    print()
    print(f"{BOLD}{'━' * 60}{RESET}")
    print(f"{BOLD}[*] 智能修复向导{RESET}")
    print(f"{'━' * 60}{RESET}")

    if fixable:
        _show_fixable(fixable)
        _interactive_select_and_run(fixable, auto)
    else:
        print(f"\n{DIM}当前没有可自动修复的项{RESET}")

    if manual:
        _show_manual(manual)

    _show_footer()


def _categorize(failed: List[CheckResult]) -> Tuple[list, list]:
    """将有修复建议的和纯人工处理的项分开"""
    fixable, manual = [], []
    for r in failed:
        if has_fix(r.check_id):
            fixable.append(r)
        else:
            manual.append(r)
    return fixable, manual


def _show_fixable(fixable: List[CheckResult]) -> None:
    """按 fix 类别分组展示可修复项"""
    # 1. 先按类别聚合
    by_cat: Dict[str, list] = {}
    for r in fixable:
        recs = get_recommendations(r.check_id)
        for rec in recs:
            cat = CATEGORY_FIX_MAP.get(rec["fix_id"], "system")
            by_cat.setdefault(cat, []).append((r, rec))

    # 2. 按严重程度排序
    SEV_ORDER = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    by_cat = dict(sorted(by_cat.items(), key=lambda x: x[0]))

    total_items = 0
    for cat, items in by_cat.items():
        emoji_label = CATEGORY_EMOJI.get(cat, cat)
        # 计算高危项（CRITICAL）
        crit_count = sum(1 for r, _ in items if r.severity.name == "CRITICAL")
        crit_str = f" {RED}({crit_count}项严重){RESET}" if crit_count else ""
        print(f"\n{emoji_label}{crit_str}")
        for r, rec in items:
            sev = _severity_icon(r.severity.name)
            fix_id = rec["fix_id"]
            action = rec["action"]
            warn = rec.get("warning", "")
            warn_str = f" {YEL}{warn}{RESET}" if warn else ""
            # 编号
            idx = total_items + 1
            print(f"  {GRN}[{idx}]{RESET} {sev} {DIM}{r.check_id}{RESET}")
            print(f"       -> {action}{warn_str}")
            total_items += 1

    print(f"\n{DIM}共 {total_items} 项可修复{RESET}")


def _interactive_select_and_run(fixable: List[CheckResult], auto: bool) -> None:
    """让用户选择要修复的项并执行"""
    if auto:
        # --auto 模式：逐个执行所有 fixable 项
        print(f"\n{MAG}[>>>] --auto 模式：自动执行所有修复...{RESET}")
        for r in fixable:
            recs = get_recommendations(r.check_id)
            for rec in recs:
                _run_single_fix(rec["fix_id"], auto=True)
        return

    # 交互模式
    print()
    print(f"{CYN}请输入要执行的编号（逗号分隔，如 1,3,5），或按 q 退出：{RESET}", end=" ")

    try:
        raw = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{DIM}已退出{RESET}")
        return

    if raw in ("q", "quit", "exit"):
        print(f"{DIM}已退出{RESET}")
        return

    # 解析编号
    try:
        indices = set(int(x.strip()) for x in raw.split(",") if x.strip())
    except ValueError:
        print(f"{RED}[X] 输入无效{RESET}")
        return

    # 重新计算 total_items（与上面展示顺序一致）
    total = 0
    for r in fixable:
        recs = get_recommendations(r.check_id)
        for rec in recs:
            total += 1

    # 收集要执行的 fix_id（去重）
    fix_ids = set()
    idx = 0
    for r in fixable:
        recs = get_recommendations(r.check_id)
        for rec in recs:
            idx += 1
            if idx in indices:
                fix_ids.add(rec["fix_id"])

    if not fix_ids:
        print(f"{DIM}没有选择任何项{RESET}")
        return

    print()
    for fix_id in sorted(fix_ids):
        _run_single_fix(fix_id, auto=False)


def _run_single_fix(fix_id: str, auto: bool) -> None:
    """执行单个 fix，并打印结果"""
    print(f"\n{'─' * 50}")
    print(f"[>] 执行: {fix_id}")
    result: FixResult = run_fix(fix_id, confirm=not auto)

    if result.success:
        print(f"{GRN}[OK] {result.message}{RESET}")
    else:
        print(f"{RED}[X] {result.message}{RESET}")


def _show_manual(manual: List[CheckResult]) -> None:
    """展示需要人工处理的问题（按类别折叠/分组）"""
    print()
    print(f"{YEL}{'━' * 60}{RESET}")
    print(f"{YEL}[M] 需人工处理的问题（共 {len(manual)} 项）{RESET}")
    print(f"{'─' * 60}{RESET}")

    # 按人工类别分组
    by_cat: Dict[str, list] = {}
    uncategorized = []
    for r in manual:
        cat = get_manual_category(r.check_id)
        if cat:
            by_cat.setdefault(cat["label"], []).append(r)
        else:
            uncategorized.append(r)

    for label, items in by_cat.items():
        print(f"\n{label}")
        for r in items:
            sev = _severity_icon(r.severity.name)
            print(f"  {sev} {DIM}{r.check_id}{RESET}")
            if r.message:
                # 截断过长的消息
                msg = r.message[:80] + ("…" if len(r.message) > 80 else "")
                print(f"       {DIM}{msg}{RESET}")

    if uncategorized:
        print(f"\n{YEL}[?] 其他{RESET}")
        for r in uncategorized:
            sev = _severity_icon(r.severity.name)
            print(f"  {sev} {DIM}{r.check_id}{RESET}")
            msg = r.message[:80] + ("…" if len(r.message) > 80 else "")
            print(f"       {DIM}{msg}{RESET}")


def _show_footer() -> None:
    print()
    print(f"{DIM}[!] 提示：即使选择了修复项，系统也会在执行高危操作前再次确认。{RESET}")
    print(f"{DIM}   如需查看所有可用 fix，请运行: python arm_diagnose.py --list-fixes{RESET}")


def _severity_icon(sev: str) -> str:
    return {
        "CRITICAL": f"{RED}[X]{RESET}",
        "WARNING":  f"{YEL}[!]{RESET}",
        "INFO":     f"{DIM}[i]{RESET}",
    }.get(sev, f"{DIM}[·]{RESET}")
