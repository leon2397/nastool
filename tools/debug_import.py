#!/usr/bin/env python3
"""调试导入问题"""
import sys
import os

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# 添加所有路径
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-core'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool-core'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools'))

print("当前sys.path:")
for i, p in enumerate(sys.path[:10]):
    print(f"  {i}: {p}")

# 测试导入
test_modules = [
    'nastool_core.checks.ai.ascend_checker',
    'nastool_core.checks.network.dns_diagnostic',
    'nastool_core.checks.network.network_quality_checker',
    'nastool_core.checks.network.network_status_checker'
]

print("\n测试导入:")
for mod in test_modules:
    try:
        module = __import__(mod, fromlist=[''])
        print(f"✅ {mod}: 导入成功")
        # 检查类名
        for attr_name in dir(module):
            if attr_name.endswith('Checker') or attr_name.endswith('Diagnostic'):
                attr = getattr(module, attr_name)
                if isinstance(attr, type):
                    print(f"   类: {attr_name}")
    except Exception as e:
        print(f"❌ {mod}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
