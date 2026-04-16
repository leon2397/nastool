#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test AI checks on Jetson"""
import sys
sys.path.insert(0, '/home/nvidia/nastool')

from checks.registry import _CHECKS
print(f"Total checks: {len(_CHECKS)}")

# List AI checks
ai_checks = [k for k, v in _CHECKS.items() if getattr(v, 'category', None) and 'ai' in str(getattr(v, 'category', '').value if hasattr(getattr(v, 'category', ''), 'value') else getattr(v, 'category', '')).lower()]
print(f"AI checks: {len(ai_checks)}")
for c in ai_checks[:10]:
    print(f"  - {c}")

# Test gpu_detected
try:
    from checks.ai.gpu_detected import check as gpu_check
    r = gpu_check()
    print(f"\ngpu_detected result:")
    print(f"  passed: {r.passed}")
    print(f"  message: {r.message}")
except Exception as e:
    print(f"ERROR gpu_detected: {e}")