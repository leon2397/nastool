#!/usr/bin/env python3
"""
NASTool 修复引擎注册表
整合所有修复功能
"""
import os
import sys

# 添加修复模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-fixes'))

class FixRegistry:
    """修复引擎注册表"""
    
    def __init__(self):
        self._fixes = {}
        self._categories = {
            'network': '网络修复',
            'security': '安全修复',
            'storage': '存储修复',
            'system': '系统修复',
            'ai': 'AI相关修复'
        }
        self._discover_fixes()
    
    def _discover_fixes(self):
        """自动发现所有修复功能"""
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'nastool-v4.0.0', 'nastool-fixes', 'nastool_fixes'
        )
        
        # 遍历修复模块
        for category in ['network', 'security', 'storage', 'system', 'ai']:
            category_path = os.path.join(base_path, category)
            if os.path.exists(category_path):
                for filename in os.listdir(category_path):
                    if filename.endswith('.py') and not filename.startswith('_'):
                        module_name = filename[:-3]
                        self._register_fix(category, module_name)
    
    def _register_fix(self, category, module_name):
        """注册单个修复功能"""
        fix_id = f"{category}.{module_name}"
        
        try:
            module = __import__(f"nastool_fixes.{category}.{module_name}", fromlist=[''])
            
            # 获取修复类
            fix_class = None
            for attr_name in dir(module):
                if attr_name.endswith('Fix') or attr_name.endswith('Config'):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type):
                        fix_class = attr
                        break
            
            if fix_class:
                self._fixes[fix_id] = {
                    'id': fix_id,
                    'category': category,
                    'category_name': self._categories.get(category, '其他'),
                    'module': module.__name__,
                    'class': fix_class.__name__,
                    'name': module_name.replace('_', ' ').title(),
                    'available': True
                }
            else:
                # 函数式修复
                self._fixes[fix_id] = {
                    'id': fix_id,
                    'category': category,
                    'category_name': self._categories.get(category, '其他'),
                    'module': module.__name__,
                    'class': None,
                    'name': module_name.replace('_', ' ').title(),
                    'available': True
                }
        except Exception as e:
            self._fixes[fix_id] = {
                'id': fix_id,
                'category': category,
                'category_name': self._categories.get(category, '其他'),
                'module': f"nastool_fixes.{category}.{module_name}",
                'class': None,
                'name': module_name.replace('_', ' ').title(),
                'available': False,
                'error': str(e)
            }
    
    def get_all_fixes(self):
        """获取所有修复功能"""
        return list(self._fixes.values())
    
    def get_fixes_by_category(self, category):
        """按类别获取修复功能"""
        return [f for f in self._fixes.values() if f['category'] == category]
    
    def get_category_count(self):
        """获取各类别修复数量"""
        counts = {cat: 0 for cat in self._categories.keys()}
        counts['total'] = 0
        
        for fix in self._fixes.values():
            if fix['available']:
                counts[fix['category']] += 1
                counts['total'] += 1
        
        return counts

def main():
    """主函数"""
    print("="*60)
    print("🔧 NASTool 修复引擎注册表")
    print("="*60)
    
    registry = FixRegistry()
    counts = registry.get_category_count()
    
    print("\n📊 修复功能统计:")
    for cat_id, cat_name in registry._categories.items():
        print(f"   {cat_name}: {counts.get(cat_id, 0)} 个")
    print(f"   {'总计':　<10}: {counts['total']} 个")
    
    print("\n" + "="*60)
    print("🔍 可用修复功能列表")
    print("="*60)
    
    current_category = None
    for fix in sorted(registry.get_all_fixes(), key=lambda x: (x['category'], x['name'])):
        if fix['category'] != current_category:
            current_category = fix['category']
            print(f"\n【{registry._categories[current_category]}】")
        
        status = "✅" if fix['available'] else "❌"
        print(f"  {status} {fix['name']}")

if __name__ == '__main__':
    main()
