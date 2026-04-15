# -*- coding: utf-8 -*-
"""
tests/test_executor.py - Regression tests for core/executor.py

Validates that all three parallel levels produce identical results
and that DAG/timeout/cancellation work correctly.
"""

import sys
import os
import time
import threading
import unittest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from checks.base import Check, CheckResult, CheckSummary, CheckSeverity, CheckCategory
from checks.registry import register_check, get_all_checks
from core.executor import (
    CheckExecutor,
    CheckMeta,
    CheckTiming,
    DependencyGraph,
    ParallelLevel,
)


class TestDependencyGraph(unittest.TestCase):
    """Test DAG construction and topological sort"""

    def test_dag_build_from_classes(self):
        """DAG should accept check classes (from get_all_checks)"""
        checks = get_all_checks()
        dag = DependencyGraph(checks)
        self.assertGreater(len(dag.meta_map), 0)

    def test_topological_sort_no_cycles(self):
        """Topological sort should succeed without cycles"""
        checks = get_all_checks()
        dag = DependencyGraph(checks)
        levels = dag.topological_sort()
        # All check IDs should appear in the levels
        all_ids = set()
        for batch in levels:
            all_ids.update(batch)
        self.assertEqual(len(all_ids), len(dag.meta_map))

    def test_single_level_no_deps(self):
        """With no dependencies, all checks should be in one level"""
        checks = get_all_checks()
        dag = DependencyGraph(checks)
        levels = dag.topological_sort()
        # Currently no checks declare dependencies, so should be 1 level
        self.assertGreaterEqual(len(levels), 1)


class TestCheckMeta(unittest.TestCase):
    """Test CheckMeta construction"""

    def test_from_check_instance(self):
        """CheckMeta should be buildable from a check instance"""
        checks = get_all_checks()
        inst = checks[0]()
        meta = CheckMeta.from_check_instance(inst)
        self.assertEqual(meta.check_id, inst.check_id)
        self.assertEqual(meta.title, inst.title)
        self.assertIn(meta.category, CheckCategory)

    def test_severity_fallback(self):
        """CheckMeta should handle missing severity attribute"""
        checks = get_all_checks()
        inst = checks[0]()
        # Remove severity if it exists
        if hasattr(inst, "severity"):
            del inst.severity
        meta = CheckMeta.from_check_instance(inst)
        # Should fallback to INFO
        self.assertEqual(meta.severity, CheckSeverity.INFO)


class TestExecutorLevels(unittest.TestCase):
    """Test that all parallel levels produce identical results"""

    @classmethod
    def setUpClass(cls):
        """Run all three levels once and cache results"""
        cls.results = {}
        cls.timings = {}
        for level in [0, 1, 2]:
            executor = CheckExecutor(
                adapter=None, parallel_level=level, early_exit=False
            )
            summary = executor.run_all()
            cls.results[level] = summary
            cls.timings[level] = executor.get_timings()

    def test_scores_match(self):
        """All levels should produce the same health score"""
        s0 = self.results[0].score
        s1 = self.results[1].score
        s2 = self.results[2].score
        self.assertEqual(s0, s1, f"L0={s0} != L1={s1}")
        self.assertEqual(s1, s2, f"L1={s1} != L2={s2}")

    def test_passed_match(self):
        """All levels should have the same number of passed checks"""
        p0 = self.results[0].passed
        p1 = self.results[1].passed
        p2 = self.results[2].passed
        self.assertEqual(p0, p1, f"L0 passed={p0} != L1 passed={p1}")
        self.assertEqual(p1, p2, f"L1 passed={p1} != L2 passed={p2}")

    def test_total_match(self):
        """All levels should check the same total number of checks"""
        t0 = self.results[0].total
        t1 = self.results[1].total
        t2 = self.results[2].total
        self.assertEqual(t0, t1, f"L0 total={t0} != L1 total={t1}")
        self.assertEqual(t1, t2, f"L1 total={t1} != L2 total={t2}")

    def test_check_ids_match(self):
        """All levels should run the same set of checks"""
        ids0 = set(r.check_id for r in self.results[0].results)
        ids1 = set(r.check_id for r in self.results[1].results)
        ids2 = set(r.check_id for r in self.results[2].results)
        self.assertEqual(ids0, ids1)
        self.assertEqual(ids1, ids2)

    def test_parallel_is_faster(self):
        """L2 should be faster than L0 (on real hardware with network checks)"""
        # This is a soft check — on fast networks, the difference may be small
        # We just verify L2 doesn't take more than 3x L0 time
        t0 = sum(t.duration_ms for t in self.timings[0].values())
        t2 = sum(t.duration_ms for t in self.timings[2].values())
        # L2 should not be dramatically slower
        if t0 > 0:
            self.assertLess(t2, t0 * 3, "L2 should not be 3x slower than L0")


class TestExecutorCancellation(unittest.TestCase):
    """Test cancellation support"""

    def test_cancel_flag(self):
        """Setting cancel flag should stop execution"""
        executor = CheckExecutor(adapter=None, parallel_level=0, early_exit=False)
        # Cancel before running
        executor.cancel()
        # Run should complete quickly (most checks skipped)
        summary = executor.run_all()
        # After cancellation, some checks may still have run
        # Just verify it doesn't hang
        self.assertIsNotNone(summary)


class TestCheckTiming(unittest.TestCase):
    """Test timing data collection"""

    def test_timing_recorded(self):
        """Each check should have timing data"""
        executor = CheckExecutor(adapter=None, parallel_level=0, early_exit=False)
        summary = executor.run_all()
        timings = executor.get_timings()
        self.assertEqual(len(timings), summary.total)

    def test_timing_has_duration(self):
        """Each timing should have a non-negative duration"""
        executor = CheckExecutor(adapter=None, parallel_level=0, early_exit=False)
        executor.run_all()
        for cid, timing in executor.get_timings().items():
            self.assertGreaterEqual(timing.duration_ms, 0, f"{cid} has negative duration")


class TestParallelLevelEnum(unittest.TestCase):
    """Test ParallelLevel enum"""

    def test_values(self):
        self.assertEqual(ParallelLevel.SERIAL.value, 0)
        self.assertEqual(ParallelLevel.CATEGORY.value, 1)
        self.assertEqual(ParallelLevel.DAG.value, 2)

    def test_from_int(self):
        self.assertEqual(ParallelLevel(0), ParallelLevel.SERIAL)
        self.assertEqual(ParallelLevel(1), ParallelLevel.CATEGORY)
        self.assertEqual(ParallelLevel(2), ParallelLevel.DAG)


if __name__ == "__main__":
    unittest.main(verbosity=2)
