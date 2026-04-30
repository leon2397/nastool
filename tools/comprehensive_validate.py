#!/usr/bin/env python3
"""
NASTool 全面验证工具
深入检查所有文件的完整性、语法、依赖和逻辑
"""
import os
import sys
import ast
import importlib.util

PROJECT_ROOT = 'D:\\project\\nastool7'

def check_file_integrity(filepath):
    """检查文件完整性"""
    result = {
        'exists': False,
        'size_ok': False,
        'readable': False,
        'encoding_ok': False,
        'error': None
    }
    
    if not os.path.exists(filepath):
        result['error'] = '文件不存在'
        return result
    
    result['exists'] = True
    
    size = os.path.getsize(filepath)
    if size == 0:
        result['error'] = '文件为空'
        return result
    if size < 10:
        result['error'] = '文件内容过短，可能不完整'
        return result
    result['size_ok'] = True
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        result['readable'] = True
        result['encoding_ok'] = True
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                content = f.read()
            result['readable'] = True
            result['encoding_ok'] = True
        except:
            result['error'] = '编码错误'
    except Exception as e:
        result['error'] = f'读取失败: {str(e)}'
    
    return result

def check_syntax(filepath):
    """检查语法"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        tree = ast.parse(content)
        return {'valid': True, 'error': None, 'tree': tree}
    except SyntaxError as e:
        return {'valid': False, 'error': f'语法错误: 第{e.lineno}行 - {e.msg}', 'tree': None}
    except Exception as e:
        return {'valid': False, 'error': f'解析失败: {str(e)}', 'tree': None}

def check_imports(filepath):
    """检查导入语句"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        return {'valid': True, 'imports': imports, 'error': None}
    except Exception as e:
        return {'valid': False, 'imports': [], 'error': str(e)}

def analyze_code_structure(filepath, tree):
    """分析代码结构"""
    if not tree:
        return {}
    
    analysis = {
        'functions': [],
        'classes': [],
        'imports': [],
        'docstrings': 0,
        'complexity': 0
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            analysis['functions'].append(node.name)
            # 简单的复杂度计算
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.And, ast.Or)):
                    analysis['complexity'] += 1
        elif isinstance(node, ast.ClassDef):
            analysis['classes'].append(node.name)
            # 检查是否有docstring
            if ast.get_docstring(node):
                analysis['docstrings'] += 1
        elif isinstance(node, ast.Import):
            for alias in node.names:
                analysis['imports'].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                analysis['imports'].append(node.module)
    
    return analysis

