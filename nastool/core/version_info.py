# -*- coding: utf-8 -*-
"""
nastool/core/version_info.py
统一版本信息获取，用于 --version 输出和版本提示
"""
from checks import list_checks

__all__ = ["get_version_info", "VERSION_INFO"]


def get_git_info() -> dict:
    """获取 Git 版本信息（失败时返回空）"""
    import subprocess, os, pathlib

    root = pathlib.Path(__file__).parent.parent.parent
    try:
        hash_r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(root), capture_output=True, text=True, timeout=5,
        )
        date_r = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            cwd=str(root), capture_output=True, text=True, timeout=5,
        )
        branch_r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(root), capture_output=True, text=True, timeout=5,
        )
        if hash_r.returncode == 0:
            return {
                "hash": hash_r.stdout.strip(),
                "date": date_r.stdout.strip()[:10] if date_r.returncode == 0 else "",
                "branch": branch_r.stdout.strip() if branch_r.returncode == 0 else "",
                "dirty": subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(root), capture_output=True, timeout=5,
                ).stdout.strip() != "",
            }
    except Exception:
        pass
    return {"hash": "", "date": "", "branch": "", "dirty": False}


def get_check_counts() -> dict:
    """获取各 category 的检查数量"""
    try:
        checks = list_checks()
        from collections import Counter
        cats = Counter(v.get("category", "?") for v in checks.values())
        total = sum(cats.values())
        parts = " / ".join(f"{cats.get(c, 0)}" for c in ("system", "network", "storage", "security", "nas", "ai", "usb"))
        return {"total": total, "by_category": dict(cats), "parts": parts}
    except Exception:
        return {"total": 0, "by_category": {}, "parts": "?"}


def get_version_info() -> dict:
    """获取完整的版本信息字典"""
    git = get_git_info()
    checks = get_check_counts()
    return {
        "version": "7.1.0-beta",
        "git_hash": git.get("hash", ""),
        "git_date": git.get("date", ""),
        "git_branch": git.get("branch", ""),
        "git_dirty": git.get("dirty", False),
        "checks_total": checks["total"],
        "checks_parts": checks["parts"],
        "checks_by_category": checks["by_category"],
    }


def format_version_text(info: dict = None) -> str:
    """格式化 --version 输出的纯文本"""
    if info is None:
        info = get_version_info()

    lines = [f"nastool {info['version']}"]
    if info.get("git_hash"):
        dirty = " (dirty)" if info.get("git_dirty") else ""
        branch = f" [{info.get('git_branch')}]" if info.get("git_branch") else ""
        lines.append(f"Git:    {info['git_hash']}{branch}{dirty} ({info.get('git_date', 'n/a')})")
    lines.append(f"Checks: {info['checks_total']} registered ({info['checks_parts']})")
    return "\n".join(lines)


def format_version_json(info: dict = None) -> str:
    """格式化 --version --json 输出的 JSON"""
    import json
    if info is None:
        info = get_version_info()
    return json.dumps(info, indent=2, ensure_ascii=False)
