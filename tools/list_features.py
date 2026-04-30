#!/usr/bin/env python3
"""
NASTool 功能清单生成器
列出所有190个功能模块
"""
import os
import sys
import json

PROJECT_ROOT = 'D:\\project\\nastool7'
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools'))

def list_all_features():
    """列出所有功能模块"""
    import sys
    sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools'))
    
    from feature_manager import FeatureManager
    
    manager = FeatureManager()
    
    # 按类别分组
    categories = {
        'checkers': {'name': '检测器', 'items': manager.checkers},
        'adapters': {'name': '适配器', 'items': manager.adapters},
        'fixes': {'name': '修复引擎', 'items': manager.fixes},
        'reporters': {'name': '报告器', 'items': manager.reporters},
        'cli_commands': {'name': 'CLI命令', 'items': manager.cli_commands},
        'monitors': {'name': '监控器', 'items': manager.monitors},
        'detectors': {'name': '探测器', 'items': manager.detectors},
        'diagnostics': {'name': '诊断器', 'items': manager.diagnostics},
    }
    
    # 输出清单
    print("📋 NASTool 功能清单")
    print("="*70)
    print(f"总功能数: {sum(len(cat['items']) for cat in categories.values())}")
    print("="*70)
    
    total_count = 0
    for cat_key, cat_info in categories.items():
        items = cat_info['items']
        if not items:
            continue
        
        print(f"\n📁 {cat_info['name']} ({len(items)}个)")
        print("-" * 50)
        
        for i, item in enumerate(sorted(items, key=lambda x: x.get('id', '')), 1):
            status = "✅" if item.get('available', False) else "❌"
            total_count += 1
            item_id = item.get('id', '未知')
            print(f"   {total_count:3d}. {status} {item_id}")
            item_name = item.get('name', '')
            if item_name and item_name != item_id:
                print(f"      └─ {item_name}")
            description = item.get('description', '')
            if description:
                print(f"         {description[:50]}...")
    
    # 生成JSON报告
    report_data = {
        'total': total_count,
        'categories': {}
    }
    
    for cat_key, cat_info in categories.items():
        report_data['categories'][cat_key] = {
            'name': cat_info['name'],
            'count': len(cat_info['items']),
            'items': cat_info['items']
        }
    
    report_path = os.path.join(PROJECT_ROOT, 'feature_list.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📝 详细报告已保存到: {report_path}")
    
    return report_data

def main():
    """主函数"""
    list_all_features()

if __name__ == '__main__':
    main()
