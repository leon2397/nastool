#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 jetpack_version 修复"""
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

def test_checks():
    """测试检查"""
    try:
        from nastool_core.checks import run_all_checks
        
        print("运行所有检查...")
        s = run_all_checks()
        
        print(f"评分: {s.score}/100")
        print(f"通过: {s.passed}, 警告: {s.warnings}, 严重: {s.critical}")
        
        # 检查特定项
        print("\n--- 特定检查项 ---")
        found_items = False
        for r in s.results:
            if r.check_id in ('jetpack_version', 'ssl_cert_days'):
                found_items = True
                sev = r.severity.value if hasattr(r.severity, 'value') else r.severity
                print(f"[{r.check_id}] sev={sev} passed={r.passed} current={r.current}")
                print(f"  message: {r.message}")
        
        if not found_items:
            print("未找到 jetpack_version 或 ssl_cert_days 检查项")
        
        return True
    except ImportError as e:
        print(f"导入模块失败: {e}")
        return False
    except Exception as e:
        print(f"执行检查时出错: {e}")
        return False

def main():
    """主函数"""
    print("=== 测试 jetpack_version 修复 ===")
    
    # 设置 Python 路径
    if setup_python_path():
        # 运行测试
        test_checks()
    else:
        print("无法运行测试 (无法找到模块)")


if __name__ == "__main__":
    main()