#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级数据融合测试 - 测试多源数据融合功能
"""

import sys
import os
import json
import time
from datetime import datetime

# 添加路径
sys.path.insert(0, r"D:\project\nastool7\nastool-core")

from nastool_core.utils.data_source import DataFusionEngine, DataSourceResult, FusionMethod, OutlierMethod
from nastool_core.utils.confidence_scorer import ConfidenceScorer
from nastool_core.utils.consistency_validator import ConsistencyValidator

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
    
    def save_bugs(self, filename="bugs_data_fusion.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.bugs, f, indent=2, ensure_ascii=False)
        print(f"\n保存了 {len(self.bugs)} 个BUG到 {filename}")

def test_1_basic_fusion(bug_tracker):
    """测试1: 基本数据融合"""
    print("\n" + "="*60)
    print("测试1: 基本数据融合")
    print("="*60)
    
    try:
        engine = DataFusionEngine()
        
        results = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.9),
            DataSourceResult(value=51.0, source="sensors", timestamp=time.time(), confidence=0.85),
            DataSourceResult(value=50.5, source="hwmon", timestamp=time.time(), confidence=0.95)
        ]
        
        fused_value, metadata = engine.fuse_data(results, FusionMethod.WEIGHTED_AVERAGE)
        print(f"融合结果: {fused_value}")
        print(f"置信度: {metadata.get('confidence', 0)}")
        print(f"数据源: {metadata.get('sources', [])}")
        
        if fused_value is None:
            bug_tracker.add_bug(
                "基本数据融合",
                "融合结果为None",
                "critical",
                {}
            )
            return False
        
        if not (50.0 <= fused_value <= 51.0):
            bug_tracker.add_bug(
                "基本数据融合",
                f"融合结果超出范围: {fused_value}",
                "medium",
                {"fused_value": fused_value}
            )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "基本数据融合",
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_2_outlier_detection(bug_tracker):
    """测试2: 异常值检测"""
    print("\n" + "="*60)
    print("测试2: 异常值检测")
    print("="*60)
    
    try:
        engine = DataFusionEngine()
        
        # 测试IQR异常值检测
        results = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.9),
            DataSourceResult(value=51.0, source="sensors", timestamp=time.time(), confidence=0.85),
            DataSourceResult(value=52.0, source="hwmon", timestamp=time.time(), confidence=0.95),
            DataSourceResult(value=80.0, source="faulty", timestamp=time.time(), confidence=0.5)
        ]
        
        fused_value, metadata = engine.fuse_data(results, FusionMethod.WEIGHTED_AVERAGE)
        print(f"融合结果（含异常值）: {fused_value}")
        print(f"数据源数量: {metadata.get('source_count', 0)}")
        
        if fused_value > 60:
            bug_tracker.add_bug(
                "异常值检测",
                f"异常值未被正确过滤: {fused_value} > 60",
                "high",
                {"fused_value": fused_value}
            )
        
        # 测试Z-score异常值检测
        engine_zscore = DataFusionEngine()
        engine_zscore.config.outlier_method = OutlierMethod.Z_SCORE
        
        fused_value_z, metadata_z = engine_zscore.fuse_data(results, FusionMethod.WEIGHTED_AVERAGE)
        print(f"Z-score融合结果: {fused_value_z}")
        
        # 测试MAD异常值检测
        engine_mad = DataFusionEngine()
        engine_mad.config.outlier_method = OutlierMethod.MAD
        
        fused_value_m, metadata_m = engine_mad.fuse_data(results, FusionMethod.WEIGHTED_AVERAGE)
        print(f"MAD融合结果: {fused_value_m}")
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "异常值检测",
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_3_consistency_validation(bug_tracker):
    """测试3: 一致性验证"""
    print("\n" + "="*60)
    print("测试3: 一致性验证")
    print("="*60)
    
    try:
        validator = ConsistencyValidator()
        
        # 测试时间一致性
        results = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.9),
            DataSourceResult(value=51.0, source="sensors", timestamp=time.time() + 0.5, confidence=0.85),
            DataSourceResult(value=50.5, source="hwmon", timestamp=time.time() + 1.0, confidence=0.95)
        ]
        
        consistency_checks = validator.validate(results)
        print("一致性检查结果:")
        for name, check in consistency_checks.items():
            print(f"  {name}: {check.is_consistent} - {check.details}")
        
        if not consistency_checks.get("overall", type('obj', (object,), {'is_consistent': False})).is_consistent:
            bug_tracker.add_bug(
                "一致性验证",
                "总体一致性检查失败",
                "medium",
                {"checks": {k: v.is_consistent for k, v in consistency_checks.items()}}
            )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "一致性验证",
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_4_confidence_scoring(bug_tracker):
    """测试4: 置信度评分"""
    print("\n" + "="*60)
    print("测试4: 置信度评分")
    print("="*60)
    
    try:
        scorer = ConfidenceScorer()
        
        # 测试高置信度场景
        results_high = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.9),
            DataSourceResult(value=51.0, source="sensors", timestamp=time.time(), confidence=0.85),
            DataSourceResult(value=50.5, source="hwmon", timestamp=time.time(), confidence=0.95)
        ]
        
        confidence_high = scorer.calculate_confidence(results_high, check_id="cpu_temp", device_type="jetson")
        print(f"高置信度评分: {confidence_high.score}")
        print(f"置信度因子: {confidence_high.factors}")
        
        if confidence_high.score < 0.7:
            bug_tracker.add_bug(
                "置信度评分",
                f"高置信度场景评分过低: {confidence_high.score} < 0.7",
                "low",
                {"score": confidence_high.score, "factors": confidence_high.factors}
            )
        
        # 测试低置信度场景
        results_low = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.5),
            DataSourceResult(value=80.0, source="sensors", timestamp=time.time(), confidence=0.5)
        ]
        
        confidence_low = scorer.calculate_confidence(results_low, check_id="cpu_temp", device_type="jetson")
        print(f"低置信度评分: {confidence_low.score}")
        
        if confidence_low.score > 0.8:
            bug_tracker.add_bug(
                "置信度评分",
                f"低置信度场景评分过高: {confidence_low.score} > 0.8",
                "low",
                {"score": confidence_low.score}
            )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "置信度评分",
            f"测试失败: {str(e)}",
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
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def test_6_edge_cases(bug_tracker):
    """测试6: 边缘情况"""
    print("\n" + "="*60)
    print("测试6: 边缘情况")
    print("="*60)
    
    try:
        engine = DataFusionEngine()
        
        # 测试单数据源
        single_result = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=time.time(), confidence=0.9)
        ]
        
        fused_value_single, metadata_single = engine.fuse_data(single_result, FusionMethod.WEIGHTED_AVERAGE)
        print(f"单数据源结果: {fused_value_single}")
        
        if fused_value_single is None:
            bug_tracker.add_bug(
                "边缘情况测试",
                "单数据源处理失败",
                "high",
                {}
            )
        
        # 测试空数据
        empty_results = []
        fused_value_empty, metadata_empty = engine.fuse_data(empty_results, FusionMethod.WEIGHTED_AVERAGE)
        print(f"空数据结果: {fused_value_empty}")
        
        if fused_value_empty is not None:
            bug_tracker.add_bug(
                "边缘情况测试",
                "空数据应该返回None",
                "low",
                {"fused_value": fused_value_empty}
            )
        
        # 测试两个数据源
        two_results = [
            DataSourceResult(value=50.0, source="s1", timestamp=time.time(), confidence=0.9),
            DataSourceResult(value=52.0, source="s2", timestamp=time.time(), confidence=0.85)
        ]
        
        fused_value_two, metadata_two = engine.fuse_data(two_results, FusionMethod.WEIGHTED_AVERAGE)
        print(f"两个数据源结果: {fused_value_two}")
        
        if fused_value_two is None:
            bug_tracker.add_bug(
                "边缘情况测试",
                "两个数据源处理失败",
                "high",
                {}
            )
        
        return True
    except Exception as e:
        bug_tracker.add_bug(
            "边缘情况测试",
            f"测试失败: {str(e)}",
            "critical",
            {"error": str(e)}
        )
        return False

def main():
    print("="*60)
    print("NASTool V4.1 高级数据融合测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    bug_tracker = BugTracker()
    
    # 运行所有测试
    tests = [
        ("基本数据融合", test_1_basic_fusion),
        ("异常值检测", test_2_outlier_detection),
        ("一致性验证", test_3_consistency_validation),
        ("置信度评分", test_4_confidence_scoring),
        ("融合方法测试", test_5_fusion_methods),
        ("边缘情况测试", test_6_edge_cases)
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