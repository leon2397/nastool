#!/usr/bin/env python3
"""
NASTool 文件可用性验证工具
严格验证每个文件是否可以正常导入和使用
"""
import os
import sys
import ast
import importlib.util

PROJECT_ROOT = 'D:\\project\\nastool7'

def validate_python_file(filepath):
    """验证单个Python文件"""
    result = {
        'path': filepath,
        'exists': False,
        'syntax_valid': False,
        'importable': False,
        'size': 0,
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
    
    # 3. 检查语法
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析语法
        ast.parse(content)
        result['syntax_valid'] = True
        
    except SyntaxError as e:
        result['error'] = f'语法错误: {e.msg} 第{e.lineno}行'
        return result
    except UnicodeDecodeError:
        result['error'] = '编码错误，无法读取'
        return result
    except Exception as e:
        result['error'] = f'读取错误: {str(e)}'
        return result
    
    # 4. 尝试导入
    try:
        # 获取模块路径
        rel_path = os.path.relpath(filepath, PROJECT_ROOT)
        module_name = rel_path.replace('\\', '/').replace('.py', '').replace('/', '.')
        
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
                result['importable'] = True
            except Exception as e:
                # 导入失败可能是依赖问题，不是文件本身的问题
                result['importable'] = False
                result['error'] = f'导入失败: {str(e)[:100]}'
        else:
            result['importable'] = False
            result['error'] = '无法创建模块规范'
            
    except Exception as e:
        result['importable'] = False
        result['error'] = f'导入异常: {str(e)[:100]}'
    
    return result

def validate_project():
    """验证整个项目"""
    print("🚀 NASTool 文件可用性严格验证")
    print("="*70)
    print(f"项目路径: {PROJECT_ROOT}")
    print("="*70)
    
    all_files = []
    errors = []
    
    # 遍历所有Python文件
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # 跳过一些目录
        if '.git' in root:
            continue
        
        for f in files:
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                all_files.append(filepath)
    
    print(f"\n📁 发现 {len(all_files)} 个Python文件")
    print("-" * 50)
    
    # 逐个验证
    valid_count = 0
    syntax_errors = 0
    import_errors = 0
    empty_files = 0
    other_errors = 0
    
    print("\n🔍 正在验证文件...")
    
    for filepath in all_files:
        result = validate_python_file(filepath)
        
        if result['syntax_valid'] and result['importable']:
            valid_count += 1
        else:
            rel_path = os.path.relpath(filepath, PROJECT_ROOT)
            errors.append({
                'path': rel_path,
                'error': result['error']
            })
            
            if '语法错误' in result['error']:
                syntax_errors += 1
            elif '导入失败' in result['error']:
                import_errors += 1
            elif '文件为空' in result['error']:
                empty_files += 1
            else:
                other_errors += 1
    
    # 输出结果
    print("\n" + "="*70)
    print("📊 验证结果")
    print("="*70)
    print(f"总文件数: {len(all_files)}")
    print(f"✅ 完全可用: {valid_count}")
    print(f"❌ 语法错误: {syntax_errors}")
    print(f"⚠️ 导入失败: {import_errors}")
    print(f"📭 空文件: {empty_files}")
    print(f"🔴 其他错误: {other_errors}")
    
    success_rate = (valid_count / len(all_files)) * 100
    print(f"\n📈 文件可用率: {success_rate:.2f}%")
    
    # 输出错误详情
    if errors:
        print("\n❌ 错误详情:")
        print("-" * 50)
        
        # 只显示前20个错误
        for i, error in enumerate(errors[:20], 1):
            print(f"   {i}. {error['path']}")
            print(f"      错误: {error['error']}")
        
        if len(errors) > 20:
            print(f"   ... 还有 {len(errors) - 20} 个错误")
    
    # 生成报告
    report_path = os.path.join(PROJECT_ROOT, 'file_validation_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("NASTool 文件可用性验证报告\n")
        f.write("="*70 + "\n")
        f.write(f"验证时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\n📊 验证结果:\n")
        f.write(f"总文件数: {len(all_files)}\n")
        f.write(f"完全可用: {valid_count}\n")
        f.write(f"语法错误: {syntax_errors}\n")
        f.write(f"导入失败: {import_errors}\n")
        f.write(f"空文件: {empty_files}\n")
        f.write(f"文件可用率: {success_rate:.2f}%\n")
        
        if errors:
            f.write("\n❌ 错误列表:\n")
            for error in errors:
                f.write(f"{error['path']}: {error['error']}\n")
    
    print(f"\n📝 报告已保存到: {report_path}")
    
    # 返回状态
    return success_rate >= 95

if __name__ == '__main__':
    success = validate_project()
    
    if success:
        print("\n✅ 项目文件验证通过！")
    else:
        print("\n❌ 项目文件验证未通过，请修复错误")
        sys.exit(1)
