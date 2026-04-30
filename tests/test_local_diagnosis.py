#!/usr/bin/env python3
# 本地诊断测试脚本 - Round 3 测试用

import sys
import os
import time

# 添加模块路径
base_path = os.path.dirname(os.path.dirname(__file__))
adapters_path = os.path.join(base_path, 'nastool-adapters')
core_path = os.path.join(base_path, 'nastool-core')
common_path = os.path.join(base_path, 'nastool-common')
sys.path.insert(0, adapters_path)
sys.path.insert(0, core_path)
sys.path.insert(0, common_path)
print(f"添加模块路径: {adapters_path}")
print(f"添加核心模块路径: {core_path}")
print(f"添加公共模块路径: {common_path}")

try:
    from nastool_core import run_checks_parallel, CHECK_TIMEOUTS
    from nastool_core.checks import list_checks
    print("导入模块成功")
except Exception as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)

def test_local_diagnosis(full_mode=False):
    print(f"\n=== 本地诊断测试 {'- 完整模式' if full_mode else ''} ===")
    
    # 获取检测项列表
    check_ids = list_checks()
    print(f"检测项数量: {len(check_ids)}")
    
    if not full_mode:
        # 快速模式：排除耗时检测
        slow_checks = {'benchmark_cpu', 'benchmark_disk', 'benchmark_memory'}
        check_ids = [c for c in check_ids if c not in slow_checks]
        print(f"快速模式 - 排除耗时检测后: {len(check_ids)} 项")
    
    # 执行检测
    start_time = time.time()
    print("\n开始执行检测...")
    
    try:
        results = run_checks_parallel(
            check_ids,
            max_concurrent=10,
            timeouts=CHECK_TIMEOUTS
        )
        elapsed = time.time() - start_time
        
        # 统计结果
        total = len(results)
        passed = sum(1 for r in results if r.get("result") and getattr(r["result"], 'passed', False))
        failed = total - passed
        
        print(f"\n=== 测试结果 ===")
        print(f"总检测项: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"耗时: {elapsed:.2f} 秒")
        
        # 显示失败的检测项
        if failed > 0:
            print("\n失败的检测项:")
            for r in results:
                result = r.get("result")
                if result and not getattr(result, 'passed', True):
                    check_id = r.get("check_id", "unknown")
                    severity = getattr(getattr(result, 'severity', None), 'value', 'unknown')
                    print(f"  - [{severity}] {check_id}: {getattr(result, 'summary', '')}")
        
        return {"total": total, "passed": passed, "failed": failed, "elapsed": elapsed}
        
    except Exception as e:
        print(f"执行检测时出错: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    # 解析参数
    full_mode = len(sys.argv) > 1 and sys.argv[1] == "--full"
    
    # 运行测试
    result = test_local_diagnosis(full_mode)
    
    # 设置退出码
    if "error" in result:
        sys.exit(1)
    elif result["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)