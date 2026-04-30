"""
benchmark_batch_v4.py - 批量检测 v3 vs v4 性能对比
"""

import time
import sys
sys.path.insert(0, r'C:\tools416\nastool-common')
sys.path.insert(0, r'C:\tools416\nastool-core')
sys.path.insert(0, r'C:\tools416\nastool-cli')

print("=" * 70)
print("NASTool v4.0 - 批量检测性能对比 (v3 vs v4)")
print("=" * 70)

# 模拟设备列表（使用本地重复检测模拟多设备）
mock_devices = [f"device-{i:02d}" for i in range(1, 6)]  # 5个设备
print(f"\n模拟设备数: {len(mock_devices)}")
print(f"  {', '.join(mock_devices)}")

# 选择少量检测项进行测试（快速验证）
test_checks = [
    "python_version", "memory_check", "system_disk",
    "cpu_temperature", "system_uptime"
]

# v3 方式：顺序执行（模拟）
print("\n" + "-" * 70)
print("v3.0 方式：设备顺序 + 检测顺序")
print("-" * 70)

from nastool_core.checks import get_check

start = time.perf_counter()
v3_total = 0

for device_id in mock_devices:
    device_start = time.perf_counter()
    for check_id in test_checks:
        try:
            check_class = get_check(check_id)
            if check_class:
                check = check_class()
                check.run()
        except:
            pass
    device_elapsed = time.perf_counter() - device_start
    v3_total += device_elapsed
    print(f"  {device_id}: {device_elapsed*1000:.1f} ms")

v3_time = time.perf_counter() - start
print(f"\nv3.0 总时间: {v3_time:.2f} 秒")

# v4 方式：设备并行 + 检测并行
print("\n" + "-" * 70)
print("v4.0 方式：设备并行 + 检测并行")
print("-" * 70)

from nastool_core.batch_parallel import batch_diagnose_parallel

def on_device_done(result):
    status = "OK" if result.success else "FAIL"
    print(f"  {result.device_id}: {result.elapsed*1000:.1f} ms [{status}]")

start = time.perf_counter()
v4_results = batch_diagnose_parallel(
    device_ids=mock_devices,
    check_ids=test_checks,
    max_concurrent_devices=5,  # 5设备并行
    max_concurrent_checks_per_device=5,  # 5检测并行
    on_device_complete=on_device_done
)
v4_time = time.perf_counter() - start

print(f"\nv4.0 总时间: {v4_time:.2f} 秒")

# 对比结果
print("\n" + "=" * 70)
print("性能对比结果")
print("=" * 70)
print(f"v3.0 (顺序): {v3_time:.2f} 秒")
print(f"v4.0 (并行): {v4_time:.2f} 秒")

if v4_time > 0:
    speedup = v3_time / v4_time
    saving = (1 - v4_time/v3_time) * 100
    print(f"速度提升: {speedup:.1f}x")
    print(f"节省时间: {saving:.1f}%")
else:
    print("v4.0 时间过短，无法计算")

# 理论分析
print("\n" + "=" * 70)
print("理论分析")
print("=" * 70)
print(f"设备数: {len(mock_devices)}")
print(f"检测项/设备: {len(test_checks)}")
print(f"v3.0 方式: 设备串行 × 检测串行 = 顺序执行")
print(f"v4.0 方式: 设备并行(max={5}) × 检测并行(max={5}) = 最大25并行")
print(f"\n在真实多设备场景下，v4.0 提升更明显:")
print(f"  - 10设备 × 10并发 = 理论10x提升")
print(f"  - 网络延迟重叠，总时间接近最慢单设备")
