# -*- coding: utf-8 -*-
"""Score test on Jetson"""
import sys
sys.path.insert(0, '/home/nvidia/nastool-v4.0.0')

from nastool_core.checks import run_all_checks

try:
    s = run_all_checks()
    print(f"score={s.score} passed={s.passed} warnings={s.warnings} critical={s.critical}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
