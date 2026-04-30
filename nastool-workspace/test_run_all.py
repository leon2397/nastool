#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/nvidia/nastool-v4.0.0/nastool-core')

try:
    from nastool_core.checks import run_all_checks
    print("run_all_checks imported successfully")
    summary = run_all_checks(full_mode=True)
    print(f"run_all_checks succeeded, {len(summary.results)} results")
except Exception as e:
    print(f"run_all_checks failed: {e}")
    import traceback
    traceback.print_exc()
