# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"C:\tools416\nastool-common")
try:
    from nastool_common.utils.progress import ProgressTracker
    print("OK")
except ImportError as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
