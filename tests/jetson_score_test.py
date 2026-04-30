#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试设备上的评分计算"""
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

def detect_device_type():
    """检测设备类型"""
    device_info = {
        "model": None,
        "is_jetson": False
    }
    
    model_path = "/proc/device-tree/model"
    if os.path.exists(model_path):
        try:
            with open(model_path, "rb") as f:
                raw = f.read().strip()
            
            try:
                model = raw.decode("utf-8", errors="replace").strip()
            except Exception:
                model = str(raw)
            
            device_info["model"] = model
            device_info["is_jetson"] = 'jetson' in model.lower()
            
        except Exception as e:
            print(f"读取设备型号失败: {e}")
    else:
        print(f"设备型号文件不存在: {model_path}")
    
    return device_info

def test_score_calculation():
    """测试评分计算"""
    try:
        from nastool_core.checks import run_all_checks
        
        print("运行真实诊断...")
        summary = run_all_checks(full_mode=True)
        
        print(f"评分={summary.score} 通过={summary.passed} 警告={summary.warnings} 严重={summary.critical}")
        
        # 检查第一个失败项的严重程度类型
        for r in summary.results:
            if not r.passed:
                sev_type = type(r.severity).__name__
                sev_val = r.severity.value if hasattr(r.severity, 'value') else r.severity
                print(f"第一个失败项: {r.check_id} -> 严重程度类型={sev_type} 值={repr(sev_val)}")
                break
        
        # 尝试健康报告
        try:
            report = summary.get_health_report()
            print(f"健康报告 评分={report.overall_score} 等级={report.grade()}")
        except Exception as e:
            print(f"健康报告生成失败: {e}")
        
        # 直接测试 HealthScorer
        try:
            from nastool_core.utils.health_scorer import HealthScorer
            scorer = HealthScorer()
            scorer.add_results(summary.results)
            r2 = scorer.calculate()
            print(f"HealthScorer 评分={r2.overall_score} 等级={r2.grade()}")
        except Exception as e:
            print(f"HealthScorer 测试失败: {e}")
        
        return True
    except ImportError as e:
        print(f"导入模块失败: {e}")
        return False
    except Exception as e:
        print(f"执行测试时出错: {e}")
        return False

def main():
    """主函数"""
    print("=== 评分计算测试 ===")
    
    # 检测设备类型
    device_info = detect_device_type()
    
    if device_info["model"]:
        print(f"设备型号: {device_info['model']}")
        print(f"是否为 Jetson: {device_info['is_jetson']}")
    else:
        print("无法获取设备型号")
    
    # 设置 Python 路径
    if setup_python_path():
        # 运行评分测试
        test_score_calculation()
    else:
        print("无法运行测试 (无法找到模块)")


if __name__ == "__main__":
    main()