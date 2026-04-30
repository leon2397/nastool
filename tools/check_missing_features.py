#!/usr/bin/env python3
"""全面扫描NASTool项目，检查是否有遗漏的功能"""
import os
import sys
import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

def scan_all_python_files():
    """扫描所有Python文件"""
    all_files = []
    
    # 扫描主要目录
    directories = [
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
    
    for directory in directories:
        path = os.path.join(PROJECT_ROOT, directory)
        if os.path.exists(path):
            for pyfile in glob.glob(os.path.join(path, '**/*.py'), recursive=True):
                # 排除__pycache__和__init__.py
                if '__pycache__' not in pyfile and not pyfile.endswith('__init__.py'):
                    rel_path = os.path.relpath(pyfile, PROJECT_ROOT)
                    all_files.append(rel_path)
    
    return all_files

def analyze_file(filepath):
    """分析单个文件，提取功能信息"""
    features = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 查找类定义
    import re
    class_pattern = r'class\s+(\w+)\s*[:(]'
    for match in re.finditer(class_pattern, content):
        class_name = match.group(1)
        # 判断可能的功能类型
        if class_name.endswith('Checker') or class_name.endswith('Check'):
            features.append({'type': 'checker', 'name': class_name})
        elif class_name.endswith('Adapter'):
            features.append({'type': 'adapter', 'name': class_name})
        elif class_name.endswith('Fix'):
            features.append({'type': 'fix', 'name': class_name})
        elif class_name.endswith('Reporter'):
            features.append({'type': 'reporter', 'name': class_name})
        elif class_name.endswith('Command'):
            features.append({'type': 'command', 'name': class_name})
        elif class_name.endswith('Diagnostic'):
            features.append({'type': 'diagnostic', 'name': class_name})
        elif class_name.endswith('Monitor'):
            features.append({'type': 'monitor', 'name': class_name})
        elif class_name.endswith('Detector'):
            features.append({'type': 'detector', 'name': class_name})
    
    return features

def main():
    print("🔍 全面扫描NASTool项目功能...")
    
    all_files = scan_all_python_files()
    print(f"\n📁 找到 {len(all_files)} 个Python文件")
    
    # 分析每个文件
    all_features = []
    for filepath in all_files:
        full_path = os.path.join(PROJECT_ROOT, filepath)
        features = analyze_file(full_path)
        for feat in features:
            feat['file'] = filepath
            all_features.append(feat)
    
    # 按类型统计
    by_type = {}
    for feat in all_features:
        by_type[feat['type']] = by_type.get(feat['type'], [])
        by_type[feat['type']].append(feat)
    
    print("\n📊 按类型统计发现的功能:")
    for type_name, features in sorted(by_type.items()):
        print(f"   {type_name}: {len(features)} 个")
    
    # 详细列出未被标准命名模式覆盖的功能
    print("\n🔍 可能遗漏的功能（非标准命名）:")
    non_standard = []
    for feat in all_features:
        if feat['type'] not in ['checker', 'adapter', 'fix', 'reporter']:
            non_standard.append(feat)
    
    if non_standard:
        for feat in non_standard[:20]:
            print(f"   [{feat['type']}] {feat['name']} - {feat['file']}")
        if len(non_standard) > 20:
            print(f"   ... 还有 {len(non_standard) - 20} 个")
    else:
        print("   无")
    
    # 检查是否有未被扫描的目录
    print("\n📋 检查项目结构完整性:")
    check_dirs = [
        ('nastool-core/nastool_core/checks', '检测器'),
        ('nastool-adapters/nastool_adapters', '适配器'),
        ('nastool-fixes/nastool_fixes', '修复器'),
        ('nastool-reporters/nastool_reporters', '报告器'),
        ('nastool-cli/nastool_cli', 'CLI命令')
    ]
    
    for dir_path, desc in check_dirs:
        full_path = os.path.join(PROJECT_ROOT, dir_path)
        if os.path.exists(full_path):
            files = [f for f in os.listdir(full_path) if f.endswith('.py') and not f.startswith('_')]
            print(f"   ✅ {desc}: {len(files)} 个文件")
        else:
            print(f"   ❌ {desc}: 目录不存在")

if __name__ == '__main__':
    main()
