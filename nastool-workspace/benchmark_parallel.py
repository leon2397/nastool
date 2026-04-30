"""
benchmark_parallel.py - 并行检测性能对比

对比顺序执行 vs 并行执行的性能差异。
"""

import time
import sys
sys.path.insert(0, r'C:\tools416\nastool-common')
sys.path.insert(0, r'C:\tools416\nastool-core')

from nastool_core import list_checks, run_check, run_checks_parallel, CHECK_TIMEOUTS

print("=" * 70)
print("NASTool v4.0 - 并行检测性能对比")
print("=" * 70)

# 获取所有检测项
check_ids = list_checks()
print(f"\n总检测项: {len(check_ids)}")

# 选择重点优化的检测项（慢检测）
slow_checks = [
    "network_latency", "latency_check", "internet_access",
    "triton_server", "torchserve", "tensorflow_serving",
    "nas_backend", "port_conflict", "pip_installed"
]

# 只测试存在的检测项
test_checks = [c for c in slow_checks if c in check_ids]
print(f"测试项: {len(test_checks)} 个慢检测")
print(f"  {', '.join(test_checks)}")

# 1. 顺序执行
print("\n" + "-" * 70)
print("1. 顺序执行")
print("-" * 70)

start = time.perf_counter()
sequential_results = []
for check_id in test_checks:
    t0 = time.perf_counter()
    try:
        result = run_check(check_id)
        status = "OK"
    except Exception as e:
        result = None
        status = f"ERROR: {e}"
    t1 = time.perf_counter()
    sequential_results.append({
        "check_id": check_id,
        "elapsed": t1 - t0,
        "status": status
    })
    print(f"  {check_id:30s} {(t1-t0)*1000:8.2f} ms  [{status}]")

sequential_total = time.perf_counter() - start
print(f"\n顺序执行总时间: {sequential_total:.2f} 秒")

# 2. 并行执行
print("\n" + "-" * 70)
print("2. 并行执行 (max_concurrent=5)")
print("-" * 70)

def progress(current, total):
    print(f"  进度: {current}/{total}", end="\r")

start = time.perf_counter()
parallel_results = run_checks_parallel(
    test_checks,
    max_concurrent=5,
    default_timeout=30.0,
    progress_callback=progress,
    timeouts=CHECK_TIMEOUTS
)
parallel_total = time.perf_counter() - start

print(f"\n并行执行总时间: {parallel_total:.2f} 秒")

# 显示详细结果
for r in parallel_results:
    status = "OK" if r["error"] is None else f"ERROR: {r['error'][:30]}"
    print(f"  {r['check_id']:30s} {r['elapsed']*1000:8.2f} ms  [{status}]")

# 3. 对比结果
print("\n" + "=" * 70)
print("性能对比结果")
print("=" * 70)
print(f"顺序执行: {sequential_total:.2f} 秒")
print(f"并行执行: {parallel_total:.2f} 秒")
print(f"速度提升: {sequential_total/parallel_total:.1f}x")
print(f"节省时间: {sequential_total - parallel_total:.2f} 秒 ({(1-parallel_total/sequential_total)*100:.1f}%)")

# 4. 全量检测对比（可选）
print("\n" + "=" * 70)
print("3. 全量检测并行测试（所有93项）")
print("=" * 70)
print("开始并行执行所有检测项...")

start = time.perf_counter()
all_results = run_checks_parallel(
    check_ids,
    max_concurrent=10,
    default_timeout=30.0,
    progress_callback=lambda c, t: print(f"  进度: {c}/{t}", end="\r"),
    timeouts=CHECK_TIMEOUTS
)
all_total = time.perf_counter() - start

print(f"\n全量并行执行: {all_total:.2f} 秒")
print(f"v3.0顺序执行: ~45 秒（预估）")
print(f"速度提升: {45/all_total:.1f}x")

# 统计失败/超时
errors = [r for r in all_results if r["error"]]
print(f"\n失败/超时: {len(errors)} 项")
for r in errors[:5]:
    print(f"  - {r['check_id']}: {r['error']}")
