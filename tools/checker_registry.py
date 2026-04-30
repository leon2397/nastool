#!/usr/bin/env python3
"""
NASTool 检测注册表
将所有检测功能统一注册和管理
"""
import os
import sys
import importlib
from typing import Dict, List, Any, Optional

class CheckerRegistry:
    """检测器注册表"""

    def __init__(self):
        self._checkers: Dict[str, Dict[str, Any]] = {}
        self._categories = {
            'ai': 'AI/机器学习检测',
            'nas': 'NAS服务检测',
            'network': '网络检测',
            'security': '安全检测',
            'storage': '存储检测',
            'system': '系统检测',
            'usb': 'USB检测'
        }
        self._discover_checkers()

    def _discover_checkers(self):
        """自动发现并注册所有检测器"""
        # 定义多个检测器目录
        base_paths = [
            # 当前版本检测器
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'nastool-core', 'nastool_core', 'checks'
            ),
            # v4.0.0版本检测器（之前被遗漏的）
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'nastool-v4.0.0', 'nastool-core', 'nastool_core', 'checks'
            )
        ]

        # 添加路径到sys.path以便导入
        for base_path in base_paths:
            if os.path.exists(base_path):
                sys.path.insert(0, os.path.dirname(os.path.dirname(base_path)))

        for base_path in base_paths:
            if not os.path.exists(base_path):
                continue

            for category in self._categories.keys():
                category_path = os.path.join(base_path, category)
                if not os.path.exists(category_path):
                    continue

                for filename in os.listdir(category_path):
                    # 支持所有Python文件（排除特殊文件）
                    if filename.endswith('.py') and not filename.startswith('_'):
                        module_name = filename[:-3]
                        checker_id = f"{category}.{module_name}"
                        
                        # 跳过重复注册
                        if checker_id not in self._checkers:
                            self._register_checker(category, module_name)

    def _register_checker(self, category: str, module_name: str):
        """注册单个检测器"""
        checker_id = f"{category}.{module_name}"

        try:
            # 动态导入检测器
            module_path = f"nastool_core.checks.{category}.{module_name}"

            # 获取检测器类名
            class_name = ''.join([
                word.capitalize()
                for word in module_name.replace('-', '_').split('_')
            ]) + 'Checker'

            self._checkers[checker_id] = {
                'id': checker_id,
                'category': category,
                'category_name': self._categories[category],
                'module': module_path,
                'class': class_name,
                'name': module_name.replace('_', ' ').title(),
                'available': True
            }
        except Exception as e:
            self._checkers[checker_id] = {
                'id': checker_id,
                'category': category,
                'category_name': self._categories[category],
                'module': module_path,
                'class': class_name,
                'name': module_name.replace('_', ' ').title(),
                'available': False,
                'error': str(e)
            }

    def list_checkers(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有或指定类别的检测器"""
        if category:
            return [c for c in self._checkers.values() if c['category'] == category]
        return list(self._checkers.values())

    def get_checker(self, checker_id: str) -> Optional[Dict[str, Any]]:
        """获取指定检测器信息"""
        return self._checkers.get(checker_id)

    def get_checker_count(self) -> Dict[str, int]:
        """获取各类别检测器数量"""
        counts = {cat: 0 for cat in self._categories.keys()}
        counts['total'] = 0

        for checker in self._checkers.values():
            if checker['available']:
                counts[checker['category']] += 1
                counts['total'] += 1

        return counts

    def get_all_categories(self) -> Dict[str, str]:
        """获取所有类别信息"""
        return self._categories.copy()

def main():
    """主函数 - 显示检测器注册表"""
    print("="*60)
    print("📋 NASTool 检测器注册表")
    print("="*60)

    registry = CheckerRegistry()

    # 显示各类别统计
    counts = registry.get_checker_count()
    print("\n📊 检测器统计:")
    for cat_id, cat_name in registry.get_all_categories().items():
        print(f"   {cat_name}: {counts.get(cat_id, 0)} 个")
    print(f"   {'总计':　<10}: {counts['total']} 个")

    # 显示可用检测器列表
    print("\n" + "="*60)
    print("🔍 可用检测器列表")
    print("="*60)

    current_category = None
    for checker in sorted(registry.list_checkers(), key=lambda x: (x['category'], x['name'])):
        if checker['category'] != current_category:
            current_category = checker['category']
            print(f"\n【{registry.get_all_categories()[current_category]}】")

        status = "✅" if checker['available'] else "❌"
        print(f"  {status} {checker['name']}")

if __name__ == '__main__':
    main()
