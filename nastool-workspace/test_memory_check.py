#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/nvidia/nastool-v4.0.0/nastool-core')

from nastool_core.checks.system.memory_check import memory_check
from nastool_core.checks.base import CheckContext

class DummyContext:
    def passed(self, **kwargs):
        print("passed:", kwargs)
        return kwargs
    
    def failed(self, **kwargs):
        print("failed:", kwargs)
        return kwargs

ctx = DummyContext()
result = memory_check(ctx)
print("Result:", result)
