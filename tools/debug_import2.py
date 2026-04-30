#!/usr/bin/env python3
"""详细调试导入问题"""
import sys
import os

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# 添加所有路径 - 当前版本nastool-core必须在v4.0.0版本前面！
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-core'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool-core'))

print("当前sys.path (前5个):")
for i, p in enumerate(sys.path[:5]):
    print(f"  {i}: {p}")

# 检查文件是否存在
files_to_check = [
    ('ai', 'ascend_checker'),
    ('network', 'dns_diagnostic'),
    ('network', 'network_quality_checker'),
    ('network', 'network_status_checker')
]

print("\n检查文件是否存在:")
for category, module_name in files_to_check:
    path1 = os.path.join(PROJECT_ROOT, 'nastool-core', 'nastool_core', 'checks', category, f'{module_name}.py')
    path2 = os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool_core', 'checks', category, f'{module_name}.py')
    print(f"\n  {category}.{module_name}:")
    print(f"    当前版本: {'存在' if os.path.exists(path1) else '不存在'} - {path1}")
    print(f"    v4.0.0版本: {'存在' if os.path.exists(path2) else '不存在'} - {path2}")

# 测试实际导入
print("\n\n测试实际导入:")
test_modules = [
    'nastool_core.checks.ai.ascend_checker',
    'nastool_core.checks.network.dns_diagnostic',
    'nastool_core.checks.network.network_quality_checker',
    'nastool_core.checks.network.network_status_checker'
]

for mod in test_modules:
    print(f"\n  尝试导入: {mod}")
    try:
        # 尝试importlib
        import importlib
        module = importlib.import_module(mod)
        print(f"    ✅ importlib成功")
        print(f"    模块文件: {module.__file__}")
    except Exception as e:
        print(f"    ❌ importlib失败: {type(e).__name__}: {e}")
    
    try:
        # 尝试__import__
        module = __import__(mod, fromlist=[''])
        print(f"    ✅ __import__成功")
        print(f"    模块文件: {module.__file__}")
    except Exception as e:
        print(f"    ❌ __import__失败: {type(e).__name__}: {e}")
