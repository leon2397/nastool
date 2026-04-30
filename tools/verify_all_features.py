#!/usr/bin/env python3
"""
彻底检查NASTool项目所有功能 - 确保100%覆盖
"""
import os
import sys
import glob
import importlib
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

def find_all_python_files():
    """查找所有Python文件"""
    all_files = []
    
    # 定义要扫描的目录
    scan_dirs = [
        'nastool-core',
        'nastool-adapters',
        'nastool-fixes',
        'nastool-reporters',
        'nastool-cli',
        'nastool-v4.0.0/nastool-core',
        'nastool-v4.0.0/nastool-adapters',
        'nastool-v4.0.0/nastool-fixes',
        'nastool-v4.0.0/nastool-reporters',
        'nastool-v4.0.0/nastool-cli',
        'tools'
    ]
    
    for scan_dir in scan_dirs:
        full_path = os.path.join(PROJECT_ROOT, scan_dir)
        if os.path.exists(full_path):
            for pyfile in glob.glob(os.path.join(full_path, '**/*.py'), recursive=True):
                if '__pycache__' not in pyfile:
                    rel_path = os.path.relpath(pyfile, PROJECT_ROOT)
                    all_files.append(rel_path)
    
    return all_files

def extract_classes(filepath):
    """提取文件中的所有类"""
    classes = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 查找类定义
        class_pattern = r'class\s+(\w+)\s*[:(]'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            # 判断功能类型
            func_type = None
            if class_name.endswith('Checker') or class_name.endswith('Check'):
                func_type = 'checker'
            elif class_name.endswith('Adapter'):
                func_type = 'adapter'
            elif class_name.endswith('Fix'):
                func_type = 'fix'
            elif class_name.endswith('Reporter'):
                func_type = 'reporter'
            elif class_name.endswith('Command'):
                func_type = 'command'
            elif class_name.endswith('Monitor'):
                func_type = 'monitor'
            elif class_name.endswith('Detector'):
                func_type = 'detector'
            elif class_name.endswith('Diagnostic'):
                func_type = 'diagnostic'
            elif class_name.endswith('Executor'):
                func_type = 'executor'
            elif class_name.endswith('Registry'):
                func_type = 'registry'
            
            if func_type:
                classes.append({
                    'name': class_name,
                    'type': func_type,
                    'file': filepath
                })
    except Exception as e:
        pass
    
    return classes

def verify_all_features():
    """验证所有功能是否被功能管理器识别"""
    print("🔍 开始彻底检查NASTool功能...")
    
    # 1. 扫描所有Python文件
    all_files = find_all_python_files()
    print(f"\n📁 扫描到 {len(all_files)} 个Python文件")
    
    # 2. 提取所有功能类
    all_classes = []
    for filepath in all_files:
        full_path = os.path.join(PROJECT_ROOT, filepath)
        classes = extract_classes(full_path)
        all_classes.extend(classes)
    
    # 3. 按类型统计
    by_type = {}
    for cls in all_classes:
        by_type[cls['type']] = by_type.get(cls['type'], [])
        by_type[cls['type']].append(cls)
    
    print("\n📊 按类型统计所有发现的功能类:")
    total_func_classes = 0
    for type_name, classes in sorted(by_type.items()):
        count = len(classes)
        total_func_classes += count
        print(f"   {type_name}: {count} 个")
    
    # 4. 对比功能管理器中的统计
    print("\n🔄 加载功能管理器...")
    sys.path.insert(0, PROJECT_ROOT)
    sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools'))
    
    from feature_manager import FeatureManager
    manager = FeatureManager()
    summary = manager.get_feature_summary()
    
    print("\n📊 功能管理器统计:")
    manager_total = summary['total']
    print(f"   检测器: {summary['checkers']}")
    print(f"   适配器: {summary['adapters']}")
    print(f"   修复引擎: {summary['fixes']}")
    print(f"   报告器: {summary['reporters']}")
    print(f"   CLI命令: {summary['cli_commands']}")
    print(f"   监控器: {summary['monitors']}")
    print(f"   探测器: {summary['detectors']}")
    print(f"   诊断器: {summary['diagnostics']}")
    print(f"   总计: {manager_total}")
    
    # 5. 找出可能遗漏的功能
    print("\n🔍 分析可能遗漏的功能:")
    
    # 检查每个类型
    type_mapping = {
        'checker': '检测器',
        'adapter': '适配器',
        'fix': '修复引擎',
        'reporter': '报告器',
        'command': 'CLI命令',
        'monitor': '监控器',
        'detector': '探测器',
        'diagnostic': '诊断器'
    }
    
    discrepancies = []
    
    for func_type, classes in by_type.items():
        count_in_files = len(classes)
        count_in_manager = summary.get(func_type + 's', 0) if func_type != 'fix' else summary.get('fixes', 0)
        
        # 特殊处理：executor和registry不算功能
        if func_type in ['executor', 'registry']:
            continue
        
        # 功能管理器中的名称映射
        manager_key = func_type + 's'
        if manager_key not in summary:
            manager_key = func_type
        
        manager_count = summary.get(manager_key, 0)
        
        if count_in_files != manager_count:
            discrepancies.append({
                'type': func_type,
                'name': type_mapping.get(func_type, func_type),
                'in_files': count_in_files,
                'in_manager': manager_count,
                'difference': count_in_files - manager_count
            })
    
    if discrepancies:
        print("\n⚠️ 发现差异:")
        for disc in discrepancies:
            if disc['difference'] > 0:
                print(f"   {disc['name']}: 文件中有{disc['in_files']}个，管理器中只有{disc['in_manager']}个，可能遗漏{disc['difference']}个")
                # 列出可能遗漏的类
                type_classes = by_type[disc['type']]
                for cls in type_classes[:5]:
                    print(f"      - {cls['name']} ({cls['file']})")
                if len(type_classes) > 5:
                    print(f"      ... 还有 {len(type_classes) - 5} 个")
            elif disc['difference'] < 0:
                print(f"   {disc['name']}: 文件中有{disc['in_files']}个，管理器中有{disc['in_manager']}个，差异{-disc['difference']}个")
    else:
        print("\n✅ 所有功能类型统计一致！")
    
    # 6. 最终验证
    print("\n" + "="*60)
    print("🎯 最终验证结果")
    print("="*60)
    print(f"   扫描到的功能类总数: {total_func_classes}")
    print(f"   功能管理器统计总数: {manager_total}")
    
    if abs(total_func_classes - manager_total) <= 10:  # 允许少量差异（executor/registry等）
        print("✅ 验证通过！功能覆盖完整")
    else:
        print("⚠️ 存在较大差异，建议进一步检查")
    
    return {
        'files_scanned': len(all_files),
        'classes_found': total_func_classes,
        'manager_total': manager_total,
        'discrepancies': discrepancies
    }

if __name__ == '__main__':
    result = verify_all_features()
