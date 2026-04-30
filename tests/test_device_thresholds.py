#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备识别和自适应阈值测试
"""

import sys
import os
import json
import time
from datetime import datetime

# 添加路径
sys.path.insert(0, r"D:\project\nastool7\nastool-core")

from nastool_core.checks import run_mock_checks, list_checks
from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
from nastool_core.utils.data_source import DataFusionEngine, DataSourceResult, FusionMethod
from nastool_core.utils.confidence_scorer import ConfidenceScorer

class BugTracker:
    def __init__(self):
        self.bugs = []
    
    def add_bug(self, test_name, description, severity, details=None):
        bug = {
            "id": len(self.bugs) + 1,
            "test_name": test_name,
            "description": description,
            "severity": severity,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.bugs.append(bug)
        print(f"[BUG #{bug['id']}] {test_name}: {description}")
        return bug
    
    def save_bugs(self, filename="bugs_device_thresholds.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.bugs, f, indent=2, ensure_ascii=False)
        print(f"\n保存了 {len(self.bugs)} 个BUG到 {filename}")

def test_1_device_detection(bug_tracker):
    """测试1: 设备检测"""
    print("\n" + "="*60)
    print("测试1: 设备检测")
    print("="*60)
    
    try:
        # 检查GPU检测
        checks = list_checks()
        gpu_check = checks.get("gpu_detected")
        
        if gpu_check:
            print(f"GPU检测项存在: {gpu_check.get('title', 'Unknown')}")
            print(f"类别: {gpu_check.get('category', 'Unknown')}")
        else:
            bug_tracker.add_bug(
                "设备检测",
                "GPU检测项不存在",
                "medium",
                {}
            )
        
        # 检查CPU温度检测
        cpu_temp_check = checks.get("cpu_temperature")
        
        if cpu_temp_check:
            print(f"CPU温度检测项存在: {cpu_temp_check.get('title', 'Unknown')}")
            print(f"类别: {cpu_temp_check.get('category', 'Unknown')}")
        else:
            bug_tracker.add_bug(
                "设备检测",
                "CPU温度检测项不存在",
                "medium",
                {}
            )
        
        # 额外检查：直接导入GPU检测函数
        try:
            from nastool_core.checks.ai.gpu_detected import gpu_detected
            print(f"GPU检测函数已导入")
            print(f"GPU检测函数类型: {type(gpu_detected)}")
        except Exception as e:
            print(f"GPU检测函数导入失败: {str(e)}")
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "设备检测",
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_2_threshold_configuration(bug_tracker):
    """测试2: 阈值配置"""
    print("\n" + "="*60)
    print("测试2: 阈值配置")
    print("="*60)
    
    try:
        # 检查CPU温度检测的阈值
        from nastool_core.checks.system.cpu_temp import CPUTempCheck
        
        cpu_check = CPUTempCheck()
        print(f"CPU温度警告阈值: {cpu_check.TEMP_WARNING}°C")
        print(f"CPU温度严重阈值: {cpu_check.TEMP_CRITICAL}°C")
        
        # 验证阈值是否合理
        if cpu_check.TEMP_WARNING >= cpu_check.TEMP_CRITICAL:
            bug_tracker.add_bug(
                "阈值配置",
                f"警告阈值({cpu_check.TEMP_WARNING}) >= 严重阈值({cpu_check.TEMP_CRITICAL})",
                "high",
                {
                    "warning": cpu_check.TEMP_WARNING,
                    "critical": cpu_check.TEMP_CRITICAL
                }
            )
        
        # 检查GPU检测的阈值
        from nastool_core.checks.ai.gpu_detected import gpu_detected
        
        print("GPU检测项配置:")
        print(f"  函数类型: {type(gpu_detected)}")
        print(f"  函数名: {gpu_detected.__name__}")
        
        # 尝试获取装饰器信息
        try:
            # gpu_detected是一个装饰器函数，不是类
            # 我们只能访问函数属性，不能访问类属性
            print(f"  函数文档: {gpu_detected.__doc__[:100] if gpu_detected.__doc__ else 'None'}")
        except Exception as e:
            print(f"  获取GPU检测项信息失败: {str(e)}")
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "阈值配置",
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_3_device_specific_thresholds(bug_tracker):
    """测试3: 设备特定阈值"""
    print("\n" + "="*60)
    print("测试3: 设备特定阈值")
    print("="*60)
    
    try:
        # 检查是否有设备特定的阈值配置
        # 由于当前实现中可能没有完整的设备识别器，我们检查配置文件
        
        config_paths = [
            os.path.expanduser("~/.nastool/config.json"),
            "config/thresholds.json",
            "config/devices.json"
        ]
        
        found_configs = []
        for config_path in config_paths:
            if os.path.exists(config_path):
                found_configs.append(config_path)
                print(f"找到配置文件: {config_path}")
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        print(f"  配置内容: {json.dumps(config, indent=2, ensure_ascii=False)[:200]}...")
                except Exception as e:
                    print(f"  读取配置失败: {str(e)}")
        
        if not found_configs:
            print("未找到设备特定阈值配置文件")
            bug_tracker.add_bug(
                "设备特定阈值",
                "未找到设备特定阈值配置文件",
                "low",
                {"checked_paths": config_paths}
            )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "设备特定阈值",
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_4_adaptive_thresholds(bug_tracker):
    """测试4: 自适应阈值"""
    print("\n" + "="*60)
    print("测试4: 自适应阈值")
    print("="*60)
    
    try:
        # 测试不同设备类型的阈值差异
        # 由于当前实现可能没有完整的设备识别器，我们模拟不同设备类型
        
        device_types = ["jetson", "rk3588", "rk3568", "generic"]
        
        print("不同设备类型的阈值配置:")
        for device_type in device_types:
            # 模拟不同设备类型的阈值
            if device_type == "jetson":
                warning_temp = 75
                critical_temp = 85
            elif device_type == "rk3588":
                warning_temp = 70
                critical_temp = 80
            elif device_type == "rk3568":
                warning_temp = 70
                critical_temp = 80
            else:
                warning_temp = 75
                critical_temp = 85
            
            print(f"  {device_type}: 警告={warning_temp}°C, 严重={critical_temp}°C")
        
        # 检查置信度评分是否考虑设备类型
        scorer = ConfidenceScorer()
        results = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.9),
            DataSourceResult(value=51.0, source="sensors", timestamp=time.time(), confidence=0.85)
        ]
        
        # 测试不同设备类型的置信度评分
        for device_type in device_types:
            confidence = scorer.calculate_confidence(results, check_id="cpu_temp", device_type=device_type)
            print(f"  {device_type} 置信度: {confidence.score}")
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "自适应阈值",
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_5_threshold_validation(bug_tracker):
    """测试5: 阈值验证"""
    print("\n" + "="*60)
    print("测试5: 阈值验证")
    print("="*60)
    
    try:
        from nastool_core.checks.system.cpu_temp import CPUTempCheck
        
        cpu_check = CPUTempCheck()
        
        # 测试不同温度值的阈值验证
        test_temps = [60, 70, 75, 80, 85, 90]
        
        print("不同温度值的阈值验证:")
        for temp in test_temps:
            # 模拟检测结果
            results = [
                DataSourceResult(value=temp, source="thermal_zone", timestamp=time.time(), confidence=0.9)
            ]
            
            fused_value, metadata = cpu_check.fusion_engine.fuse_data(results, FusionMethod.WEIGHTED_AVERAGE)
            
            # 判断严重性
            if fused_value >= cpu_check.TEMP_CRITICAL:
                severity = "CRITICAL"
            elif fused_value >= cpu_check.TEMP_WARNING:
                severity = "WARNING"
            else:
                severity = "PASSED"
            
            print(f"  {temp}°C: {severity}")
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "阈值验证",
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_6_mock_diagnosis_with_thresholds(bug_tracker):
    """测试6: Mock诊断测试"""
    print("\n" + "="*60)
    print("测试6: Mock诊断测试")
    print("="*60)
    
    try:
        # 运行mock诊断
        result = run_mock_checks("healthy")
        
        print(f"健康评分: {result.score}")
        print(f"总检测项: {result.total}")
        print(f"通过: {result.passed}, 警告: {result.warnings}, 严重: {result.critical}")
        
        # 检查温度相关的检测项
        temp_checks = [r for r in result.results if 'temp' in r.check_id.lower()]
        
        print(f"\n温度相关检测项 ({len(temp_checks)}):")
        for check in temp_checks[:5]:  # 只显示前5个
            status = "PASS" if check.passed else check.severity.value.upper()
            print(f"  {check.check_id}: {status} - {check.message}")
        
        if result.score < 90:
            bug_tracker.add_bug(
                "Mock诊断测试",
                f"健康评分低于预期: {result.score} < 90",
                "medium",
                {"score": result.score, "total": result.total}
            )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "Mock诊断测试",
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def main():
    print("="*60)
    print("NASTool V4.1 设备识别和自适应阈值测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    bug_tracker = BugTracker()
    
    # 运行所有测试
    tests = [
        ("设备检测", test_1_device_detection),
        ("阈值配置", test_2_threshold_configuration),
        ("设备特定阈值", test_3_device_specific_thresholds),
        ("自适应阈值", test_4_adaptive_thresholds),
        ("阈值验证", test_5_threshold_validation),
        ("Mock诊断测试", test_6_mock_diagnosis_with_thresholds)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func(bug_tracker)
            results.append((test_name, "PASS" if success else "FAIL"))
        except Exception as e:
            bug_tracker.add_bug(
                test_name,
                f"测试执行失败: {str(e)}",
                "critical",
                {"error": str(e)}
            )
            results.append((test_name, "FAIL"))
    
    # 输出测试结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    for test_name, status in results:
        print(f"[{status}] {test_name}")
    
    # 保存BUG报告
    bug_tracker.save_bugs()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    print(f"总测试数: {len(results)}")
    print(f"通过: {sum(1 for _, s in results if s == 'PASS')}")
    print(f"失败: {sum(1 for _, s in results if s == 'FAIL')}")
    print(f"发现BUG: {len(bug_tracker.bugs)}")

if __name__ == "__main__":
    main()