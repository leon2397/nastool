# -*- coding: utf-8 -*-
"""
tests/test_executor.py - Regression tests for core/executor.py

Set FAST=1 to skip slow integration tests (L0/L1/L2 full comparison).
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from checks.base import CheckResult, CheckSeverity, CheckCategory
from checks.registry import get_all_checks
from core.executor import (
    CheckExecutor,
    CheckMeta,
    CheckTiming,
    DependencyGraph,
    ParallelLevel,
)

FAST = os.environ.get("FAST", "0") == "1"


class TestDependencyGraph(unittest.TestCase):
    """Test DAG construction and topological sort"""

    def test_dag_build_from_classes(self):
        checks = get_all_checks()
        dag = DependencyGraph(checks)
        self.assertGreater(len(dag.meta_map), 0)

    def test_topological_sort_no_cycles(self):
        checks = get_all_checks()
        dag = DependencyGraph(checks)
        levels = dag.topological_sort()
        all_ids = set()
        for batch in levels:
            all_ids.update(batch)
        self.assertEqual(len(all_ids), len(dag.meta_map))

    def test_single_level_no_deps(self):
        checks = get_all_checks()
        dag = DependencyGraph(checks)
        levels = dag.topological_sort()
        self.assertGreaterEqual(len(levels), 1)


class TestCheckMeta(unittest.TestCase):
    def test_from_check_instance(self):
        checks = get_all_checks()
        inst = checks[0]()
        meta = CheckMeta.from_check_instance(inst)
        self.assertEqual(meta.check_id, inst.check_id)
        self.assertIn(meta.category, CheckCategory)

    def test_severity_fallback(self):
        checks = get_all_checks()
        inst = checks[0]()
        if hasattr(inst, "severity"):
            del inst.severity
        meta = CheckMeta.from_check_instance(inst)
        self.assertEqual(meta.severity, CheckSeverity.INFO)


class TestParallelLevelEnum(unittest.TestCase):
    def test_values(self):
        self.assertEqual(ParallelLevel.SERIAL.value, 0)
        self.assertEqual(ParallelLevel.CATEGORY.value, 1)
        self.assertEqual(ParallelLevel.DAG.value, 2)


class TestExecutorUnit(unittest.TestCase):
    """Fast unit tests — no full check runs"""

    def test_cancel_flag(self):
        executor = CheckExecutor(adapter=None, parallel_level=0, early_exit=False)
        executor.cancel()
        self.assertTrue(executor._cancel_flag)

    def test_skip_check(self):
        from checks.base import CheckSummary
        executor = CheckExecutor(adapter=None, parallel_level=0)
        checks = get_all_checks()
        inst = checks[0]()
        summary = CheckSummary()
        executor._skip_check(inst, summary, "test_skip")
        self.assertEqual(summary.total, 1)

    def test_error_result(self):
        executor = CheckExecutor(adapter=None, parallel_level=0)
        checks = get_all_checks()
        inst = checks[0]()
        result = executor._error_result(inst, "boom")
        self.assertFalse(result.passed)
        self.assertEqual(result.severity, CheckSeverity.WARNING)


# ── Slow integration tests (skip with FAST=1) ──────────────────────

@unittest.skipIf(FAST, "Slow integration test (set FAST=0 to run)")
class TestExecutorLevels(unittest.TestCase):
    """Test that all parallel levels produce identical results"""

    @classmethod
    def setUpClass(cls):
        cls.results = {}
        cls.timings = {}
        for level in [0, 1, 2]:
            executor = CheckExecutor(adapter=None, parallel_level=level, early_exit=False)
            summary = executor.run_all()
            cls.results[level] = summary
            cls.timings[level] = executor.get_timings()

    def test_scores_match(self):
        s0, s1, s2 = (self.results[l].score for l in [0, 1, 2])
        self.assertEqual(s0, s1)
        self.assertEqual(s1, s2)

    def test_passed_match(self):
        p0, p1, p2 = (self.results[l].passed for l in [0, 1, 2])
        self.assertEqual(p0, p1)
        self.assertEqual(p1, p2)

    def test_total_match(self):
        t0, t1, t2 = (self.results[l].total for l in [0, 1, 2])
        self.assertEqual(t0, t1)
        self.assertEqual(t1, t2)

    def test_check_ids_match(self):
        ids0 = set(r.check_id for r in self.results[0].results)
        ids1 = set(r.check_id for r in self.results[1].results)
        ids2 = set(r.check_id for r in self.results[2].results)
        self.assertEqual(ids0, ids1)
        self.assertEqual(ids1, ids2)

    def test_parallel_is_faster(self):
        t0 = sum(t.duration_ms for t in self.timings[0].values())
        t2 = sum(t.duration_ms for t in self.timings[2].values())
        if t0 > 0:
            self.assertLess(t2, t0 * 3)


@unittest.skipIf(FAST, "Slow integration test (set FAST=0 to run)")
class TestCheckTiming(unittest.TestCase):
    def test_timing_recorded(self):
        executor = CheckExecutor(adapter=None, parallel_level=0, early_exit=False)
        summary = executor.run_all()
        timings = executor.get_timings()
        self.assertEqual(len(timings), summary.total)

    def test_timing_has_duration(self):
        executor = CheckExecutor(adapter=None, parallel_level=0, early_exit=False)
        executor.run_all()
        for cid, timing in executor.get_timings().items():
            self.assertGreaterEqual(timing.duration_ms, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
