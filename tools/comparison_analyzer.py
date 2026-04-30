#!/usr/bin/env python3
"""测试对比分析模块"""

import os
import sys
import json
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class ComparisonAnalyzer:
    """测试对比分析器"""
    
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'reports.db')
    
    def compare_reports(self, report_ids):
        """对比多个报告"""
        if len(report_ids) < 2:
            return {'error': '至少需要2个报告进行对比'}
        
        reports = []
        for report_id in report_ids:
            report = self._get_report_by_id(report_id)
            if report:
                reports.append(report)
        
        if len(reports) < 2:
            return {'error': '有效的报告不足2个'}
        
        return self._analyze_comparison(reports)
    
    def _get_report_by_id(self, report_id):
        """根据ID获取报告"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM test_history WHERE id = ?', (report_id,))
            history = cursor.fetchone()
            
            cursor.execute('SELECT * FROM test_details WHERE history_id = ?', (report_id,))
            details = cursor.fetchall()
            
            conn.close()
            
            if history:
                return {
                    'id': history[0],
                    'device_id': history[1],
                    'device_name': history[2],
                    'device_ip': history[3],
                    'test_mode': history[4],
                    'timestamp': history[5],
                    'duration': history[6],
                    'passed': history[7],
                    'failed': history[8],
                    'error': history[9],
                    'total': history[10],
                    'details': [{'test_name': d[2], 'status': d[3], 'details': d[4]} for d in details]
                }
            return None
        except Exception as e:
            print(f"Error getting report: {e}")
            return None
    
    def _analyze_comparison(self, reports):
        """分析对比结果"""
        comparison = {
            'reports': reports,
            'summary': {},
            'trends': [],
            'differences': [],
            'recommendations': []
        }
        
        # 基本统计
        avg_duration = sum(r['duration'] for r in reports) / len(reports)
        total_passed = sum(r['passed'] for r in reports)
        total_failed = sum(r['failed'] for r in reports)
        total_errors = sum(r['error'] for r in reports)
        
        comparison['summary'] = {
            'report_count': len(reports),
            'devices': list(set(r['device_id'] for r in reports)),
            'avg_duration': avg_duration,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_errors': total_errors,
            'overall_pass_rate': (total_passed / sum(r['total'] for r in reports)) * 100 if sum(r['total'] for r in reports) > 0 else 0
        }
        
        # 趋势分析
        if len(reports) > 1:
            sorted_reports = sorted(reports, key=lambda x: x['timestamp'])
            
            for i in range(1, len(sorted_reports)):
                prev = sorted_reports[i-1]
                curr = sorted_reports[i]
                
                trend = {
                    'period': f"{prev['timestamp']} -> {curr['timestamp']}",
                    'duration_change': curr['duration'] - prev['duration'],
                    'passed_change': curr['passed'] - prev['passed'],
                    'failed_change': curr['failed'] - prev['failed'],
                    'error_change': curr['error'] - prev['error']
                }
                comparison['trends'].append(trend)
        
        # 差异分析
        if len(reports) == 2:
            r1, r2 = reports
            comparison['differences'] = self._find_differences(r1, r2)
        
        # 生成建议
        comparison['recommendations'] = self._generate_recommendations(comparison)
        
        return comparison
    
    def _find_differences(self, r1, r2):
        """找出两个报告的差异"""
        differences = []
        
        # 比较基本指标
        if r1['duration'] != r2['duration']:
            diff = abs(r1['duration'] - r2['duration'])
            direction = '增加' if r2['duration'] > r1['duration'] else '减少'
            differences.append(f"测试时长{direction}了 {diff:.2f}秒")
        
        if r1['passed'] != r2['passed']:
            diff = abs(r1['passed'] - r2['passed'])
            direction = '增加' if r2['passed'] > r1['passed'] else '减少'
            differences.append(f"通过数{direction}了 {diff}个")
        
        if r1['failed'] != r2['failed']:
            diff = abs(r1['failed'] - r2['failed'])
            direction = '增加' if r2['failed'] > r1['failed'] else '减少'
            differences.append(f"失败数{direction}了 {diff}个")
        
        # 比较测试详情
        r1_tests = {t['test_name']: t for t in r1['details']}
        r2_tests = {t['test_name']: t for t in r2['details']}
        
        all_tests = set(r1_tests.keys()) | set(r2_tests.keys())
        
        for test_name in all_tests:
            t1 = r1_tests.get(test_name)
            t2 = r2_tests.get(test_name)
            
            if not t1:
                differences.append(f"新增测试项: {test_name}")
            elif not t2:
                differences.append(f"移除测试项: {test_name}")
            elif t1['status'] != t2['status']:
                differences.append(f"{test_name}: {t1['status']} -> {t2['status']}")
        
        return differences
    
    def _generate_recommendations(self, comparison):
        """生成建议"""
        recommendations = []
        summary = comparison['summary']
        
        # 通过率建议
        if summary['overall_pass_rate'] < 80:
            recommendations.append("⚠️ 测试通过率低于80%，建议检查失败的测试项")
        
        # 错误率建议
        if summary['total_errors'] > 0:
            recommendations.append("⚠️ 存在测试错误，建议检查日志排查问题")
        
        # 趋势建议
        for trend in comparison['trends']:
            if trend['duration_change'] > 10:
                recommendations.append("⚠️ 测试时长明显增加，建议优化测试流程")
            if trend['failed_change'] > 0:
                recommendations.append("⚠️ 失败数增加，建议关注相关测试项")
        
        if not recommendations:
            recommendations.append("✅ 测试结果稳定，继续保持")
        
        return recommendations
    
    def generate_summary_report(self, device_id):
        """生成设备测试汇总报告"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM test_history WHERE device_id = ? ORDER BY timestamp DESC', (device_id,))
            records = cursor.fetchall()
            
            if not records:
                return {'error': '该设备没有测试记录'}
            
            conn.close()
            
            total_tests = len(records)
            total_passed = sum(r[7] for r in records)
            total_failed = sum(r[8] for r in records)
            total_errors = sum(r[9] for r in records)
            avg_duration = sum(r[6] for r in records) / len(records)
            
            latest_record = records[0]
            
            return {
                'device_id': device_id,
                'total_tests': total_tests,
                'avg_duration': avg_duration,
                'overall_pass_rate': (total_passed / sum(r[10] for r in records)) * 100 if sum(r[10] for r in records) > 0 else 0,
                'total_passed': total_passed,
                'total_failed': total_failed,
                'total_errors': total_errors,
                'latest_test': {
                    'timestamp': latest_record[5],
                    'duration': latest_record[6],
                    'passed': latest_record[7],
                    'failed': latest_record[8],
                    'error': latest_record[9]
                },
                'trend': self._calculate_trend(records)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_trend(self, records):
        """计算趋势"""
        if len(records) < 2:
            return '数据不足'
        
        recent = records[:3]
        older = records[-3:] if len(records) >= 6 else records[3:]
        
        recent_pass_rate = sum(r[7] for r in recent) / sum(r[10] for r in recent) * 100 if sum(r[10] for r in recent) > 0 else 0
        older_pass_rate = sum(r[7] for r in older) / sum(r[10] for r in older) * 100 if sum(r[10] for r in older) > 0 else 0
        
        diff = recent_pass_rate - older_pass_rate
        
        if diff > 5:
            return f'📈 上升趋势 (+{diff:.1f}%)'
        elif diff < -5:
            return f'📉 下降趋势 ({diff:.1f}%)'
        else:
            return '➡️  保持稳定'
    
    def export_comparison(self, comparison, filepath, format='text'):
        """导出对比报告"""
        if format == 'json':
            content = json.dumps(comparison, ensure_ascii=False, indent=2)
        else:
            content = self._format_text_report(comparison)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def _format_text_report(self, comparison):
        """格式化文本报告"""
        lines = []
        lines.append('='*70)
        lines.append('📊 测试报告对比分析')
        lines.append('='*70)
        
        # 摘要
        summary = comparison['summary']
        lines.append(f"\n📋 对比摘要")
        lines.append(f"  报告数量: {summary['report_count']}")
        lines.append(f"  涉及设备: {', '.join(summary['devices'])}")
        lines.append(f"  平均时长: {summary['avg_duration']:.2f}秒")
        lines.append(f"  总通过率: {summary['overall_pass_rate']:.1f}%")
        
        # 详细报告列表
        lines.append("\n📝 报告详情")
        for i, report in enumerate(comparison['reports'], 1):
            lines.append(f"\n  报告 {i}:")
            lines.append(f"    ID: {report['id']}")
            lines.append(f"    设备: {report['device_name']} ({report['device_ip']})")
            lines.append(f"    模式: {report['test_mode']}")
            lines.append(f"    时间: {report['timestamp']}")
            lines.append(f"    结果: ✅{report['passed']} ⚠️{report['failed']} ❌{report['error']}")
        
        # 趋势分析
        if comparison['trends']:
            lines.append("\n📈 趋势分析")
            for trend in comparison['trends']:
                lines.append(f"\n  {trend['period']}")
                lines.append(f"    时长变化: {'+' if trend['duration_change'] > 0 else ''}{trend['duration_change']:.2f}秒")
                lines.append(f"    通过变化: {'+' if trend['passed_change'] > 0 else ''}{trend['passed_change']}")
                lines.append(f"    失败变化: {'+' if trend['failed_change'] > 0 else ''}{trend['failed_change']}")
        
        # 差异分析
        if comparison['differences']:
            lines.append("\n🔍 差异分析")
            for diff in comparison['differences']:
                lines.append(f"  • {diff}")
        
        # 建议
        lines.append("\n💡 建议")
        for rec in comparison['recommendations']:
            lines.append(f"  {rec}")
        
        lines.append('\n' + '='*70)
        
        return '\n'.join(lines)

def main():
    """命令行接口"""
    import argparse
    parser = argparse.ArgumentParser(description='测试对比分析工具')
    parser.add_argument('action', choices=['compare', 'summary'], help='操作')
    parser.add_argument('ids', nargs='*', help='报告ID列表')
    parser.add_argument('-d', '--device', help='设备ID')
    parser.add_argument('-f', '--format', choices=['text', 'json'], default='text', help='输出格式')
    parser.add_argument('-o', '--output', help='输出文件')
    
    args = parser.parse_args()
    
    analyzer = ComparisonAnalyzer()
    
    if args.action == 'compare':
        if not args.ids:
            print("❌ 需要提供报告ID")
            return
        
        result = analyzer.compare_reports(args.ids)
        if 'error' in result:
            print(f"❌ {result['error']}")
            return
        
        report = analyzer._format_text_report(result) if args.format == 'text' else json.dumps(result, ensure_ascii=False, indent=2)
        print(report)
        
        if args.output:
            analyzer.export_comparison(result, args.output, args.format)
            print(f"\n📊 报告已保存到 {args.output}")
    
    elif args.action == 'summary':
        if not args.device:
            print("❌ 需要提供设备ID")
            return
        
        result = analyzer.generate_summary_report(args.device)
        if 'error' in result:
            print(f"❌ {result['error']}")
            return
        
        print('='*60)
        print('📊 设备测试汇总报告')
        print('='*60)
        print(f"设备ID: {result['device_id']}")
        print(f"测试次数: {result['total_tests']}")
        print(f"平均时长: {result['avg_duration']:.2f}秒")
        print(f"总体通过率: {result['overall_pass_rate']:.1f}%")
        print(f"趋势: {result['trend']}")
        print('='*60)

if __name__ == '__main__':
    main()
