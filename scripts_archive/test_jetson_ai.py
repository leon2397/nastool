#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test AI checks on Jetson - detailed version"""
import sys
sys.path.insert(0, '/home/nvidia/nastool')

print("=" * 60)
print("Jetson AI Checks Test")
print("=" * 60)

# Test CUDA
try:
    from checks.ai.cuda_version import CudaVersionCheck
    c = CudaVersionCheck()
    r = c.run()
    print(f"\n[CUDA Version Check]")
    print(f"  passed: {r.passed}")
    print(f"  message: {r.message}")
    print(f"  current: {getattr(r, 'current', 'N/A')}")
except Exception as e:
    print(f"\n[CUDA Version Check] ERROR: {e}")

# Test JetPack
try:
    from checks.ai.jetpack_version import JetPackVersionCheck
    c = JetPackVersionCheck()
    r = c.run()
    print(f"\n[JetPack Version Check]")
    print(f"  passed: {r.passed}")
    print(f"  message: {r.message}")
except Exception as e:
    print(f"\n[JetPack Version Check] ERROR: {e}")

# Test TensorRT
try:
    from checks.ai.tensorrt_version import TensorRTVersionCheck
    c = TensorRTVersionCheck()
    r = c.run()
    print(f"\n[TensorRT Version Check]")
    print(f"  passed: {r.passed}")
    print(f"  message: {r.message}")
except Exception as e:
    print(f"\n[TensorRT Version Check] ERROR: {e}")

# Test GPU Detected
try:
    from checks.ai.gpu_detected import GPUDetectedCheck
    c = GPUDetectedCheck()
    r = c.run()
    print(f"\n[GPU Detected Check]")
    print(f"  passed: {r.passed}")
    print(f"  message: {r.message}")
except Exception as e:
    print(f"\n[GPU Detected Check] ERROR: {e}")

print("\n" + "=" * 60)
print("Test Complete")