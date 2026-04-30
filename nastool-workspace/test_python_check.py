#!/usr/bin/env python3
import nastool_core.checks.system.python_version as pv

check = pv.PythonVersionCheck()
result = check.run()
print(f"check_id: {result.check_id}")
print(f"current: {result.current}")
print(f"expected: {result.expected}")
print(f"message: {result.message}")
