#!/usr/bin/env python3
"""
NASTool 文件可用性严格验证工具
验证每个文件的语法正确性和结构完整性
"""
import os
import sys
import ast

PROJECT_ROOT = 'D:\\project\\nastool7'

def validate_file_structure(filepath):
    """验证文件结构"""
    result = {
        'path': filepath,
        'exists': False,
        'readable': False,
        'syntax_valid': False,
        'size': 0,
        'line_count': 0,
        'functions': 0,
        'classes': 0,
        'error': None
    }
    
    # 1. 检查文件是否存在
    if not os.path.exists(filepath):
        result['error'] = '文件不存在'
        return result
    
    result['exists'] = True
    result['size'] = os.path.getsize(filepath)
    
    # 2. 检查文件大小
    if result['size'] == 0:
        result['error'] = '文件为空'
        return result
    
    # 3. 尝试读取文件
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        result['readable'] = True
        result['line_count'] = len(content.split('\n'))
        
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                content = f.read()
            result['readable'] = True
            result['line_count'] = len(content.split('\n'))
        except:
            result['error'] = '编码错误，无法读取'
            return result
    except Exception as e:
        result['error'] = f'读取错误: {str(e)}'
        return result
    
    # 4. 语法检查（只解析，不执行）
    try:
        tree = ast.parse(content)
        result['syntax_valid'] = True
        
        # 统计函数和类
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                result['functions'] += 1
            elif isinstance(node, ast.ClassDef):
                result['classes'] += 1
                
    except SyntaxError as e:
        result['error'] = f'语法错误: {e.msg} 第{e.lineno}行'
        return result
    except Exception as e:
        result['error'] = f'解析错误: {str(e)}'
        return result
    
    return result

def validate_project():
    """验证整个项目"""
    print("🚀 NASTool 文件可用性严格验证")
    print("="*70)
    print(f"项目路径: {PROJECT_ROOT}")
    print("="*70)
    
    all_files = []
    errors = []
    empty_files = []
    syntax_errors = []
    
    # 遍历所有Python文件（排除archive目录）
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # 跳过不需要检查的目录
        if 'archive' in root or '.git' in root:
            continue
        
        # 跳过隐藏目录
        parts = root.split(os.sep)
        if any(p.startswith('.') for p in parts):
            continue
        
        for f in files:
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                all_files.append(filepath)
    
    print(f"\n📁 发现 {len(all_files)} 个Python文件（排除archive）")
    print("-" * 50)
    
    # 逐个验证
    valid_count = 0
    total_functions = 0
    total_classes = 0
    total_lines = 0
    
    print("\n🔍 正在验证文件...")
    
    for i, filepath in enumerate(all_files, 1):
        result = validate_file_structure(filepath)
        
        if result['syntax_valid']:
            valid_count += 1
            total_functions += result['functions']
            total_classes += result['classes']
            total_lines += result['line_count']
        else:
            rel_path = os.path.relpath(filepath, PROJECT_ROOT)
            errors.append({
                'path': rel_path,
                'error': result['error'],
                'type': 'syntax' if '语法错误' in result['error'] else 'other'
            })
            
            if result['error'] == '文件为空':
                empty_files.append(rel_path)
            elif '语法错误' in result['error']:
                syntax_errors.append(rel_path)
    
    # 输出结果
    print("\n" + "="*70)
    print("📊 验证结果")
    print("="*70)
    print(f"总文件数: {len(all_files)}")
    print(f"✅ 语法正确: {valid_count}")
    print(f"❌ 语法错误: {len(syntax_errors)}")
    print(f"📭 空文件: {len(empty_files)}")
    print(f"🔴 其他错误: {len(errors) - len(syntax_errors) - len(empty_files)}")
    
    success_rate = (valid_count / len(all_files)) * 100
    print(f"\n📈 文件可用率: {success_rate:.2f}%")
    
    # 代码统计
    print("\n📈 代码统计")
    print("-" * 50)
    print(f"总行数: {total_lines:,}")
    print(f"函数数: {total_functions:,}")
    print(f"类数: {total_classes:,}")
    
    # 输出错误详情
    if errors:
        print("\n❌ 错误详情:")
        print("-" * 50)
        
        # 语法错误
        if syntax_errors:
            print("\n📝 语法错误:")
            for path in syntax_errors[:10]:
                print(f"   - {path}")
            if len(syntax_errors) > 10:
                print(f"   ... 还有 {len(syntax_errors) - 10} 个")
        
        # 空文件
        if empty_files:
            print("\n📭 空文件:")
            for path in empty_files[:10]:
                print(f"   - {path}")
            if len(empty_files) > 10:
                print(f"   ... 还有 {len(empty_files) - 10} 个")
    
    # 生成报告
    report_path = os.path.join(PROJECT_ROOT, 'file_validation_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("NASTool 文件可用性验证报告\n")
        f.write("="*70 + "\n")
        f.write(f"验证时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\n📊 验证结果:\n")
        f.write(f"总文件数: {len(all_files)}\n")
        f.write(f"语法正确: {valid_count}\n")
        f.write(f"语法错误: {len(syntax_errors)}\n")
        f.write(f"空文件: {len(empty_files)}\n")
        f.write(f"文件可用率: {success_rate:.2f}%\n")
        f.write("\n📈 代码统计:\n")
        f.write(f"总行数: {total_lines:,}\n")
        f.write(f"函数数: {total_functions:,}\n")
        f.write(f"类数: {total_classes:,}\n")
        
        if errors:
            f.write("\n❌ 错误列表:\n")
            for error in errors:
                f.write(f"{error['path']}: {error['error']}\n")
    
    print(f"\n📝 报告已保存到: {report_path}")
    
    # 返回状态
    return success_rate >= 99 and len(syntax_errors) == 0

if __name__ == '__main__':
    success = validate_project()
    
    if success:
        print("\n✅ 项目文件验证通过！")
    else:
        print("\n❌ 项目文件验证未通过，请修复错误")
        sys.exit(1)