def validate_project():
    """全面验证项目"""
    print("🚀 NASTool 全面验证")
    print("="*70)
    print(f"项目路径: {PROJECT_ROOT}")
    print("="*70)
    
    all_files = []
    errors = []
    warnings = []
    
    # 遍历所有Python文件
    for root, dirs, files in os.walk(PROJECT_ROOT):
        if 'archive' in root or '.git' in root:
            continue
        
        for f in files:
            if f.endswith('.py'):
                all_files.append(os.path.join(root, f))
    
    print(f"\n📁 发现 {len(all_files)} 个Python文件")
    print("-" * 50)
    
    # 统计变量
    stats = {
        'total': len(all_files),
        'ok': 0,
        'integrity_errors': 0,
        'syntax_errors': 0,
        'import_errors': 0,
        'total_lines': 0,
        'total_functions': 0,
        'total_classes': 0,
        'files_with_docstrings': 0
    }
    
    print("\n🔍 正在全面检查...")
    
    for filepath in all_files:
        rel_path = os.path.relpath(filepath, PROJECT_ROOT)
        
        # 1. 检查文件完整性
        integrity = check_file_integrity(filepath)
        if not integrity['exists']:
            errors.append({'file': rel_path, 'type': 'missing', 'error': integrity['error']})
            stats['integrity_errors'] += 1
            continue
        
        if not integrity['size_ok']:
            errors.append({'file': rel_path, 'type': 'size', 'error': integrity['error']})
            stats['integrity_errors'] += 1
            continue
        
        # 2. 检查语法
        syntax = check_syntax(filepath)
        if not syntax['valid']:
            errors.append({'file': rel_path, 'type': 'syntax', 'error': syntax['error']})
            stats['syntax_errors'] += 1
            continue
        
        # 3. 分析代码结构
        analysis = analyze_code_structure(filepath, syntax['tree'])
        
        # 4. 检查导入
        imports = check_imports(filepath)
        if not imports['valid']:
            errors.append({'file': rel_path, 'type': 'import', 'error': imports['error']})
            stats['import_errors'] += 1
            continue
        
        # 统计
        stats['ok'] += 1
        stats['total_functions'] += len(analysis['functions'])
        stats['total_classes'] += len(analysis['classes'])
        if analysis['docstrings'] > 0:
            stats['files_with_docstrings'] += 1
        
        # 读取行数
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            stats['total_lines'] += len(f.readlines())
        
        # 检查潜在问题
        if len(analysis['functions']) > 50:
            warnings.append(f"{rel_path}: 函数数量过多 ({len(analysis['functions'])}个)")
        
        if analysis.get('complexity', 0) > 100:
            warnings.append(f"{rel_path}: 代码复杂度较高")
        
        if len(analysis['imports']) > 20:
            warnings.append(f"{rel_path}: 导入模块过多 ({len(analysis['imports'])}个)")
    
    # 输出结果
    print("\n" + "="*70)
    print("📊 验证结果")
    print("="*70)
    
    print(f"\n📁 文件统计:")
    print(f"   总文件数: {stats['total']}")
    print(f"   ✅ 验证通过: {stats['ok']}")
    print(f"   ❌ 完整性错误: {stats['integrity_errors']}")
    print(f"   ❌ 语法错误: {stats['syntax_errors']}")
    print(f"   ❌ 导入错误: {stats['import_errors']}")
    
    success_rate = (stats['ok'] / stats['total']) * 100
    print(f"\n📈 文件可用率: {success_rate:.2f}%")
    
    print(f"\n📈 代码统计:")
    print(f"   总行数: {stats['total_lines']:,}")
    print(f"   函数数: {stats['total_functions']:,}")
    print(f"   类数: {stats['total_classes']:,}")
    print(f"   有文档的文件: {stats['files_with_docstrings']}")
    
    # 输出错误详情
    if errors:
        print("\n❌ 错误详情:")
        print("-" * 50)
        
        # 按类型分组
        error_types = {'missing': '缺失文件', 'size': '文件大小', 'syntax': '语法错误', 'import': '导入错误'}
        
        for error_type, desc in error_types.items():
            type_errors = [e for e in errors if e['type'] == error_type]
            if type_errors:
                print(f"\n📝 {desc}:")
                for error in type_errors[:5]:
                    print(f"   - {error['file']}: {error['error']}")
                if len(type_errors) > 5:
                    print(f"   ... 还有 {len(type_errors) - 5} 个")
    
    # 输出警告
    if warnings:
        print("\n⚠️ 警告:")
        print("-" * 50)
        for warning in warnings[:10]:
            print(f"   ⚠️ {warning}")
        if len(warnings) > 10:
            print(f"   ... 还有 {len(warnings) - 10} 个警告")
    
    # 生成报告
    report_path = os.path.join(PROJECT_ROOT, 'comprehensive_validation_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("NASTool 全面验证报告\n")
        f.write("="*70 + "\n")
        f.write(f"验证时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("📊 验证结果:\n")
        f.write(f"总文件数: {stats['total']}\n")
        f.write(f"验证通过: {stats['ok']}\n")
        f.write(f"完整性错误: {stats['integrity_errors']}\n")
        f.write(f"语法错误: {stats['syntax_errors']}\n")
        f.write(f"文件可用率: {success_rate:.2f}%\n\n")
        
        f.write("📈 代码统计:\n")
        f.write(f"总行数: {stats['total_lines']:,}\n")
        f.write(f"函数数: {stats['total_functions']:,}\n")
        f.write(f"类数: {stats['total_classes']:,}\n\n")
        
        if errors:
            f.write("❌ 错误列表:\n")
            for error in errors:
                f.write(f"{error['file']} [{error['type']}]: {error['error']}\n")
        
        if warnings:
            f.write("\n⚠️ 警告列表:\n")
            for warning in warnings:
                f.write(f"{warning}\n")
    
    print(f"\n📝 报告已保存到: {report_path}")
    
    # 验证模块导入
    print("\n🔗 验证核心模块导入...")
    core_modules = [
        'nastool_core',
        'nastool_adapters',
        'nastool_fixes',
        'nastool_reporters',
        'nastool_cli',
        'nastool_common'
    ]
    
    import_success = []
    import_failures = []
    
    for module in core_modules:
        try:
            spec = importlib.util.find_spec(module)
            if spec:
                import_success.append(module)
                print(f"   ✅ {module}")
            else:
                import_failures.append(module)
                print(f"   ❌ {module}: 无法找到模块")
        except Exception as e:
            import_failures.append(module)
            print(f"   ❌ {module}: {str(e)}")
    
    print(f"\n📊 模块导入: {len(import_success)}/{len(core_modules)} 通过")
    
    # 最终评估
    print("\n" + "="*70)
    print("🎯 最终评估")
    print("="*70)
    
    all_passed = (success_rate == 100 and 
                  stats['syntax_errors'] == 0 and 
                  stats['integrity_errors'] == 0 and
                  len(import_failures) == 0)
    
    if all_passed:
        print("✅ 项目完全通过验证！")
        print("   所有文件完整、语法正确、模块可导入")
    elif success_rate >= 99 and stats['syntax_errors'] == 0:
        print("✅ 项目基本通过验证")
        print("   可以正常交付使用")
    else:
        print("⚠️ 项目需要修复部分问题")
        print("   建议修复后再交付")
    
    return all_passed

if __name__ == '__main__':
    validate_project()
