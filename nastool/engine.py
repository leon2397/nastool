"""
nastool/engine.py — 执行引擎

职责单一：按 profile / --only / --skip 挑出检查项，逐个执行，
把任何意外都收敛成一条 CheckResult，永远不中断整次检测。

关键设计：
  · 依赖不满足 → SKIP，而不是猜一个结论（缺 smartctl 绝不能报「SMART 正常」）
  · 检查器抛异常 → UNKNOWN + error，而不是让整份报告失败
  · 采集器崩了 → 空事实 + 记录到 collect_errors，对应项自然落到不可判定
"""
from __future__ import annotations

import datetime
import hashlib
import os
import platform as _platform
import signal
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from . import __version__
from . import checks  # noqa: F401  导入即注册全部检查项
from .context import CheckContext
from .model import CheckResult, Report, ReportMeta, Status
from .profiles import get_profile, with_categories
from .registry import CheckMeta, resolve
from .scoring import compute


@dataclass
class RunOptions:
    storage_path: str = ""
    peers: List[str] = field(default_factory=list)
    do_speed_test: bool = True
    do_smart: bool = True
    do_ai: bool = True
    do_internet_check: bool = True
    verbose: bool = False
    profile: str = "nas"
    only: List[str] = field(default_factory=list)
    skip: List[str] = field(default_factory=list)
    enable: List[str] = field(default_factory=list)
    check_timeout: int = 60      # 单项检查的硬超时（秒），仅 POSIX 生效


ProgressFn = Callable[[int, int, CheckMeta], None]


# ── 单项超时（Unix 可用；Windows 依赖各采集器自身的 subprocess timeout）──
@contextmanager
def _time_limit(seconds: int):
    if seconds and hasattr(signal, "SIGALRM") and os.name == "posix":
        def _raise(signum, frame):
            raise TimeoutError(f"检查超时（>{seconds}s）")

        old = signal.signal(signal.SIGALRM, _raise)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    else:
        yield


def _skipped(meta: CheckMeta, reason: str) -> CheckResult:
    return CheckResult(
        id=meta.id, title=meta.title, category=meta.category,
        weight=meta.weight, status=Status.SKIP,
        summary=reason, confidence=0.0,
    )


def _run_one(meta: CheckMeta, ctx: CheckContext,
             timeout: int = 60) -> CheckResult:
    # 1) 平台适用性
    plats = [p for p in meta.platforms if p]
    if plats and "any" not in plats:
        if not any(ctx.has(p) for p in plats):
            return _skipped(meta, f"当前平台不适用（需要 {' / '.join(plats)}）")

    # 2) 依赖能力
    missing = [r for r in meta.requires if not ctx.has(r)]
    if missing:
        return _skipped(meta, f"缺少依赖：{', '.join(missing)}，本次未检测")

    # 3) 执行
    started = time.time()
    try:
        with _time_limit(timeout):
            payload = meta.function(ctx)
    except Exception as e:  # noqa: BLE001 - 单项失败不影响整体
        return CheckResult(
            id=meta.id, title=meta.title, category=meta.category,
            weight=meta.weight, status=Status.UNKNOWN,
            summary="检查执行失败，本次无法判定",
            error=f"{type(e).__name__}: {e}",
            confidence=0.0,
            duration_ms=int((time.time() - started) * 1000),
        )

    elapsed = int((time.time() - started) * 1000)

    if isinstance(payload, CheckResult):
        result = payload
        result.id = result.id or meta.id
        result.title = result.title or meta.title
        result.category = result.category or meta.category
        result.weight = meta.weight
    else:
        data = dict(payload or {})
        data.pop("weight", None)
        result = CheckResult(
            id=meta.id, title=meta.title, category=meta.category,
            weight=meta.weight, **data,
        )

    result.duration_ms = elapsed
    if result.confidence is None:
        result.confidence = _default_confidence(result.status)
    return result


def _default_confidence(status: Status) -> float:
    return {
        Status.PASS: 0.9,
        Status.WARN: 0.85,
        Status.FAIL: 0.85,
        Status.UNKNOWN: 0.0,
        Status.SKIP: 0.0,
    }.get(status, 0.5)


def _fingerprint(platform_facts) -> str:
    """设备指纹：同一台机器两次检测应当一致，用于历史对比时校验。"""
    raw = "|".join([
        _platform.node(),
        str(getattr(platform_facts, "arch", "")),
        str(getattr(platform_facts, "facts", {}).get("model", "")),
        str(getattr(platform_facts, "vendor", "")),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def run(options: Optional[RunOptions] = None,
        progress: Optional[ProgressFn] = None) -> Report:
    """执行一次完整检测，返回 Report。"""
    opts = options or RunOptions()
    started = time.time()

    profile = with_categories(get_profile(opts.profile), opts.enable)
    ctx = CheckContext(opts, profile)

    # 平台必须先采：它决定后续哪些检查项适用
    platform_facts = ctx.platform

    # --only 是显式指定，此时忽略 profile 的分类裁剪
    categories = None if opts.only else profile.active
    metas = resolve(only=opts.only, skip=opts.skip, categories=categories)

    total = len(metas)
    checks: List[CheckResult] = []
    for idx, meta in enumerate(metas, 1):
        if progress:
            progress(idx, total, meta)
        checks.append(_run_one(meta, ctx, timeout=opts.check_timeout))

    score, coverage = compute(checks, profile, ai_facts=ctx.ai)

    report = Report()
    report.meta = ReportMeta(
        version=__version__,
        generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        duration_s=round(time.time() - started, 1),
        hostname=_platform.node(),
        profile=profile.key,
        python=_platform.python_version(),
        platform_summary=_platform.platform(terse=True),
        fingerprint=_fingerprint(platform_facts),
        options={
            "storage_path": ctx.resolve_storage_path,
            "peers": list(opts.peers),
            "speed_test": opts.do_speed_test,
            "smart": opts.do_smart,
            "ai": opts.do_ai,
            "internet": opts.do_internet_check,
            "only": list(opts.only),
            "skip": list(opts.skip),
        },
    )
    report.platform = platform_facts
    report.facts = ctx.facts()
    report.checks = checks
    report.score = score
    report.coverage = coverage
    report.collect_errors = [f"{k}: {v}" for k, v in ctx.collector_errors.items()]
    return report
