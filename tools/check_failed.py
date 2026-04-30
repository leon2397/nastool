#!/usr/bin/env python3
"""检查失败的检测器"""
from unified_checker_executor import UnifiedCheckerExecutor

executor = UnifiedCheckerExecutor()
failed = [c for c in executor.checkers if not c['available']]

print('失败的检测器:')
for f in failed:
    print(f"  {f['id']}: {f['module_info']}")
