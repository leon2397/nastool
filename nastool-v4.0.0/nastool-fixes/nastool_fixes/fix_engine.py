# -*- coding: utf-8 -*-
"""
fixes/fix_engine.py - Unified fix engine (v7.0)

Merged from:
  - fix_engine_v2.py  (snapshots + dry-run)
  - fix_recommendations.py  (check->fix mapping)
  - interactive_fix.py  (interactive UI)

Single file, clear architecture, no duplication.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from checks.base import CheckResult


# ── Risk levels ──────────────────────────────────────────────────────────────

class FixRisk:
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    DANGER = "danger"   # destructive, requires explicit confirmation


# ── Check -> Fix mapping ──────────────────────────────────────────────────────

@dataclass
class FixRec:
    """A single fix recommendation for a check."""
    fix_id: str
    action: str
    auto_applicable: bool = True
    risk: str = FixRisk.LOW
    requires_root: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# Map: check_id -> list of FixRec
FIX_MAP: Dict[str, List[FixRec]] = {
    "python_version":           [FixRec("install_python",        "升级 Python 版本",    auto_applicable=True,  risk=FixRisk.MEDIUM, requires_root=True)],
    "pip_installed":            [FixRec("install_python",        "安装 pip",             auto_applicable=True,  risk=FixRisk.MEDIUM, requires_root=True)],
    "docker_info":              [FixRec("install_docker",         "安装/修复 Docker",     auto_applicable=True,  risk=FixRisk.MEDIUM, requires_root=True)],
    "docker_compose_installed": [FixRec("install_docker",        "安装 Docker Compose",  auto_applicable=True,  risk=FixRisk.MEDIUM, requires_root=True)],
    "docker_images":            [FixRec("cleanup_docker_images",  "清理未使用镜像",       auto_applicable=True,  risk=FixRisk.LOW)],
    "logrotate_config":         [FixRec("setup_logrotate",       "配置日志轮转",         auto_applicable=True,  risk=FixRisk.LOW,   requires_root=True)],
    "log_disk_usage":           [FixRec("cleanup_logs",          "清理系统日志",         auto_applicable=True,  risk=FixRisk.MEDIUM)],
    "tmp_space":                [FixRec("cleanup_tmp_space",      "清理临时文件",         auto_applicable=True,  risk=FixRisk.LOW)],
    "system_disk":              [FixRec("create_paths",           "创建必要目录",         auto_applicable=True,  risk=FixRisk.LOW)],
    "raid_status":              [FixRec("config_raid_recovery",   "RAID 重建/恢复",       auto_applicable=False, risk=FixRisk.HIGH,  requires_root=True)],
    "dns_resolve":             [FixRec("config_dns",             "配置 DNS 服务器",      auto_applicable=True,  risk=FixRisk.LOW,   requires_root=True)],
    "cuda_version":             [FixRec("install_cuda",           "升级 CUDA",            auto_applicable=True,  risk=FixRisk.HIGH,  requires_root=True)],
    "ssh_root":                 [FixRec("disable_root_login",     "禁用 SSH root 登录",   auto_applicable=True,  risk=FixRisk.MEDIUM, requires_root=True)],
    "login_failures":          [FixRec("enable_fail2ban",       "启用 Fail2ban",        auto_applicable=True,  risk=FixRisk.MEDIUM, requires_root=True)],
    "password_policy":          [FixRec("enforce_password_policy","强制密码策略",         auto_applicable=True,  risk=FixRisk.MEDIUM, requires_root=True)],
    "ssl_cert":                 [FixRec("renew_ssl_cert",        "续期 SSL 证书",        auto_applicable=False, risk=FixRisk.MEDIUM, requires_root=True)],
    "ups_status":               [FixRec("config_ups_shutdown",  "配置 UPS 关机",        auto_applicable=False, risk=FixRisk.MEDIUM, requires_root=True)],
    "gpu_detected":             [FixRec("install_gpu_driver",    "安装 GPU 驱动",        auto_applicable=True,  risk=FixRisk.HIGH,  requires_root=True)],
    "gpu_memory":               [FixRec("free_gpu_memory",       "释放 GPU 显存",        auto_applicable=True,  risk=FixRisk.LOW)],
    "tensorflow_version":        [FixRec("install_tensorflow",   "安装 TensorFlow",       auto_applicable=True,  risk=FixRisk.MEDIUM)],
    "keras_version":            [FixRec("install_keras",         "安装 Keras",            auto_applicable=True,  risk=FixRisk.MEDIUM)],
}


# Manual categories (no auto-fix available)
MANUAL_CATEGORIES = {
    "system":   "需人工处理的系统问题",
    "storage":  "需人工处理的存储问题",
    "network":  "需人工处理的网络问题",
    "security": "需人工处理的安全问题",
    "nas":      "需人工处理的 NAS 问题",
    "ai":       "需人工处理的 AI 问题",
}


# ── Results ───────────────────────────────────────────────────────────────────

@dataclass
class FixResult:
    """Result of a fix execution."""
    fix_id: str
    check_id: str
    action: str
    success: bool
    dry_run: bool = False
    risk: str = FixRisk.LOW
    before_state: Optional[dict] = None
    after_state: Optional[dict] = None
    error: Optional[str] = None
    warning: Optional[str] = None
    commands_run: List[str] = field(default_factory=list)
    rollback_cmd: Optional[str] = None

    def summary(self) -> str:
        if self.dry_run:
            return f"[dry-run] {self.action}"
        if self.success:
            return f"[OK] {self.action}"
        return f"[X] {self.action}: {self.error}"


# ── Snapshot ─────────────────────────────────────────────────────────────────

@dataclass
class FixSnapshot:
    """Before/after state snapshot."""
    timestamp: str
    check_id: str
    fix_id: str
    before: dict
    after: Optional[dict] = None
    success: bool = False
    error: Optional[str] = None


# ── FixEngine ─────────────────────────────────────────────────────────────────

class FixEngine:
    """
    Unified fix engine.

    Usage:
        engine = FixEngine()
        recs = engine.get_recommendations(check_results)
        result = engine.execute("cleanup_docker_images", "docker_images", dry_run=True)
        engine.interactive_flow(check_results)  # full interactive flow
    """

    def __init__(self, snapshot_dir: str = "~/.nastool/fix_snapshots"):
        self.snapshot_dir = Path(os.path.expanduser(snapshot_dir))
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    # ── Recommendations ────────────────────────────────────────────────────────

    def get_recommendations(
        self,
        check_results: List["CheckResult"],
        auto_only: bool = False,
    ) -> Dict[str, List[FixRec]]:
        """
        Get fix recommendations grouped by risk category.

        Args:
            check_results: List of CheckResult objects (or dicts)
            auto_only: Only return auto-applicable fixes

        Returns:
            {"auto_fixable": [...], "manual": [...], "low_risk": [...], "high_risk": [...]}
        """
        auto, manual, low, high = [], [], [], []

        for result in check_results:
            check_id = result.check_id if hasattr(result, "check_id") else result.get("check_id", "")
            if not result.passed and check_id in FIX_MAP:
                for rec in FIX_MAP[check_id]:
                    if auto_only and not rec.auto_applicable:
                        continue
                    rec_copy = FixRec(
                        fix_id=rec.fix_id,
                        action=rec.action,
                        auto_applicable=rec.auto_applicable,
                        risk=rec.risk,
                        requires_root=rec.requires_root,
                    )
                    rec_copy._check_id = check_id   # attach for reference
                    if rec.risk in (FixRisk.HIGH, FixRisk.DANGER):
                        high.append(rec_copy)
                    else:
                        low.append(rec_copy)

        return {
            "auto_fixable": [r for r in low if r.auto_applicable],
            "manual": [r for r in low if not r.auto_applicable],
            "low_risk": low,
            "high_risk": high,
        }

    def has_fix(self, check_id: str) -> bool:
        """Check if any fix exists for a check_id."""
        return check_id in FIX_MAP

    def get_fixes(self, check_id: str) -> List[FixRec]:
        """Get all fix recommendations for a check_id."""
        return FIX_MAP.get(check_id, [])

    # ── Execution ─────────────────────────────────────────────────────────────

    def execute(
        self,
        fix_id: str,
        check_id: str = "",
        dry_run: bool = False,
        force: bool = False,
        auto_rollback: bool = True,
    ) -> FixResult:
        """
        Execute a single fix.

        Args:
            fix_id: Fix identifier
            check_id: Related check identifier
            dry_run: Show what would happen without executing
            force: Skip confirmation prompts
            auto_rollback: 是否在修复失败时自动回滚

        Returns:
            FixResult
        """
        rec = self._find_rec(fix_id)
        if not rec:
            return FixResult(fix_id, check_id, "unknown", False, dry_run=dry_run,
                             error=f"Unknown fix_id: {fix_id}")

        action = rec.action

        # Dry-run
        if dry_run:
            return FixResult(
                fix_id=fix_id, check_id=check_id, action=action,
                success=True, dry_run=True, risk=rec.risk,
                warning=f"[DRY-RUN] 将执行: {action}",
            )

        # High-risk confirmation
        if rec.risk in (FixRisk.HIGH, FixRisk.DANGER) and not force:
            print(f"[!]  高风险操作: {action}")
            print(f"   风险等级: {rec.risk}")
            try:
                resp = input("   确认执行? [y/N]: ").strip().lower()
                if resp not in ("y", "yes"):
                    return FixResult(fix_id, check_id, action, False,
                                     error="Cancelled by user")
            except EOFError:
                return FixResult(fix_id, check_id, action, False,
                                 error="No terminal for confirmation")

        # Snapshot
        snapshot = self._take_snapshot(check_id, fix_id)

        # Execute via registry
        from .registry import run_fix_with_rollback
        try:
            fix_result = run_fix_with_rollback(fix_id, confirm=False, auto_rollback=auto_rollback)
            if fix_result.success:
                after = self._take_snapshot(check_id, fix_id)
                self._save_snapshot(snapshot, after, success=True)
                return FixResult(
                    fix_id=fix_id, check_id=check_id, action=action,
                    success=True, risk=rec.risk,
                    before_state=snapshot,
                    after_state=after,
                    commands_run=fix_result.commands_run if hasattr(fix_result, "commands_run") else [],
                    rollback_cmd=fix_result.rollback_command if hasattr(fix_result, "rollback_command") else None,
                    rollback_status=fix_result.rollback_status if hasattr(fix_result, "rollback_status") else None,
                )
            else:
                self._save_snapshot(snapshot, None, success=False, error=fix_result.error)
                return FixResult(fix_id, check_id, action, False,
                                 risk=rec.risk, error=fix_result.error,
                                 rollback_status=fix_result.rollback_status if hasattr(fix_result, "rollback_status") else None)
        except Exception as e:
            self._save_snapshot(snapshot, None, success=False, error=str(e))
            return FixResult(fix_id, check_id, action, False,
                             risk=rec.risk, error=str(e))

    def execute_auto(
        self,
        check_results: List["CheckResult"],
    ) -> List[FixResult]:
        """
        Auto-execute all applicable fixes (--fix --auto mode).

        Args:
            check_results: List of CheckResult objects

        Returns:
            List of FixResult
        """
        recs = self.get_recommendations(check_results, auto_only=True)
        results = []
        for rec in recs["auto_fixable"]:
            check_id = getattr(rec, "_check_id", "")
            result = self.execute(rec.fix_id, check_id)
            results.append(result)
            print(f"  {result.summary()}")
        return results

    # ── Interactive flow ──────────────────────────────────────────────────────

    def interactive_flow(
        self,
        check_results: List["CheckResult"],
    ) -> None:
        """
        Full interactive fix flow (--fix mode without --auto).
        """
        recs = self.get_recommendations(check_results)

        total_auto = len(recs["auto_fixable"])
        total_manual = len(recs["manual"])
        total_high = len(recs["high_risk"])

        print()
        print("─" * 60)
        print(f"  📋 修复推荐报告")
        print("─" * 60)

        if total_auto == 0 and total_manual == 0 and total_high == 0:
            print("  [OK] 没有发现需要修复的问题")
            return

        if total_auto > 0:
            print(f"\n  [OK] 可自动修复 ({total_auto} 项)")
            for i, rec in enumerate(recs["auto_fixable"], 1):
                check_id = getattr(rec, "_check_id", "")
                print(f"    {i}. [{rec.fix_id}] {rec.action} (check: {check_id})")

        if total_high > 0:
            print(f"\n  🔴 高风险需确认 ({total_high} 项)")
            for i, rec in enumerate(recs["high_risk"], 1):
                check_id = getattr(rec, "_check_id", "")
                print(f"    {i}. [{rec.fix_id}] {rec.action} (check: {check_id})")

        if total_manual > 0:
            print(f"\n  [!] 需人工处理 ({total_manual} 项)")
            for rec in recs["manual"]:
                check_id = getattr(rec, "_check_id", "")
                print(f"    • [{rec.fix_id}] {rec.action} (check: {check_id})")

        print()
        try:
            resp = input("输入要执行的修复编号 (逗号分隔)，或 'a' 执行全部自动修复，'q' 退出: ").strip().lower()
        except EOFError:
            resp = "q"

        if resp == "q":
            print("  已退出")
            return

        all_recs = recs["auto_fixable"] + recs["high_risk"]
        if resp == "a":
            targets = recs["auto_fixable"]
        else:
            indices = []
            for part in resp.split(","):
                part = part.strip()
                if part.isdigit():
                    indices.append(int(part) - 1)
            targets = [all_recs[i] for i in indices if 0 <= i < len(all_recs)]

        print()
        results = []
        for rec in targets:
            check_id = getattr(rec, "_check_id", "")
            result = self.execute(rec.fix_id, check_id)
            results.append(result)
            print(f"  {result.summary()}")

        # Summary
        ok = sum(1 for r in results if r.success)
        fail = len(results) - ok
        print()
        print(f"  完成: [OK] {ok} 成功, [X] {fail} 失败")

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _find_rec(self, fix_id: str) -> Optional[FixRec]:
        for recs in FIX_MAP.values():
            for rec in recs:
                if rec.fix_id == fix_id:
                    return rec
        return None

    def _take_snapshot(self, check_id: str, fix_id: str) -> dict:
        return {
            "timestamp": datetime.now().isoformat(),
            "check_id": check_id,
            "fix_id": fix_id,
            "note": "simplified snapshot",
        }

    def _save_snapshot(
        self,
        before: dict,
        after: Optional[dict],
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        data = {
            "timestamp": before["timestamp"],
            "check_id": before["check_id"],
            "fix_id": before["fix_id"],
            "before": before,
            "after": after,
            "success": success,
            "error": error,
        }
        try:
            path = self.snapshot_dir / f"{before['fix_id']}_{ts}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass   # snapshot failure is non-fatal


# ── Convenience ───────────────────────────────────────────────────────────────

def get_recommendations_for(check_id: str) -> List[FixRec]:
    """Get fix recommendations for a single check_id."""
    return FIX_MAP.get(check_id, [])


def has_fix(check_id: str) -> bool:
    """Check if check has any fix."""
    return check_id in FIX_MAP


def summarize_check(check_id: str) -> str:
    """Human-readable summary of available fixes for a check."""
    recs = get_recommendations_for(check_id)
    if not recs:
        cats = MANUAL_CATEGORIES.values()
        return f"需人工处理 ({', '.join(cats)})"
    actions = [r.action for r in recs]
    return "; ".join(actions)
