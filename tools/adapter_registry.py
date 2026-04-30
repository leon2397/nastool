#!/usr/bin/env python3
"""
NASTool 适配器注册表
将所有硬件适配器统一注册和管理
"""
import os
import sys
import importlib
from typing import Dict, List, Any, Optional

# 添加适配器模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-adapters'))

class AdapterRegistry:
    """适配器注册表"""

    def __init__(self):
        self._adapters: Dict[str, Dict[str, Any]] = {}
        self._categories = {
            'ascend': '昇腾适配器',
            'jetson': 'Jetson适配器',
            'synology': '群晖适配器',
            'qnap': '威联通适配器',
            'rockchip': '瑞芯微适配器',
            'sophon': '算能适配器',
            'generic': '通用适配器',
            'other': '其他适配器'
        }
        self._discover_adapters()

    def _discover_adapters(self):
        """自动发现并注册所有适配器"""
        # 定义多个适配器目录
        base_paths = [
            # 当前版本适配器
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'nastool-adapters', 'nastool_adapters'
            ),
            # v4.0.0版本适配器（之前被遗漏的）
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'nastool-v4.0.0', 'nastool-adapters', 'nastool_adapters'
            )
        ]

        # 添加路径到sys.path
        for base_path in base_paths:
            if os.path.exists(base_path):
                sys.path.insert(0, os.path.dirname(os.path.dirname(base_path)))

        # 定义文件名到类别的映射
        filename_to_category = {
            'synology': 'synology',
            'synology_notifier': 'synology',
            'synology_scheduler': 'synology',
            'qnap': 'qnap',
            'rockchip': 'rockchip',
            'sophon': 'sophon',
            'generic': 'generic',
            'nvidia_jetson': 'jetson',
            'hw_jet': 'jetson',
            'ascend': 'ascend',
            'ssh_detector': 'other',
            'http_detector': 'other',
            'http_backend': 'other',
            'adb_adapter': 'other',
            'benchmark': 'other',
            'detector': 'other',
            'logger': 'other',
            'mock_adapter': 'other',
            'nas_client': 'other',
            'nastool_api_client': 'other',
            'relay_detector': 'other',
            'reporter': 'other'
        }

        for base_path in base_paths:
            if not os.path.exists(base_path):
                continue

            # 遍历适配器文件
            for filename in os.listdir(base_path):
                if filename.endswith('.py') and not filename.startswith('_') and filename != 'base.py':
                    module_name = filename[:-3]
                    adapter_id = f"{category}.{module_name}" if 'category' in locals() else f"other.{module_name}"
                    
                    # 跳过重复注册
                    if adapter_id in self._adapters:
                        continue
                    
                    # 根据文件名确定类别
                    category = filename_to_category.get(module_name, 'other')
                    self._register_adapter(category, module_name)

            # 遍历子目录（ascend, jetson, utils）
            for sub_dir in ['ascend', 'jetson', 'utils']:
                sub_dir_path = os.path.join(base_path, sub_dir)
                if os.path.exists(sub_dir_path):
                    for filename in os.listdir(sub_dir_path):
                        if filename.endswith('.py') and not filename.startswith('_'):
                            module_name = filename[:-3]
                            adapter_id = f"{sub_dir}.{module_name}"
                            
                            # 跳过重复注册
                            if adapter_id in self._adapters:
                                continue
                            
                            # 确定类别
                            if sub_dir in ['ascend', 'jetson']:
                                category = sub_dir
                            else:
                                category = 'other'
                            
                            self._register_adapter(category, f"{sub_dir}.{module_name}")

    def _register_adapter(self, category: str, module_name: str):
        """注册单个适配器"""
        adapter_id = f"{category}.{module_name}"

        try:
            # 动态导入模块
            if category in ['ascend', 'jetson']:
                module_path = f"nastool_adapters.{category}.{module_name}"
            else:
                module_path = f"nastool_adapters.{module_name}"

            # 获取适配器类名
            class_name = ''.join([
                word.capitalize()
                for word in module_name.replace('-', '_').split('_')
            ])

            self._adapters[adapter_id] = {
                'id': adapter_id,
                'category': category,
                'category_name': self._categories.get(category, '其他'),
                'module': module_path,
                'class': class_name,
                'name': module_name.replace('_', ' ').title(),
                'available': True
            }
        except Exception as e:
            self._adapters[adapter_id] = {
                'id': adapter_id,
                'category': category,
                'category_name': self._categories.get(category, '其他'),
                'module': module_path,
                'class': class_name,
                'name': module_name.replace('_', ' ').title(),
                'available': False,
                'error': str(e)
            }

    def list_adapters(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有或指定类别的适配器"""
        if category:
            return [a for a in self._adapters.values() if a['category'] == category]
        return list(self._adapters.values())

    def get_adapter(self, adapter_id: str) -> Optional[Dict[str, Any]]:
        """获取指定适配器信息"""
        return self._adapters.get(adapter_id)

    def get_adapter_count(self) -> Dict[str, int]:
        """获取各类别适配器数量"""
        counts = {cat: 0 for cat in self._categories.keys()}
        counts['total'] = 0

        for adapter in self._adapters.values():
            if adapter['available']:
                counts[adapter['category']] += 1
                counts['total'] += 1

        return counts

    def get_all_categories(self) -> Dict[str, str]:
        """获取所有类别信息"""
        return self._categories.copy()

def main():
    """主函数 - 显示适配器注册表"""
    print("="*60)
    print("🔌 NASTool 适配器注册表")
    print("="*60)

    registry = AdapterRegistry()

    # 显示各类别统计
    counts = registry.get_adapter_count()
    print("\n📊 适配器统计:")
    for cat_id, cat_name in registry.get_all_categories().items():
        print(f"   {cat_name}: {counts.get(cat_id, 0)} 个")
    print(f"   {'总计':　<10}: {counts['total']} 个")

    # 显示可用适配器列表
    print("\n" + "="*60)
    print("🔍 可用适配器列表")
    print("="*60)

    current_category = None
    for adapter in sorted(registry.list_adapters(), key=lambda x: (x['category'], x['name'])):
        if adapter['category'] != current_category:
            current_category = adapter['category']
            print(f"\n【{registry.get_all_categories()[current_category]}】")

        status = "✅" if adapter['available'] else "❌"
        print(f"  {status} {adapter['name']}")

if __name__ == '__main__':
    main()
