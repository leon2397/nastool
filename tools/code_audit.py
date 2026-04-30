#!/usr/bin/env python3
"""
NASTool 全面代码审计工具
扫描所有功能模块，找出未被整合的代码
"""
import os
import sys
import json

def scan_project(base_path):
    """扫描项目结构"""
    project_info = {
        'modules': [],
        'scripts': [],
        'packages': [],
        'unused_files': [],
        'total_files': 0,
        'total_lines': 0
    }
    
    for root, dirs, files in os.walk(base_path):
        # 跳过某些目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'archive', 'tests']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, base_path)
                
                # 统计行数
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        line_count = len(lines)
                        project_info['total_lines'] += line_count
                except:
                    line_count = 0
                
                project_info['total_files'] += 1
                
                # 判断文件类型
                if '/nastool-' in '/' + rel_path:
                    project_info['packages'].append({
                        'path': rel_path,
                        'lines': line_count
                    })
                elif '/tools/' in '/' + rel_path:
                    project_info['modules'].append({
                        'path': rel_path,
                        'lines': line_count
                    })
                elif '/diagnostics/' in '/' + rel_path or '/network/' in '/' + rel_path or '/remote/' in '/' + rel_path:
                    project_info['scripts'].append({
                        'path': rel_path,
                        'lines': line_count
                    })
    
    return project_info

def analyze_main_integration(base_path):
    """分析主入口的整合情况"""
    main_file = os.path.join(base_path, 'nastool.py')
    integration_info = {
        'main_features': [],
        'called_modules': [],
        'uncalled_modules': []
    }
    
    if os.path.exists(main_file):
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 分析调用的模块
            called_modules = []
            for line in content.split('\n'):
                if 'import' in line and 'tools' in line:
                    called_modules.append(line.strip())
                if 'from tools' in line:
                    called_modules.append(line.strip())
            
            integration_info['called_modules'] = called_modules
    
    return integration_info

def generate_report(project_info, integration_info):
    """生成审计报告"""
    report = "="*70 + "\n"
    report += "🔍 NASTool 全面代码审计报告\n"
    report += "="*70 + "\n\n"
    
    # 项目概览
    report += "📊 项目概览\n"
    report += "-"*40 + "\n"
    report += f"总文件数: {project_info['total_files']}\n"
    report += f"总行数: {project_info['total_lines']:,}\n"
    report += f"工具模块数: {len(project_info['modules'])}\n"
    report += f"脚本数: {len(project_info['scripts'])}\n"
    report += f"包数: {len(project_info['packages'])}\n\n"
    
    # 工具模块
    report += "🛠️ 工具模块\n"
    report += "-"*40 + "\n"
    for mod in sorted(project_info['modules'], key=lambda x: x['path']):
        report += f"  {mod['path']:40s} ({mod['lines']}行)\n"
    report += "\n"
    
    # 脚本文件
    report += "📜 脚本文件\n"
    report += "-"*40 + "\n"
    for script in sorted(project_info['scripts'], key=lambda x: x['path']):
        report += f"  {script['path']:40s} ({script['lines']}行)\n"
    report += "\n"
    
    # 包模块
    report += "📦 包模块\n"
    report += "-"*40 + "\n"
    for pkg in sorted(project_info['packages'], key=lambda x: x['path']):
        report += f"  {pkg['path']:40s} ({pkg['lines']}行)\n"
    report += "\n"
    
    # 整合分析
    report += "🔗 主入口整合分析\n"
    report += "-"*40 + "\n"
    report += "已调用的模块:\n"
    for mod in integration_info['called_modules']:
        report += f"  ✅ {mod}\n"
    
    return report

def main():
    base_path = os.path.dirname(os.path.dirname(__file__))
    print("🚀 正在进行全面代码审计...")
    
    project_info = scan_project(base_path)
    integration_info = analyze_main_integration(base_path)
    
    report = generate_report(project_info, integration_info)
    print(report)
    
    # 保存报告
    report_path = os.path.join(base_path, 'docs/CODE_AUDIT_REPORT.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n📝 报告已保存到: {report_path}")

if __name__ == '__main__':
    main()
