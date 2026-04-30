#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Jetson checks with correct module names"""
import sys
sys.path.insert(0, '/home/nvidia/nastool')

print("=" * 60)
print("Jetson Check Test - Correct Module Names")
print("=" * 60)

# Test uptime (should work)
try:
    from checks.system.uptime import UptimeCheck
    c = UptimeCheck()
    r = c.run()
    print(f"\n[uptime] passed={r.passed}")
    print(f"  message: {r.message[:80] if r.message else 'N/A'}")
except Exception as e:
    print(f"\n[uptime] ERROR: {e}")

# Test cpu_temp
try:
    from checks.system.cpu_temp import CpuTempCheck
    c = CpuTempCheck()
    r = c.run()
    print(f"\n[cpu_temp] passed={r.passed}")
    print(f"  message: {r.message[:80] if r.message else 'N/A'}")
except Exception as e:
    print(f"\n[cpu_temp] ERROR: {e}")

# Test memory_check
try:
    from checks.system.memory_check import MemoryCheck
    c = MemoryCheck()
    r = c.run()
    print(f"\n[memory_check] passed={r.passed}")
    print(f"  message: {r.message[:80] if r.message else 'N/A'}")
except Exception as e:
    print(f"\n[memory_check] ERROR: {e}")

# Test system_disk
try:
    from checks.system.system_disk import SystemDiskCheck
    c = SystemDiskCheck()
    r = c.run()
    print(f"\n[system_disk] passed={r.passed}")
    print(f"  message: {r.message[:80] if r.message else 'N/A'}")
except Exception as e:
    print(f"\n[system_disk] ERROR: {e}")

# Test kernel_version
try:
    from checks.system.kernel_version import KernelVersionCheck
    c = KernelVersionCheck()
    r = c.run()
    print(f"\n[kernel_version] passed={r.passed}")
    print(f"  message: {r.message[:80] if r.message else 'N/A'}")
except Exception as e:
    print(f"\n[kernel_version] ERROR: {e}")

# Test python_version
try:
    from checks.system.python_version import PythonVersionCheck
    c = PythonVersionCheck()
    r = c.run()
    print(f"\n[python_version] passed={r.passed}")
    print(f"  message: {r.message[:80] if r.message else 'N/A'}")
except Exception as e:
    print(f"\n[python_version] ERROR: {e}")

# Test storage_disk
try:
    from checks.storage.storage_disk import StorageDiskCheck
    c = StorageDiskCheck()
    r = c.run()
    print(f"\n[storage_disk] passed={r.passed}")
    print(f"  message: {r.message[:80] if r.message else 'N/A'}")
except Exception as e:
    print(f"\n[storage_disk] ERROR: {e}")

print("\n" + "=" * 60)
print("Test Complete")