#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全方位测试NASTool V4.1 - 真机测试脚本
测试目标: 192.168.1.123 (Jetson设备)
"""

import sys
import os
import json
import time
from datetime import datetime

# 添加路径
sys.path.insert(0, r"D:\project\nastool7\nastool-core")
sys.path.insert(0, r"D:\project\nastool7\nastool-cli")

from nastool_core.checks import run_mock_checks, run_all_checks, list_checks
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
    
    def save_bugs(self, filename="bugs_round_3.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.bugs, f, indent=2, ensure_ascii=False)
        print(f"\n保存了 {len(self.bugs)} 个BUG到 {filename}")

def test_1_mock_mode(bug_tracker):
    """测试1: Mock模式测试"""
    print("\n" + "="*60)
    print("测试1: Mock模式测试")
    print("="*60)
    
    try:
        result = run_mock_checks("healthy")
        print(f"健康评分: {result.score}")
        print(f"总检测项: {result.total}")
        print(f"通过: {result.passed}, 警告: {result.warnings}, 严重: {result.critical}")
        
        if result.score < 90:
            bug_tracker.add_bug(
                "Mock模式测试",
                f"健康评分低于预期: {result.score} < 90",
                "medium",
                {"score": result.score, "total": result.total}
            )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "Mock模式测试",
            f"Mock模式测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_2_data_fusion(bug_tracker):
    """测试2: 数据融合功能"""
    print("\n" + "="*60)
    print("测试2: 数据融合功能")
    print("="*60)
    
    try:
        engine = DataFusionEngine()
        
        # 测试正常数据融合
        results = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.9),
            DataSourceResult(value=51.0, source="sensors", timestamp=time.time(), confidence=0.85),
            DataSourceResult(value=50.5, source="hwmon", timestamp=time.time(), confidence=0.95)
        ]
        
        fused_value, metadata = engine.fuse_data(results, FusionMethod.WEIGHTED_AVERAGE)
        print(f"融合结果: {fused_value}")
        print(f"置信度: {metadata.get('confidence', 0)}")
        
        # 测试异常值检测
        results_with_outlier = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.9),
            DataSourceResult(value=51.0, source="sensors", timestamp=time.time(), confidence=0.85),
            DataSourceResult(value=52.0, source="hwmon", timestamp=time.time(), confidence=0.95),
            DataSourceResult(value=80.0, source="faulty", timestamp=time.time(), confidence=0.5)
        ]
        
        fused_value_outlier, metadata_outlier = engine.fuse_data(results_with_outlier, FusionMethod.WEIGHTED_AVERAGE)
        print(f"异常值融合结果: {fused_value_outlier}")
        
        if fused_value_outlier > 60:
            bug_tracker.add_bug(
                "数据融合功能",
                f"异常值未被正确过滤: {fused_value_outlier} > 60",
                "medium",
                {"fused_value": fused_value_outlier}
            )
        
        # 测试单数据源
        single_result = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.9)
        ]
        
        fused_value_single, metadata_single = engine.fuse_data(single_result, FusionMethod.WEIGHTED_AVERAGE)
        print(f"单数据源结果: {fused_value_single}")
        
        if fused_value_single is None:
            bug_tracker.add_bug(
                "数据融合功能",
                "单数据源处理失败",
                "high",
                {}
            )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "数据融合功能",
            f"数据融合测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_3_confidence_scoring(bug_tracker):
    """测试3: 置信度评分功能"""
    print("\n" + "="*60)
    print("测试3: 置信度评分功能")
    print("="*60)
    
    try:
        scorer = ConfidenceScorer()
        
        results = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.9),
            DataSourceResult(value=51.0, source="sensors", timestamp=time.time(), confidence=0.85),
            DataSourceResult(value=50.5, source="hwmon", timestamp=time.time(), confidence=0.95)
        ]
        
        confidence = scorer.calculate_confidence(results, check_id="cpu_temp", device_type="jetson")
        print(f"置信度评分: {confidence.score}")
        print(f"置信度因子: {confidence.factors}")
        
        if confidence.score < 0.7:
            bug_tracker.add_bug(
                "置信度评分功能",
                f"置信度评分过低: {confidence.score} < 0.7",
                "low",
                {"score": confidence.score, "factors": confidence.factors}
            )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "置信度评分功能",
            f"置信度评分测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_4_list_checks(bug_tracker):
    """测试4: 列出所有检测项"""
    print("\n" + "="*60)
    print("测试4: 列出所有检测项")
    print("="*60)
    
    try:
        checks = list_checks()
        print(f"总检测项数: {len(checks)}")
        
        # 按类别统计
        categories = {}
        for check_id, check_info in checks.items():
            category = check_info.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
        
        print("检测项分类统计:")
        for category, count in sorted(categories.items()):
            print(f"  {category}: {count}")
        
        if len(checks) < 50:
            bug_tracker.add_bug(
                "列出检测项",
                f"检测项数量过少: {len(checks)} < 50",
                "low",
                {"total_checks": len(checks)}
            )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "列出检测项",
            f"列出检测项测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_5_fusion_methods(bug_tracker):
    """测试5: 所有融合方法"""
    print("\n" + "="*60)
    print("测试5: 所有融合方法")
    print("="*60)
    
    try:
        engine = DataFusionEngine()
        
        results = [
            DataSourceResult(value=50.0, source="s1", timestamp=time.time(), confidence=0.9),
            DataSourceResult(value=52.0, source="s2", timestamp=time.time(), confidence=0.85),
            DataSourceResult(value=51.0, source="s3", timestamp=time.time(), confidence=0.95)
        ]
        
        methods = [
            FusionMethod.WEIGHTED_AVERAGE,
            FusionMethod.MEDIAN,
            FusionMethod.MEAN,
            FusionMethod.MODE,
            FusionMethod.GEOMETRIC_MEAN,
            FusionMethod.HARMONIC_MEAN,
            FusionMethod.MIN,
            FusionMethod.MAX
        ]
        
        print("融合方法测试结果:")
        for method in methods:
            try:
                fused_value, metadata = engine.fuse_data(results, method)
                print(f"  {method.value}: {fused_value}")
            except Exception as e:
                bug_tracker.add_bug(
                    "融合方法测试",
                    f"{method.value} 融合方法失败: {str(e)}",
                    "medium",
                    {"method": method.value, "error": str(e)}
                )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "融合方法测试",
            f"融合方法测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def main():
    print("="*60)
    print("NASTool V4.1 全方位测试 - 真机测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试目标: 192.168.1.123 (Jetson设备)")
    
    bug_tracker = BugTracker()
    
    # 运行所有测试
    tests = [
        ("Mock模式测试", test_1_mock_mode),
        ("数据融合功能", test_2_data_fusion),
        ("置信度评分功能", test_3_confidence_scoring),
        ("列出检测项", test_4_list_checks),
        ("融合方法测试", test_5_fusion_methods)
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