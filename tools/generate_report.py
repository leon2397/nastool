#!/usr/bin/env python3
"""
NASTool 检测器测试报告生成器
生成详细的测试报告
"""
import os
import sys
import time
from datetime import datetime

# 设置路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-core'))

def generate_report():
    """生成完整的测试报告"""
    from unified_checker_executor import UnifiedCheckerExecutor
    executor = UnifiedCheckerExecutor()
    
    report = []
    report.append("="*70)
    report.append("📊 NASTool 检测器功能测试报告")
    report.append("="*70)
    report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"测试环境: 局域网本地机器")
    report.append(f"检测器总数: {len(executor.checkers)}")
    report.append(f"可用检测器: {sum(1 for c in executor.checkers if c['available'])}")
    report.append("="*70)
    
    # 按类别测试并生成报告
    categories = ['system', 'network', 'storage', 'security', 'ai', 'nas', 'usb']
    category_names = {
        'system': '系统检测',
        'network': '网络检测',
        'storage': '存储检测',
        'security': '安全检测',
        'ai': 'AI/机器学习检测',
        'nas': 'NAS服务检测',
        'usb': 'USB设备检测'
    }
    
    overall_stats = {'total': 0, 'passed': 0, 'failed': 0}
    
    for category in categories:
        report.append(f"\n📁 {category_names[category]}")
        report.append("-" * 50)
        
        category_checkers = [c for c in executor.checkers if c.get('category') == category]
        cat_stats = {'passed': 0, 'failed': 0}
        
        for checker in category_checkers:
            checker_id = checker['id']
            name = checker.get('name', checker_id)
            
            try:
                result = executor.execute_checker(checker_id)
                
                if result.get('status') == 'success':
                    cat_stats['passed'] += 1
                    status = "✅"
                    result_data = result.get('result', {})
                    if isinstance(result_data, dict):
                        summary = result_data.get('summary', result_data.get('message', '检测通过'))
                    else:
                        summary = str(result_data)[:80]
                    report.append(f"   {status} {name}: {summary}")
                else:
                    cat_stats['failed'] += 1
                    status = "❌"
                    message = result.get('message', '检测失败')
                    report.append(f"   {status} {name}: {message}")
                    
            except Exception as e:
                cat_stats['failed'] += 1
                report.append(f"   ❌ {name}: 异常 - {str(e)}")
        
        overall_stats['total'] += len(category_checkers)
        overall_stats['passed'] += cat_stats['passed']
        overall_stats['failed'] += cat_stats['failed']
        
        pass_rate = (cat_stats['passed'] / len(category_checkers)) * 100 if category_checkers else 0
        report.append(f"\n   📊 统计: {cat_stats['passed']}/{len(category_checkers)} 通过 ({pass_rate:.1f}%)")
    
    # 生成汇总
    report.append("\n" + "="*70)
    report.append("🎯 测试汇总")
    report.append("="*70)
    
    overall_pass_rate = (overall_stats['passed'] / overall_stats['total']) * 100 if overall_stats['total'] else 0
    
    report.append(f"检测器总数: {overall_stats['total']}")
    report.append(f"通过: {overall_stats['passed']}")
    report.append(f"失败: {overall_stats['failed']}")
    report.append(f"通过率: {overall_pass_rate:.1f}%")
    
    # 功能统计
    from feature_manager import FeatureManager
    manager = FeatureManager()
    summary = manager.get_feature_summary()
    
    report.append("\n📈 功能模块统计")
    report.append("-" * 50)
    report.append(f"   检测器: {summary['checkers']} 个")
    report.append(f"   适配器: {summary['adapters']} 个")
    report.append(f"   修复引擎: {summary['fixes']} 个")
    report.append(f"   报告器: {summary['reporters']} 个")
    report.append(f"   CLI命令: {summary['cli_commands']} 个")
    report.append(f"   监控器: {summary['monitors']} 个")
    report.append(f"   探测器: {summary['detectors']} 个")
    report.append(f"   诊断器: {summary['diagnostics']} 个")
    report.append(f"   总计: {summary['total']} 个功能")
    
    # 生成结论
    report.append("\n" + "="*70)
    report.append("📋 测试结论")
    report.append("="*70)
    
    if overall_pass_rate >= 90:
        report.append("✅ 测试通过！NASTool功能完整，可正常运行")
    elif overall_pass_rate >= 70:
        report.append("⚠️ 测试基本通过，但有部分功能需要修复")
    else:
        report.append("❌ 测试未通过，需要修复大量功能")
    
    # 保存报告
    report_path = os.path.join(PROJECT_ROOT, 'test_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    # 打印报告
    print('\n'.join(report))
    print(f"\n📝 报告已保存到: {report_path}")

def main():
    """主函数"""
    generate_report()

if __name__ == '__main__':
    main()
