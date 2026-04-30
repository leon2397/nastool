#!/usr/bin/env python3
"""测试失败的检测器导入"""
import sys
sys.path.insert(0, 'nastool-core')

# 测试导入
test_modules = [
    'nastool_core.checks.ai.ascend_checker',
    'nastool_core.checks.network.dns_diagnostic',
    'nastool_core.checks.network.network_quality_checker',
    'nastool_core.checks.network.network_status_checker'
]

for mod in test_modules:
    try:
        module = __import__(mod, fromlist=[''])
        print(f"✅ {mod}: 导入成功")
        # 列出模块中的类
        classes = [x for x in dir(module) if isinstance(getattr(module, x), type)]
        print(f"   类: {', '.join(classes)}")
    except Exception as e:
        print(f"❌ {mod}: {e}")
