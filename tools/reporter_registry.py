#!/usr/bin/env python3
"""
NASTool 报告器注册表
整合所有报告输出功能（包括PDF）
"""
import os
import sys

# 添加报告模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-reporters'))

class ReporterRegistry:
    """报告器注册表"""
    
    def __init__(self):
        self._reporters = {}
        self._discover_reporters()
    
    def _discover_reporters(self):
        """自动发现所有报告器"""
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'nastool-v4.0.0', 'nastool-reporters', 'nastool_reporters'
        )
        
        for filename in os.listdir(base_path):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                self._register_reporter(module_name)
    
    def _register_reporter(self, module_name):
        """注册单个报告器"""
        try:
            module = __import__(f"nastool_reporters.{module_name}", fromlist=[''])
            
            # 获取报告器类
            reporter_class = None
            class_name = ''.join([word.capitalize() for word in module_name.split('_')]) + 'Reporter'
            
            if hasattr(module, class_name):
                reporter_class = getattr(module, class_name)
            
            if not reporter_class:
                # 尝试其他模式
                for attr_name in dir(module):
                    if attr_name.endswith('Reporter') or attr_name.endswith('Report'):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type):
                            reporter_class = attr
                            class_name = attr_name
                            break
            
            if reporter_class:
                self._reporters[module_name] = {
                    'id': module_name,
                    'name': module_name.replace('_', ' ').title(),
                    'class': class_name,
                    'module': module.__name__,
                    'available': True
                }
            else:
                self._reporters[module_name] = {
                    'id': module_name,
                    'name': module_name.replace('_', ' ').title(),
                    'class': None,
                    'module': module.__name__,
                    'available': True
                }
        except Exception as e:
            self._reporters[module_name] = {
                'id': module_name,
                'name': module_name.replace('_', ' ').title(),
                'class': None,
                'module': f"nastool_reporters.{module_name}",
                'available': False,
                'error': str(e)
            }
    
    def get_all_reporters(self):
        """获取所有报告器"""
        return list(self._reporters.values())
    
    def get_reporter_count(self):
        """获取报告器数量"""
        return len([r for r in self._reporters.values() if r['available']])

def main():
    """主函数"""
    print("="*60)
    print("📝 NASTool 报告器注册表")
    print("="*60)
    
    registry = ReporterRegistry()
    
    print(f"\n📊 报告器数量: {registry.get_reporter_count()} 个")
    
    print("\n" + "="*60)
    print("🔍 可用报告器列表")
    print("="*60)
    
    for reporter in sorted(registry.get_all_reporters(), key=lambda x: x['name']):
        status = "✅" if reporter['available'] else "❌"
        print(f"  {status} {reporter['name']}")

if __name__ == '__main__':
    main()
