# -*- coding: utf-8 -*-
"""
gui/integration.py - 新模块 API 桥接层

将 nastool_modules 的模块化 API 转换为 GUI 期望的格式。
"""

from __future__ import annotations

from typing import Optional, Callable
from dataclasses import dataclass, field

# ── 新模块 API ─────────────────────────────────────────────────────
from nastool_core.checks import run_mock_checks, list_available_checks
from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
from nastool_core.data.mock_results import get_mock_result
from nastool_fixes import get_fix, list_available_fixes, get_all_fixes
from nastool_reporters import TerminalReporter, JSONReporter, HTMLReporter

# ── 旧版映射（兼容性） ─────────────────────────────────────────────
SEV_MAP = {
    "passed": "passed",
    "warning": "warning",
    "critical": "critical",
    "info": "info",
}


def sev_to_gui(sev: CheckSeverity) -> str:
    return SEV_MAP.get(sev.value, "info")


def sev_to_color(sev: CheckSeverity) -> str:
    return {
        "passed": "#3fb950",
        "warning": "#d29922",
        "critical": "#f85149",
        "info": "#58a6ff",
    }.get(sev.value, "#8b949e")


def cat_to_str(cat: CheckCategory) -> str:
    return cat.value if cat else "unknown"


# ── GUI 专用 CheckResult（flat dict 格式）──────────────────────────
@dataclass
class GUIResult:
    check_id: str
    title: str
    category: str
    severity: str       # passed/warning/critical/info
    passed: bool
    current: str
    expected: str
    message: str
    fix_available: bool
    fix_id: Optional[str]
    fix_title: str
    fix_risk: str
    fix_command: str


def to_gui_result(cr: CheckResult) -> GUIResult:
    return GUIResult(
        check_id=cr.check_id,
        title=cr.title,
        category=cat_to_str(cr.category),
        severity=sev_to_gui(cr.severity),
        passed=cr.passed,
        current=cr.current,
        expected=cr.expected,
        message=cr.message,
        fix_available=cr.fix_available,
        fix_id=cr.fix_id,
        fix_title=cr.fix_description or "",
        fix_risk=getattr(cr, "fix_risk", "low"),
        fix_command=cr.fix_command or "",
    )


# ── 核心执行器 ─────────────────────────────────────────────────────
class DiagnosisEngine:
    """
    诊断引擎，基于新模块化架构。

    两种模式：
    - mock():    使用模拟数据，无需真实设备（当前唯一可用模式）
    - adapter():  使用真实设备适配器（nastool_adapters，待实现）
    """

    def __init__(self, adapter=None):
        self.adapter = adapter

    def run_mock(
        self,
        profile: str = "healthy",
        full_mode: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[GUIResult]:
        """
        使用模拟数据运行检测。

        Args:
            profile: healthy / degraded / critical / mixed
            full_mode: 是否包含基准测试
            progress_callback: (current, total, check_id) -> None

        Returns:
            list[GUIResult] — 检测结果列表
        """
        checks = list_available_checks()
        total = len(checks)
        results: list[GUIResult] = []

        for i, check_id in enumerate(checks):
            cr = get_mock_result(check_id, profile)
            gui_result = to_gui_result(cr)
            results.append(gui_result)
            if progress_callback:
                progress_callback(i + 1, total, check_id)

        return results

    def run_real(
        self,
        full_mode: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        adapter_type: str = "",
        adapter_kwargs: Optional[dict] = None,
    ) -> list[GUIResult]:
        """
        使用真实设备适配器运行检测。

        Args:
            full_mode: 完整诊断（含基准测试）
            progress_callback: 进度回调
            adapter_type: 适配器类型 ("ssh", "http", "relay")
            adapter_kwargs: 适配器初始化参数

        Returns:
            list[GUIResult]
        """
        adapter_kwargs = adapter_kwargs or {}

        # HTTP 模式
        if adapter_type == "http":
            from nastool_adapters.http_detector import RemoteHTTPDetector
            self.adapter = RemoteHTTPDetector(**adapter_kwargs)
            connected = self.adapter.connect()
            if not connected:
                raise Exception(f"无法连接到 HTTP 目标: {adapter_kwargs.get('target_url')}")
        # SSH 模式
        elif adapter_type == "ssh":
            from nastool_adapters.ssh_detector import RemoteSSHDetector
            self.adapter = RemoteSSHDetector(**adapter_kwargs)
            connected = self.adapter.connect()
            if not connected:
                raise Exception(f"无法连接到 SSH 目标: {adapter_kwargs.get('host')}")
        # Relay 模式
        elif adapter_type == "relay":
            from nastool_adapters.relay_detector import RelayDetector
            self.adapter = RelayDetector(**adapter_kwargs)
            connected = self.adapter.connect()
            if not connected:
                raise Exception(f"无法连接到 Relay 目标")
        else:
            # 尝试用已设置的 adapter
            if not self.adapter:
                return []

        # 运行诊断
        try:
            if hasattr(self.adapter, "run_diagnosis"):
                raw_results = self.adapter.run_diagnosis(full_mode=full_mode)
            elif hasattr(self.adapter, "run"):
                raw_results = self.adapter.run()
            else:
                return []
        except Exception as e:
            print(f"[ERROR] 诊断失败: {e}")
            return []

        # 转换为 GUIResult
        results = []
        total = len(raw_results)
        for i, cr in enumerate(raw_results):
            gui_result = to_gui_result(cr)
            results.append(gui_result)
            if progress_callback:
                progress_callback(i + 1, total, cr.check_id)

        return results

    def run(
        self,
        mock: bool = True,
        profile: str = "healthy",
        full_mode: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        adapter_type: str = "",
        adapter_kwargs: Optional[dict] = None,
    ) -> tuple[list[GUIResult], int]:
        """
        主入口，自动选择模式。

        Returns:
            (results: list[GUIResult], score: int)
        """
        if mock:
            results = self.run_mock(profile, full_mode, progress_callback)
        else:
            results = self.run_real(full_mode, progress_callback,
                                    adapter_type=adapter_type,
                                    adapter_kwargs=adapter_kwargs)

        score = self._calc_score(results)
        return results, score

    def _calc_score(self, results: list[GUIResult]) -> int:
        if not results:
            return 0
        passed = sum(1 for r in results if r.passed)
        return round(passed / len(results) * 100)

    def list_categories(self, results: list[GUIResult]) -> list[str]:
        return sorted(set(r.category for r in results))

    def get_fixes(self, check_id: str) -> Optional[dict]:
        fixes = list_available_fixes()
        return fixes.get(check_id)
