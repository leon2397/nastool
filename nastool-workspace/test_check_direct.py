#!/usr/bin/env python3
from nastool_core.checks.system import python_version as pv

check = pv.PythonVersionCheck()
result = check.run()
print("Direct call result:")
print(f"  current: {result.current}")
print(f"  message: {result.message}")
