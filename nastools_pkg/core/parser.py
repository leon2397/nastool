# -*- coding: utf-8 -*-
"""
nastools_pkg/core/parser.py — 检测结果解析

将 nastool CheckResult 或远程执行返回的 dict 列表
转换为 GUI 可消费的结构化数据。

v1.1: 最小实现，nastools GUI 通过 RemoteExecutor.to_json()
直接获取 dict，parser 仅提供批量转换便利函数。
"""

from __future__ import annotations

from typing import Any, Dict, List


def parse_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse a list of check result dicts into a summary structure.

    Parameters
    ----------
    results : list[dict]
        Each dict comes from ``RemoteExecutor.to_json()`` or
        ``RemoteExecutor.run()``.

    Returns
    -------
    dict
        Summary with keys: ``total``, ``passed``, ``failed``, ``warnings``,
        ``items``.
    """
    passed = 0
    failed = 0
    warnings = 0
    items: List[Dict[str, Any]] = []

    for r in results:
        sev = r.get("severity", "info")
        if sev in ("ok", "passed", "info"):
            passed += 1
        elif sev in ("error", "critical", "failed"):
            failed += 1
        else:
            warnings += 1
        items.append(r)

    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "items": items,
    }
