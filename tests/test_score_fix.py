#!/usr/bin/env python3
"""Run real diagnosis on Jetson and print results."""
import sys, os
os.chdir('/home/nvidia/nastool-v4.0.0')
sys.path.insert(0, '/home/nvidia/nastool-v4.0.0')

import importlib
# Reload the modules to pick up changes
for mod in list(sys.modules.keys()):
    if mod.startswith('nastool_'):
        del sys.modules[mod]

from nastool_core.checks import run_all_checks

print("Running real diagnosis (v4.0.1 patched)...", flush=True)
summary = run_all_checks(full_mode=True)

# Print score (this is what we fixed)
report = summary.get_health_report()
print(f"\n=== SCORE TEST ===", flush=True)
print(f"Score: {report.overall_score}", flush=True)
print(f"Grade: {report.grade()}", flush=True)
print(f"Level: {report.level_name}", flush=True)
print(f"Passed: {report.total_passed}/{report.total_checks}", flush=True)
print(f"Warnings: {report.total_warnings}", flush=True)
print(f"Critical: {report.total_critical}", flush=True)
print(f"\nSummary.score: {summary.score}", flush=True)

# Show critical items
if report.critical_items:
    print(f"\n=== CRITICAL ({len(report.critical_items)}) ===", flush=True)
    for r in report.critical_items[:5]:
        print(f"  [{r.check_id}] {r.message}", flush=True)

if report.warnings_items:
    print(f"\n=== WARNINGS ({len(report.warnings_items)}) ===", flush=True)
    for r in report.warnings_items[:5]:
        print(f"  [{r.check_id}] {r.message}", flush=True)

# Test severity normalization
from nastool_core.checks.base import CheckSeverity
print(f"\n=== SEVERITY TEST ===", flush=True)
test_sev = "warning"
print(f"String 'warning' norm -> {test_sev.lower()}", flush=True)

# Direct score calculation test
from nastool_core.utils.health_scorer import HealthScorer, CheckSeverity as HS
scorer = HealthScorer()
for r in summary.results:
    scorer.add_result(r)
report2 = scorer.calculate()
print(f"\nDirect HealthScorer score: {report2.overall_score}", flush=True)
print(f"Grade: {report2.grade()}", flush=True)
