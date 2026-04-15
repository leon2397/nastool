# -*- coding: utf-8 -*-
"""
core/executor.py - Asynchronous parallel check execution engine

Supports three execution levels:
  Level 0: Fully serial (fallback, no dependencies)
  Level 1: Category parallel (AI/Storage/System/Network/NAS/Security/USB each run in parallel)
  Level 2: Full DAG topological sort (respects depends_on declarations)

Usage:
  from core.executor import CheckExecutor
  executor = CheckExecutor(adapter, parallel_level=2)
  summary = executor.run_all()
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from checks.base import Check, CheckResult, CheckSummary, CheckSeverity, CheckCategory
from checks.registry import get_all_checks, get_check



class ParallelLevel(Enum):
    """Execution parallelism levels"""
    SERIAL = 0       # Fully serial (no parallelism)
    CATEGORY = 1      # Parallel by category
    DAG = 2           # Full DAG topological sort (default)


# ---------------------------------------------------------------------------
# Check metadata for dependency graph
# ---------------------------------------------------------------------------

@dataclass
class CheckMeta:
    """Metadata for a check, used by the DAG executor"""
    check_id: str
    title: str
    category: CheckCategory
    severity: CheckSeverity
    # Dependency: list of check_ids that must complete before this one runs
    depends_on: List[str] = field(default_factory=list)
    # Estimated execution time (seconds) — used for scheduling hints
    estimated_time: float = 0.5
    # Whether this check can run in parallel with others in same group
    can_parallel: bool = True
    # Timeout in seconds (0 = no timeout)
    timeout: float = 30.0
    # Tags for grouping
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_check_instance(cls, inst: Check) -> "CheckMeta":
        # severity / category / title may be class attributes or instance attributes
        severity = getattr(inst, "severity", None) or getattr(type(inst), "severity", CheckSeverity.INFO)
        category = getattr(inst, "category", None) or getattr(type(inst), "category", CheckCategory.SYSTEM)
        title = getattr(inst, "title", None) or getattr(type(inst), "title", inst.check_id)
        return cls(
            check_id=inst.check_id,
            title=title,
            category=category,
            severity=severity,
            depends_on=getattr(inst, "depends_on", []) or getattr(type(inst), "depends_on", []),
            estimated_time=getattr(inst, "estimated_time", 0.5),
            can_parallel=getattr(inst, "can_parallel", True),
            timeout=getattr(inst, "timeout", 30.0),
            tags=getattr(inst, "tags", []),
        )


# ---------------------------------------------------------------------------
# DAG utilities
# ---------------------------------------------------------------------------

class DependencyGraph:
    """Directed Acyclic Graph for check execution ordering"""

    def __init__(self, checks: List[Check]):
        self.checks = checks
        self.meta_map: Dict[str, CheckMeta] = {}
        self.graph: Dict[str, Set[str]] = defaultdict(set)   # check_id -> set of dependents
        self.reverse: Dict[str, Set[str]] = defaultdict(set)  # check_id -> set of dependencies

        self._build()

    def _build(self):
        """Build DAG from check instances (accepts classes or instances)"""
        # Step 1: Instantiate if needed (get_all_checks returns classes)
        instances = []
        for item in self.checks:
            if isinstance(item, type):  # It's a class
                try:
                    inst = item()
                    instances.append(inst)
                except Exception:
                    pass  # Skip checks that fail to instantiate
            else:  # Already an instance
                instances.append(item)
        self.checks = instances  # Normalize to instances

        # Step 2: Create meta for each check
        for inst in self.checks:
            self.meta_map[inst.check_id] = CheckMeta.from_check_instance(inst)

        # Step 2: Build adjacency lists
        for inst in self.checks:
            meta = self.meta_map[inst.check_id]
            for dep_id in meta.depends_on:
                if dep_id in self.meta_map:
                    self.reverse[inst.check_id].add(dep_id)
                    self.graph[dep_id].add(inst.check_id)

        # Step 3: Validate — check for cycles
        if self._has_cycle():
            raise ValueError("Check dependency graph contains a cycle!")

    def _has_cycle(self) -> bool:
        """DFS cycle detection"""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in self.meta_map:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def topological_sort(self) -> List[List[str]]:
        """
        Kahn's algorithm — returns levels (list of batches).
        Each batch contains check_ids that can run in parallel.
        """
        in_degree = defaultdict(int)
        for check_id in self.meta_map:
            in_degree[check_id] = len(self.reverse[check_id])

        levels: List[List[str]] = []
        remaining = set(self.meta_map.keys())

        while remaining:
            # Find all nodes with in_degree == 0
            ready = [cid for cid in remaining if in_degree[cid] == 0]
            if not ready:
                # Should not happen if no cycles, but guard anyway
                raise ValueError(
                    f"Cycle detected or unreachable nodes: {remaining}"
                )
            levels.append(ready)
            for cid in ready:
                remaining.remove(cid)
                for dependent in self.graph[cid]:
                    in_degree[dependent] -= 1

        return levels

    def get_dependents(self, check_id: str) -> List[str]:
        """Get all checks that depend on this check (directly or transitively)"""
        result: List[str] = []
        stack = list(self.graph.get(check_id, []))
        while stack:
            cid = stack.pop()
            if cid not in result:
                result.append(cid)
                stack.extend(self.graph.get(cid, []))
        return result

    def show_dag(self) -> str:
        """Return a text representation of the DAG for debugging"""
        lines = ["Check Dependency Graph", "=" * 40]
        for check_id, meta in sorted(self.meta_map.items()):
            deps = meta.depends_on
            if deps:
                lines.append(f"  {check_id} depends on: {deps}")
            else:
                lines.append(f"  {check_id} (no deps)")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-check timing record
# ---------------------------------------------------------------------------

@dataclass
class CheckTiming:
    check_id: str
    started_at: float = 0.0
    finished_at: float = 0.0
    duration_ms: float = 0.0
    error: Optional[str] = None
    result: Optional[CheckResult] = None

    def mark_start(self):
        self.started_at = time.perf_counter()

    def mark_done(self, result: Optional[CheckResult] = None, error: Optional[str] = None):
        self.finished_at = time.perf_counter()
        self.duration_ms = (self.finished_at - self.started_at) * 1000
        self.result = result
        self.error = error


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

class CheckExecutor:
    """
    Parallel check execution engine.

    Args:
        adapter: Adapter instance (e.g. JetsonAdapter, AscendAdapter)
        parallel_level: 0=serial, 1=category parallel, 2=DAG (default 2)
        max_workers: Max threads for Level 1 (default 8)
        early_exit: Stop on first CRITICAL failure (default True)
        progress_callback: Optional callback(check_id, status) for UI updates
    """

    def __init__(
        self,
        adapter: Any,
        parallel_level: int = 2,
        max_workers: int = 8,
        early_exit: bool = True,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.adapter = adapter
        self.parallel_level = ParallelLevel(parallel_level)
        self.max_workers = max_workers
        self.early_exit = early_exit
        self.progress_callback = progress_callback or (lambda cid, s: None)

        self.summary: Optional[CheckSummary] = None
        self.timings: Dict[str, CheckTiming] = {}
        self._cancel_flag = False
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

        # These are set in run_all()
        self._checks: List[Check] = []
        self._check_instances: Dict[str, Check] = {}
        self._dag: Optional[DependencyGraph] = None  # Built after checks are instantiated

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_all(self) -> CheckSummary:
        """Run all registered checks and return a summary."""
        check_classes = get_all_checks()
        # Instantiate check classes (get_all_checks returns classes)
        self._checks = []
        self._check_instances = {}
        for cls in check_classes:
            try:
                inst = cls()
                self._checks.append(inst)
                self._check_instances[inst.check_id] = inst
            except Exception:
                pass  # Skip checks that fail to instantiate


        if self.parallel_level == ParallelLevel.SERIAL:
            return self._run_serial()
        elif self.parallel_level == ParallelLevel.CATEGORY:
            return self._run_category_parallel()
        else:
            return self._run_dag()

    def cancel(self):
        """Request cancellation of running checks."""
        self._cancel_flag = True

    def get_timings(self) -> Dict[str, CheckTiming]:
        """Return timing data for all checks."""
        return self.timings

    # ------------------------------------------------------------------
    # Level 0: Serial
    # ------------------------------------------------------------------

    def _run_serial(self) -> CheckSummary:
        """Run all checks strictly serially — no parallelism at all."""
        summary = CheckSummary()
        self.timings = {}

        for inst in self._checks:
            if self._cancel_flag:
                break

            self.progress_callback(inst.check_id, "running")
            timing = CheckTiming(check_id=inst.check_id)
            timing.mark_start()

            try:
                result = self._safe_run(inst)
            except Exception as e:
                result = self._error_result(inst, str(e))

            timing.mark_done(result=result)
            self.timings[inst.check_id] = timing
            summary.add_result(result)
            self.progress_callback(inst.check_id, "done")

            if self.early_exit and result.severity == CheckSeverity.CRITICAL and not result.passed:
                # Still collect remaining checks but don't run them
                for remaining in self._checks[self._checks.index(inst) + 1:]:
                    self._skip_check(remaining, summary, "skipped_early_critical")
                break

        summary.calculate_score()
        self.summary = summary
        return summary

    # ------------------------------------------------------------------
    # Level 1: Category parallel
    # ------------------------------------------------------------------

    def _run_category_parallel(self) -> CheckSummary:
        """
        Run checks in parallel by category.
        Each category runs as a separate thread group.
        Checks within a category run serially (avoids state conflicts).
        """
        summary = CheckSummary()
        self.timings = {}

        # Group checks by category
        by_category: Dict[CheckCategory, List[Check]] = defaultdict(list)
        for inst in self._checks:
            by_category[inst.category].append(inst)

        # Collect results from all threads
        results_lock = threading.Lock()
        all_results: List[CheckResult] = []
        critical_hit = threading.Event()

        def run_category(category: CheckCategory, checks: List[Check]):
            for inst in checks:
                if self._cancel_flag or critical_hit.is_set():
                    break

                self.progress_callback(inst.check_id, "running")
                timing = CheckTiming(check_id=inst.check_id)
                timing.mark_start()

                try:
                    result = self._safe_run(inst)
                except Exception as e:
                    result = self._error_result(inst, str(e))

                timing.mark_done(result=result)
                with results_lock:
                    self.timings[inst.check_id] = timing
                    all_results.append(result)
                    self.progress_callback(inst.check_id, "done")

                    if self.early_exit and result.severity == CheckSeverity.CRITICAL and not result.passed:
                        critical_hit.set()

        threads = []
        for category, checks in by_category.items():
            t = threading.Thread(
                target=run_category,
                args=(category, checks),
                name=f"category-{category.value}",
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for result in all_results:
            summary.add_result(result)

        summary.calculate_score()
        self.summary = summary
        return summary

    # ------------------------------------------------------------------
    # Level 2: Full DAG
    # ------------------------------------------------------------------

    def _run_dag(self) -> CheckSummary:
        """Run checks respecting the dependency DAG. Parallel where possible."""
        summary = CheckSummary()
        self.timings = {}

        # Build DAG now (after checks are instantiated in run_all)
        if self._dag is None:
            self._dag = DependencyGraph(self._checks)

        levels = self._dag.topological_sort()
        completed: Set[str] = set()
        critical_hit = threading.Event()

        for batch_idx, batch in enumerate(levels):
            if self._cancel_flag or critical_hit.is_set():
                # Cancel remaining batches
                for cid in batch:
                    self._skip_check(self._check_instances[cid], summary, "skipped_cancelled")
                for remaining_batch in levels[batch_idx + 1:]:
                    for cid in remaining_batch:
                        self._skip_check(self._check_instances[cid], summary, "skipped_cancelled")
                break

            # Submit all checks in this batch in parallel
            futures = {}
            for check_id in batch:
                inst = self._check_instances[check_id]
                self.progress_callback(check_id, "running")
                timing = CheckTiming(check_id=check_id)
                timing.mark_start()
                self.timings[check_id] = timing

                future = self._executor.submit(self._safe_run, inst)
                futures[future] = check_id

            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                check_id = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = self._error_result(
                        self._check_instances[check_id], str(e)
                    )

                self.timings[check_id].mark_done(result=result)
                completed.add(check_id)
                summary.add_result(result)
                self.progress_callback(check_id, "done")

                if self.early_exit and result.severity == CheckSeverity.CRITICAL and not result.passed:
                    critical_hit.set()

        summary.calculate_score()
        self.summary = summary
        return summary

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_run(self, inst: Check) -> CheckResult:
        """Run a check with timeout protection (no nested thread-pool submit)"""
        meta = self.meta_map.get(inst.check_id) if self._dag else None
        timeout = meta.timeout if meta else 30.0

        if timeout > 0:
            return self._run_with_timeout(inst, timeout)
        return inst.run()

    def _run_with_timeout(self, inst: Check, timeout: float) -> CheckResult:
        """Run a check with a timeout using a dedicated thread (avoids thread-pool deadlock)"""
        result_holder: list = [None]
        exc_holder: list = [None]

        def _target():
            try:
                result_holder[0] = inst.run()
            except Exception as e:
                exc_holder[0] = e

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            # Timed out — thread is still running (daemon, will be cleaned up on exit)
            return CheckResult(
                check_id=inst.check_id,
                category=inst.category,
                severity=CheckSeverity.CRITICAL,
                passed=False,
                title=inst.title,
                current=f"Timeout after {timeout}s",
                expected="Completed within timeout",
                message=f"Check '{inst.title}' timed out after {timeout}s",
                details={"timeout": timeout},
            )

        if exc_holder[0] is not None:
            raise exc_holder[0]

        return result_holder[0]

    def _skip_check(self, inst: Check, summary: CheckSummary, reason: str):
        """Add a skipped result when early-exit or cancellation happens"""
        result = CheckResult(
            check_id=inst.check_id,
            category=inst.category,
            severity=CheckSeverity.INFO,
            passed=True,
            title=inst.title,
            current="skipped",
            expected="not_run",
            message=f"Skipped: {reason}",
            details={"skip_reason": reason},
        )
        summary.add_result(result)
        if inst.check_id not in self.timings:
            self.timings[inst.check_id] = CheckTiming(check_id=inst.check_id)

    def _error_result(self, inst: Check, error: str) -> CheckResult:
        """Wrap an exception as a failed CheckResult"""
        return CheckResult(
            check_id=inst.check_id,
            category=inst.category,
            severity=CheckSeverity.WARNING,
            passed=False,
            title=inst.title,
            current="error",
            expected="check_completed",
            message=f"Check raised exception: {error}",
            details={"exception": error},
        )

    @property
    def meta_map(self) -> Dict[str, CheckMeta]:
        """Lazily build meta_map from current checks"""
        if not hasattr(self, "_meta_map") or self._meta_map is None:
            self._meta_map: Dict[str, CheckMeta] = {}
            for inst in self._checks:
                self._meta_map[inst.check_id] = CheckMeta.from_check_instance(inst)
        return self._meta_map

    def __del__(self):
        """Clean up thread pool on destruction"""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def run_checks_parallel(
    adapter: Any,
    parallel_level: int = 2,
    max_workers: int = 8,
    early_exit: bool = True,
) -> CheckSummary:
    """
    One-shot parallel check runner.

    Example:
        from core.executor import run_checks_parallel
        from adapters.jetson.common import JetsonAdapter

        adapter = JetsonAdapter("Orin-AGX-64G")
        summary = run_checks_parallel(adapter, parallel_level=2)
        print(f"Health score: {summary.score}")
    """
    executor = CheckExecutor(
        adapter=adapter,
        parallel_level=parallel_level,
        max_workers=max_workers,
        early_exit=early_exit,
    )
    return executor.run_all()
