# -*- coding: utf-8 -*-
import shutil, os, sys, importlib

NASTOOL = r"C:\tools415\nastool"
DATA_INIT = os.path.join(NASTOOL, "data", "__init__.py")
MOCK_DATA = os.path.join(NASTOOL, "data", "mock_results.py")
MOCK_ROOT = os.path.join(NASTOOL, "mock_results.py")

# Step 1: Copy mock_results.py into data/
shutil.copy2(MOCK_ROOT, MOCK_DATA)
print(f"Copied mock_results.py -> data/: {os.path.exists(MOCK_DATA)}")

# Step 2: Simplify data/__init__.py
init_content = """# data/__init__.py
# Device profile data module
# Re-exports ProfileManager for backward compatibility
try:
    from data.mock_results import ProfileManager
except ImportError:
    ProfileManager = None
"""
with open(DATA_INIT, "w", encoding="utf-8") as f:
    f.write(init_content)
print(f"Updated __init__.py: {os.path.getsize(DATA_INIT)} bytes")

# Step 3: Update arm_diagnose.py import path (data.mock_results -> mock_results)
ARM_DIAG = os.path.join(NASTOOL, "arm_diagnose.py")
with open(ARM_DIAG, encoding="utf-8") as f:
    content = f.read()
if "from data.mock_results import" in content:
    content = content.replace(
        "from data.mock_results import PROFILE_DESCRIPTIONS",
        "from mock_results import PROFILE_DESCRIPTIONS"
    )
    with open(ARM_DIAG, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated arm_diagnose.py import path")
else:
    print("arm_diagnose.py already updated")

# Step 4: Update checks/__init__.py import path
CHECKS_INIT = os.path.join(NASTOOL, "checks", "__init__.py")
with open(CHECKS_INIT, encoding="utf-8") as f:
    content = f.read()
if "from data.mock_results import" in content:
    content = content.replace(
        "from data.mock_results import get_mock_result, PROFILES, PROFILE_DESCRIPTIONS",
        "from mock_results import get_mock_result, PROFILES, PROFILE_DESCRIPTIONS"
    )
    with open(CHECKS_INIT, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated checks/__init__.py import path")
else:
    print("checks/__init__.py already updated")

# Step 5: Test
sys.path.insert(0, os.path.dirname(NASTOOL))
sys.path.insert(0, NASTOOL)

# Reload data
if "data" in sys.modules:
    del sys.modules["data"]
if "data.mock_results" in sys.modules:
    del sys.modules["data.mock_results"]

import data
print(f"data.ProfileManager: {data.ProfileManager}")

from arm_diagnose import main
print("arm_diagnose import OK")

# Test mock
from checks import run_mock_checks
s = run_mock_checks("healthy")
print(f"Mock healthy: {s.total} checks, score={s.score}")
