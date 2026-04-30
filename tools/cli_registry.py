#!/usr/bin/env python3
"""
NASTool CLI命令注册表
整合所有CLI命令
"""
import os
import sys

# 添加CLI模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-cli'))

class CLICommandRegistry:
    """CLI命令注册表"""
    
    def __init__(self):
        self._commands = {}
        self._categories = {
            'device': '设备管理',
            'diagnose': '诊断测试',
            'batch': '批量操作',
            'compare': '报告对比',
            'jetson': 'Jetson管理',
            'other': '其他命令'
        }
        self._discover_commands()
    
    def _discover_commands(self):
        """自动发现所有CLI命令"""
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'nastool-v4.0.0', 'nastool-cli', 'nastool_cli'
        )
        
        # 定义文件到类别的映射
        file_to_category = {
            'device.py': 'device',
            'diagnose.py': 'diagnose',
            'batch.py': 'batch',
            'compare.py': 'compare',
            'jetson_install.py': 'jetson',
            'jetson_patch.py': 'jetson',
            'main.py': 'other',
            'main_v4.py': 'other',
            'ws_client.py': 'other'
        }
        
        # 扫描主目录
        for filename in os.listdir(base_path):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                category = file_to_category.get(filename, 'other')
                self._register_command(category, module_name)
        
        # 扫描commands子目录
        commands_path = os.path.join(base_path, 'commands')
        if os.path.exists(commands_path):
            for filename in os.listdir(commands_path):
                if filename.endswith('.py') and not filename.startswith('_'):
                    module_name = f"commands.{filename[:-3]}"
                    category = file_to_category.get(filename, 'other')
                    self._register_command(category, module_name)
    
    def _register_command(self, category, module_name):
        """注册单个命令"""
        command_id = f"{category}.{module_name}"
        
        try:
            module = __import__(f"nastool_cli.{module_name}", fromlist=[''])
            
            self._commands[command_id] = {
                'id': command_id,
                'category': category,
                'category_name': self._categories.get(category, '其他'),
                'module': f"nastool_cli.{module_name}",
                'name': module_name.replace('_', ' ').title(),
                'available': True
            }
        except Exception as e:
            self._commands[command_id] = {
                'id': command_id,
                'category': category,
                'category_name': self._categories.get(category, '其他'),
                'module': f"nastool_cli.{module_name}",
                'name': module_name.replace('_', ' ').title(),
                'available': False,
                'error': str(e)
            }
    
    def get_all_commands(self):
        """获取所有命令"""
        return list(self._commands.values())
    
    def get_command_count(self):
        """获取命令数量"""
        counts = {cat: 0 for cat in self._categories.keys()}
        counts['total'] = 0
        
        for cmd in self._commands.values():
            if cmd['available']:
                counts[cmd['category']] += 1
                counts['total'] += 1
        
        return counts

def main():
    """主函数"""
    print("="*60)
    print("💻 NASTool CLI命令注册表")
    print("="*60)
    
    registry = CLICommandRegistry()
    counts = registry.get_command_count()
    
    print("\n📊 CLI命令统计:")
    for cat_id, cat_name in registry._categories.items():
        print(f"   {cat_name}: {counts.get(cat_id, 0)} 个")
    print(f"   {'总计':　<10}: {counts['total']} 个")
    
    print("\n" + "="*60)
    print("🔍 可用命令列表")
    print("="*60)
    
    current_category = None
    for cmd in sorted(registry.get_all_commands(), key=lambda x: (x['category'], x['name'])):
        if cmd['category'] != current_category:
            current_category = cmd['category']
            print(f"\n【{registry._categories[current_category]}】")
        
        status = "✅" if cmd['available'] else "❌"
        print(f"  {status} {cmd['name']}")

if __name__ == '__main__':
    main()
