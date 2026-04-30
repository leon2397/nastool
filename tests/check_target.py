# -*- coding: utf-8 -*-
"""Check jetpack and SSL results on Jetson"""
import sys
sys.path.insert(0, '/home/nvidia/nastool-v4.0.0')

from nastool_core.checks import run_all_checks

s = run_all_checks()
print(f"Score: {s.score}/100")
print()
for r in s.results:
    if r.check_id in ('jetpack_version', 'ssl_cert_days'):
        sev = r.severity.value if hasattr(r.severity, 'value') else r.severity
        print(f"[{r.check_id}] sev={sev} passed={r.passed}")
        print(f"  message: {r.message}")
        print(f"  current: {r.current}")
        print()
