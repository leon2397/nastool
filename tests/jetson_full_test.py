#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在设备上运行完整诊断"""
import sys
import os


def setup_python_path():
    """设置Python路径"""
    # 尝试不同的路径
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "nastool-v4.0.0"),
        "/home/nvidia/nastool-v4.0.0",
        "/opt/nastool-v4.0.0",
        os.path.join(os.path.expanduser("~"), "nastool-v4.0.0")
    ]
    
    for path in possible_paths:
        if os.path.exists(os.path.join(path, "nastool_core")):
            sys.path.insert(0, path)
            print(f"设置 Python 路径: {path}")
            return True
    
    print("警告: 未找到 nastool-v4.0.0 目录")
    return False

def run_full_diagnosis():
    """运行完整诊断"""
    try:
        from nastool_core.checks import run_all_checks
        from nastool_core.checks.base import CheckSeverity
        
        print("运行完整诊断...")
        s = run_all_checks()
        
        print(f"=== NASTool v4.0.0 完整诊断 ===")
        print(f"评分: {s.score}/100")
        print(f"通过: {s.passed}, 警告: {s.warnings}, 严重: {s.critical}")
        
        # 显示严重问题
        print("\n--- 严重问题 ---")
        critical_found = False
        for r in s.results:
            sev_str = r.severity.value if hasattr(r.severity, 'value') else r.severity
            if sev_str in ('critical', 'CRITICAL'):
                critical_found = True
                print(f"  [{r.check_id}] {r.title}: {r.message}")
        
        if not critical_found:
            print("  无严重问题")
        
        # 显示警告
        print("\n--- 警告 ---")
        warning_found = False
        for r in s.results:
            sev_str = r.severity.value if hasattr(r.severity, 'value') else r.severity
            if sev_str in ('warning', 'WARNING'):
                warning_found = True
                print(f"  [{r.check_id}] {r.title}: {r.message}")
        
        if not warning_found:
            print("  无警告")
        
        # 按类别显示
        print("\n--- 按类别统计 ---")
        from collections import defaultdict
        by_cat = defaultdict(lambda: [0, 0, 0])
        
        for r in s.results:
            cat = r.category.value if hasattr(r.category, 'value') else r.category
            if r.passed:
                by_cat[cat][0] += 1
            else:
                sev_str = r.severity.value if hasattr(r.severity, 'value') else r.severity
                if sev_str in ('critical', 'CRITICAL'):
                    by_cat[cat][2] += 1
                else:
                    by_cat[cat][1] += 1
        
        for cat, (ok, warn, crit) in sorted(by_cat.items()):
            print(f"  {cat}: {ok} 正常 / {warn} 警告 / {crit} 严重")
        
        return True
    except ImportError as e:
        print(f"导入模块失败: {e}")
        return False
    except Exception as e:
        print(f"执行诊断时出错: {e}")
        return False

def main():
    """主函数"""
    print("=== 完整诊断测试 ===")
    
    # 设置 Python 路径
    if setup_python_path():
        # 运行完整诊断
        run_full_diagnosis()
    else:
        print("无法运行诊断 (无法找到模块)")


if __name__ == "__main__":
    main()
