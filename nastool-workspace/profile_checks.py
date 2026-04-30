"""
profile_checks.py - NASTool 检测项性能分析（简化版）
"""

import time
import sys
sys.path.insert(0, r'C:\tools416\nastool-common')
sys.path.insert(0, r'C:\tools416\nastool-core')

from nastool_core.checks import list_checks, get_check

print("=" * 60)
print("NASTool v3.0 检测项性能分析")
print("=" * 60)

# 获取所有检测项
check_ids = list_checks()
print(f"\n总检测项: {len(check_ids)}")

# 记录每个检测项的执行时间
results = []

print("\n开始性能测试（每项运行1次）...")
print("-" * 60)

for i, check_id in enumerate(check_ids, 1):
    start = time.perf_counter()
    try:
        check_class = get_check(check_id)
        if check_class:
            check = check_class()
            result = check.run()
            category = result.category.value if hasattr(result, 'category') else 'UNKNOWN'
        else:
            category = 'UNKNOWN'
    except Exception as e:
        category = 'ERROR'
    end = time.perf_counter()
    
    elapsed = end - start
    results.append((check_id, elapsed, category))
    print(f"[{i:3d}/{len(check_ids)}] {check_id:40s} {elapsed*1000:8.2f} ms  [{category}]")

# 排序
results.sort(key=lambda x: x[1], reverse=True)

print("\n" + "=" * 60)
print("性能分析结果 - Top 20 最慢检测项")
print("=" * 60)
print(f"{'Rank':<6} {'Check ID':<40} {'Time(ms)':<12} {'Category':<10}")
print("-" * 60)

for rank, (check_id, elapsed, category) in enumerate(results[:20], 1):
    print(f"{rank:<6} {check_id:<40} {elapsed*1000:12.2f} {category:<10}")

# 统计
print("\n" + "=" * 60)
print("统计摘要")
print("=" * 60)
total_time = sum(r[1] for r in results)
print(f"总检测时间: {total_time:.2f} 秒")
print(f"平均单项: {total_time/len(results)*1000:.2f} ms")
print(f"Top 10 占比: {sum(r[1] for r in results[:10])/total_time*100:.1f}%")

# 分类统计
print("\n分类统计:")
category_times = {}
for check_id, elapsed, category in results:
    if category not in category_times:
        category_times[category] = []
    category_times[category].append(elapsed)

for category, times in sorted(category_times.items(), key=lambda x: sum(x[1]), reverse=True):
    total = sum(times)
    avg = total / len(times)
    print(f"  {category:<12} 总计: {total*1000:8.1f}ms  平均: {avg*1000:6.1f}ms  项数: {len(times)}")

# 优化建议
print("\n" + "=" * 60)
print("优化建议 - 建议并行化的检测项（>50ms）")
print("=" * 60)
for check_id, elapsed, category in results:
    if elapsed > 0.05:  # > 50ms
        print(f"  - {check_id:<40} {elapsed*1000:8.2f} ms  [{category}]")
