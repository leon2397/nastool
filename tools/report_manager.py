#!/usr/bin/env python3
"""NASTool 报告管理系统"""

import os
import sys
import json
import sqlite3
from datetime import datetime

class ReportManager:
    def __init__(self):
        self.report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'reports')
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'test_history.db')
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建测试历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                device_name TEXT,
                device_ip TEXT,
                test_mode TEXT,
                timestamp TEXT,
                duration REAL,
                passed INTEGER,
                failed INTEGER,
                error INTEGER,
                total INTEGER,
                report_path TEXT
            )
        ''')
        
        # 创建测试详情表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                history_id INTEGER,
                test_name TEXT,
                status TEXT,
                details TEXT,
                FOREIGN KEY (history_id) REFERENCES test_history(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_report(self, report):
        """保存报告到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 生成报告文件路径
        filename = f"{report['device_id']}_{report['timestamp'].replace(':', '-')}.json"
        report_path = os.path.join(self.report_dir, filename)
        
        # 保存JSON报告
        os.makedirs(self.report_dir, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 保存到数据库
        summary = report['summary']
        cursor.execute('''
            INSERT INTO test_history (
                device_id, device_name, device_ip, test_mode, 
                timestamp, duration, passed, failed, error, total, report_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report['device_id'],
            report['device_name'],
            report['device_ip'],
            report['test_mode'],
            report['timestamp'],
            report['duration'],
            summary['passed'],
            summary['failed'],
            summary['error'],
            summary['total'],
            filename
        ))
        
        history_id = cursor.lastrowid
        
        # 保存测试详情
        for result in report['results']:
            cursor.execute('''
                INSERT INTO test_details (history_id, test_name, status, details)
                VALUES (?, ?, ?, ?)
            ''', (history_id, result['name'], result['status'], result['details']))
        
        conn.commit()
        conn.close()
        
        return filename
    
    def get_reports(self, device_id=None, start_time=None, end_time=None, status=None):
        """查询报告"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM test_history WHERE 1=1'
        params = []
        
        if device_id:
            query += ' AND device_id = ?'
            params.append(device_id)
        
        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time)
        
        if end_time:
            query += ' AND timestamp <= ?'
            params.append(end_time)
        
        if status:
            if status == 'pass':
                query += ' AND failed = 0 AND error = 0'
            elif status == 'fail':
                query += ' AND failed > 0'
            elif status == 'error':
                query += ' AND error > 0'
        
        query += ' ORDER BY timestamp DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        reports = []
        for row in rows:
            reports.append({
                'id': row[0],
                'device_id': row[1],
                'device_name': row[2],
                'device_ip': row[3],
                'test_mode': row[4],
                'timestamp': row[5],
                'duration': row[6],
                'passed': row[7],
                'failed': row[8],
                'error': row[9],
                'total': row[10],
                'report_path': row[11]
            })
        
        conn.close()
        return reports
    
    def get_report_details(self, history_id):
        """获取报告详情"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取基本信息
        cursor.execute('SELECT * FROM test_history WHERE id = ?', (history_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        history = {
            'id': row[0],
            'device_id': row[1],
            'device_name': row[2],
            'device_ip': row[3],
            'test_mode': row[4],
            'timestamp': row[5],
            'duration': row[6],
            'passed': row[7],
            'failed': row[8],
            'error': row[9],
            'total': row[10],
            'report_path': row[11]
        }
        
        # 获取测试详情
        cursor.execute('SELECT * FROM test_details WHERE history_id = ?', (history_id,))
        rows = cursor.fetchall()
        
        details = []
        for row in rows:
            details.append({
                'id': row[0],
                'test_name': row[2],
                'status': row[3],
                'details': row[4]
            })
        
        conn.close()
        
        return {'history': history, 'details': details}
    
    def compare_reports(self, report_ids):
        """对比多个报告"""
        reports = []
        for report_id in report_ids:
            report = self.get_report_details(report_id)
            if report:
                reports.append(report)
        
        if len(reports) < 2:
            return None
        
        # 分析差异
        comparison = {
            'reports': reports,
            'differences': []
        }
        
        # 比较测试结果
        first_details = {d['test_name']: d for d in reports[0]['details']}
        
        for i, report in enumerate(reports[1:], 1):
            for detail in report['details']:
                test_name = detail['test_name']
                if test_name in first_details:
                    first_status = first_details[test_name]['status']
                    current_status = detail['status']
                    
                    if first_status != current_status:
                        comparison['differences'].append({
                            'test_name': test_name,
                            'baseline': reports[0]['device_name'],
                            'baseline_status': first_status,
                            'comparison': report['device_name'],
                            'comparison_status': current_status
                        })
        
        return comparison
    
    def get_device_summary(self, device_id):
        """获取设备测试汇总"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*), SUM(passed), SUM(failed), SUM(error), AVG(duration)
            FROM test_history WHERE device_id = ?
        ''', (device_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'device_id': device_id,
            'test_count': row[0],
            'total_passed': row[1],
            'total_failed': row[2],
            'total_error': row[3],
            'avg_duration': row[4]
        }
    
    def export_report(self, history_id, format='json'):
        """导出报告"""
        report = self.get_report_details(history_id)
        if not report:
            return None
        
        filename = f"report_{history_id}.{format}"
        filepath = os.path.join(self.report_dir, filename)
        
        if format == 'json':
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        
        elif format == 'html':
            html = self._generate_html_report(report)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
        
        return filepath
    
    def _generate_html_report(self, report):
        """生成HTML报告"""
        history = report['history']
        details = report['details']
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>NASTool 测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #4CAF50; color: white; padding: 20px; }}
        .summary {{ margin: 20px 0; }}
        .status {{ padding: 10px; margin: 5px; border-radius: 5px; }}
        .pass {{ background: #d4edda; color: #155724; }}
        .fail {{ background: #f8d7da; color: #721c24; }}
        .error {{ background: #fff3cd; color: #856404; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>NASTool 测试报告</h1>
        <p>设备: {history['device_name']} ({history['device_ip']})</p>
        <p>模式: {history['test_mode']} | 时间: {history['timestamp']} | 耗时: {history['duration']}秒</p>
    </div>
    
    <div class="summary">
        <h2>测试汇总</h2>
        <p>通过: {history['passed']} | 失败: {history['failed']} | 错误: {history['error']} | 总计: {history['total']}</p>
    </div>
    
    <h2>测试详情</h2>
    <table>
        <tr><th>测试项</th><th>状态</th><th>详情</th></tr>
'''
        
        for detail in details:
            status_class = detail['status']
            status_text = {'pass': '✅ 通过', 'fail': '❌ 失败', 'error': '⚠️ 错误'}.get(detail['status'], detail['status'])
            html += f"<tr><td>{detail['test_name']}</td><td class='status {status_class}'>{status_text}</td><td>{detail['details']}</td></tr>"
        
        html += '''
    </table>
</body>
</html>
'''
        return html

def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NASTool 报告管理器')
    subparsers = parser.add_subparsers(dest='command')
    
    # 列出报告
    list_parser = subparsers.add_parser('list', help='列出报告')
    list_parser.add_argument('-d', '--device', help='设备ID')
    list_parser.add_argument('-s', '--status', choices=['pass', 'fail', 'error'], help='状态筛选')
    
    # 查看报告详情
    show_parser = subparsers.add_parser('show', help='查看报告详情')
    show_parser.add_argument('report_id', type=int, help='报告ID')
    
    # 对比报告
    compare_parser = subparsers.add_parser('compare', help='对比报告')
    compare_parser.add_argument('report_ids', nargs='+', type=int, help='报告ID列表')
    
    # 导出报告
    export_parser = subparsers.add_parser('export', help='导出报告')
    export_parser.add_argument('report_id', type=int, help='报告ID')
    export_parser.add_argument('-f', '--format', choices=['json', 'html'], default='json', help='导出格式')
    
    # 设备汇总
    summary_parser = subparsers.add_parser('summary', help='设备测试汇总')
    summary_parser.add_argument('device_id', help='设备ID')
    
    args = parser.parse_args()
    
    rm = ReportManager()
    
    if args.command == 'list':
        reports = rm.get_reports(device_id=args.device, status=args.status)
        print('='*80)
        print('📊 测试报告列表')
        print('='*80)
        print(f"{'ID':<5} {'设备':<15} {'模式':<10} {'时间':<25} {'通过/失败/错误'}")
        print('-'*80)
        for report in reports[:20]:
            print(f"{report['id']:<5} {report['device_name']:<15} {report['test_mode']:<10} {report['timestamp']:<25} {report['passed']}/{report['failed']}/{report['error']}")
        print('='*80)
    
    elif args.command == 'show':
        report = rm.get_report_details(args.report_id)
        if report:
            history = report['history']
            print('='*60)
            print(f"📊 报告详情 (ID: {args.report_id})")
            print('='*60)
            print(f"设备: {history['device_name']} ({history['device_ip']})")
            print(f"模式: {history['test_mode']}")
            print(f"时间: {history['timestamp']}")
            print(f"耗时: {history['duration']}秒")
            print(f"结果: {history['passed']}/{history['total']} 通过")
            print('-'*60)
            print("测试项:")
            for detail in report['details']:
                status = {'pass': '✅', 'fail': '❌', 'error': '⚠️'}.get(detail['status'], '⚪')
                print(f"  {status} {detail['test_name']}: {detail['details']}")
            print('='*60)
    
    elif args.command == 'compare':
        comparison = rm.compare_reports(args.report_ids)
        if comparison:
            print('='*60)
            print('🔍 报告对比')
            print('='*60)
            for diff in comparison['differences']:
                print(f"\n测试项: {diff['test_name']}")
                print(f"  {diff['baseline']}: {diff['baseline_status']}")
                print(f"  {diff['comparison']}: {diff['comparison_status']}")
            if not comparison['differences']:
                print('✅ 所有测试结果一致')
            print('='*60)
    
    elif args.command == 'export':
        filepath = rm.export_report(args.report_id, args.format)
        if filepath:
            print(f"✅ 报告已导出: {filepath}")
        else:
            print('❌ 报告不存在')
    
    elif args.command == 'summary':
        summary = rm.get_device_summary(args.device_id)
        if summary:
            print('='*60)
            print(f"📋 设备 {args.device_id} 测试汇总")
            print('='*60)
            print(f"测试次数: {summary['test_count']}")
            print(f"总通过: {summary['total_passed']}")
            print(f"总失败: {summary['total_failed']}")
            print(f"总错误: {summary['total_error']}")
            print(f"平均耗时: {summary['avg_duration']:.2f}秒")
            print('='*60)
        else:
            print('❌ 设备无测试记录')

if __name__ == '__main__':
    main()
