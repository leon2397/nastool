#!/usr/bin/env python3
"""
NASTool 适配器执行器
将所有27个硬件适配器整合到统一的执行框架中
"""
import os
import sys
import importlib
from typing import Dict, List, Any, Optional

# 添加适配器模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-adapters'))
sys.path.insert(0, os.path.dirname(__file__))

import adapter_registry

class AdapterExecutor:
    """适配器执行器"""

    def __init__(self):
        self._results = []

    def execute_adapter(self, adapter_id: str, device_info: Optional[Dict] = None) -> Dict[str, Any]:
        """执行单个适配器"""
        try:
            category, module_name = adapter_id.split('.', 1)
            
            # 动态导入模块
            if category in ['ascend', 'jetson']:
                module = importlib.import_module(f"nastool_adapters.{category}.{module_name}")
            else:
                module = importlib.import_module(f"nastool_adapters.{module_name}")
            
            # 获取适配器类
            class_name = ''.join([
                word.capitalize()
                for word in module_name.replace('-', '_').split('_')
            ])
            
            adapter_class = getattr(module, class_name, None)
            
            if not adapter_class:
                # 尝试其他类名模式
                for attr_name in dir(module):
                    if attr_name[0].isupper() and isinstance(getattr(module, attr_name), type):
                        adapter_class = getattr(module, attr_name)
                        class_name = attr_name
                        break
            
            if not adapter_class:
                return {
                    'adapter_id': adapter_id,
                    'status': 'error',
                    'message': '无法找到适配器类'
                }
            
            # 创建适配器实例并执行检测
            try:
                adapter = adapter_class()
            except:
                # 尝试无参数构造
                try:
                    adapter = adapter_class.__new__(adapter_class)
                except:
                    return {
                        'adapter_id': adapter_id,
                        'status': 'error',
                        'message': '无法创建适配器实例'
                    }
            
            # 尝试不同的检测方法
            if hasattr(adapter, 'detect'):
                result = adapter.detect(device_info)
            elif hasattr(adapter, 'check'):
                result = adapter.check(device_info)
            elif hasattr(adapter, 'run'):
                result = adapter.run(device_info)
            elif hasattr(adapter, 'info'):
                result = adapter.info()
            else:
                # 返回适配器基本信息
                return {
                    'adapter_id': adapter_id,
                    'status': 'info',
                    'message': f"适配器 {class_name} 已加载",
                    'details': {'class': class_name}
                }
            
            # 处理结果
            if isinstance(result, dict):
                return {
                    'adapter_id': adapter_id,
                    'status': result.get('status', 'info'),
                    'message': result.get('message', ''),
                    'details': result.get('details', {})
                }
            else:
                return {
                    'adapter_id': adapter_id,
                    'status': 'info',
                    'message': str(result),
                    'details': {}
                }
        
        except Exception as e:
            return {
                'adapter_id': adapter_id,
                'status': 'error',
                'message': str(e)
            }

    def execute_category(self, category: str, device_info: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行指定类别的所有适配器"""
        registry = adapter_registry.AdapterRegistry()
        adapters = registry.list_adapters(category)
        
        results = []
        for adapter in adapters:
            if adapter['available']:
                result = self.execute_adapter(adapter['id'], device_info)
                results.append(result)
        
        return results

    def execute_all(self, device_info: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行所有适配器"""
        registry = adapter_registry.AdapterRegistry()
        all_adapters = registry.list_adapters()
        
        results = []
        for adapter in all_adapters:
            if adapter['available']:
                result = self.execute_adapter(adapter['id'], device_info)
                results.append(result)
        
        return results

def main():
    """主函数 - 演示适配器执行器"""
    print("="*60)
    print("🔌 NASTool 适配器执行器")
    print("="*60)

    executor = AdapterExecutor()
    
    # 执行昇腾适配器
    print("\n🔍 正在执行昇腾适配器...")
    results = executor.execute_category('ascend')
    
    for result in results:
        status_icon = {
            'pass': '✅',
            'ok': '✅',
            'warning': '⚠️',
            'fail': '❌',
            'error': '❌',
            'info': '⚪'
        }.get(result['status'], '⚪')
        
        print(f"  {status_icon} {result['adapter_id']}: {result['message']}")

if __name__ == '__main__':
    main()
