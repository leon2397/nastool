#!/usr/bin/env python3
"""
NASTool 统一检测器执行引擎
确保所有检测器都能被正确发现和执行
"""
import os
import sys
import importlib
from typing import Dict, List, Any, Optional

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# 添加所有路径 - 当前版本nastool-core必须在v4.0.0版本前面！
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools'))
# 当前版本优先
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-core'))
# v4.0.0版本作为补充
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool-core'))

class UnifiedCheckerExecutor:
    """统一检测器执行引擎"""
    
    def __init__(self):
        self.checkers = []
        # 确保正确的sys.path顺序
        self._ensure_correct_path_order()
        self._discover_all_checkers()
    
    def _ensure_correct_path_order(self):
        """确保当前版本nastool-core在v4.0.0版本前面"""
        current_core = os.path.join(PROJECT_ROOT, 'nastool-core')
        v4_core = os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool-core')
        
        # 如果v4.0.0版本在当前版本前面，移除v4.0.0版本
        if v4_core in sys.path and current_core in sys.path:
            v4_index = sys.path.index(v4_core)
            current_index = sys.path.index(current_core)
            if v4_index < current_index:
                sys.path.remove(v4_core)
                # 在当前版本后面重新添加v4.0.0版本
                sys.path.insert(current_index + 1, v4_core)
        
        # 确保当前版本存在
        if current_core not in sys.path:
            sys.path.insert(0, current_core)
        
        # 确保v4.0.0版本存在
        if v4_core not in sys.path:
            sys.path.append(v4_core)
    
    def _discover_all_checkers(self):
        """发现所有检测器，处理命名变体"""
        base_paths = [
            os.path.join(PROJECT_ROOT, 'nastool-core', 'nastool_core', 'checks'),
            os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool-core', 'nastool_core', 'checks')
        ]
        
        categories = ['ai', 'nas', 'network', 'security', 'storage', 'system', 'usb']
        category_names = {
            'ai': 'AI/机器学习',
            'nas': 'NAS服务',
            'network': '网络',
            'security': '安全',
            'storage': '存储',
            'system': '系统',
            'usb': 'USB'
        }
        
        seen_checkers = set()
        
        for base_path in base_paths:
            if not os.path.exists(base_path):
                continue
            
            for category in categories:
                cat_path = os.path.join(base_path, category)
                if not os.path.exists(cat_path):
                    continue
                
                for filename in os.listdir(cat_path):
                    if filename.endswith('.py') and not filename.startswith('_'):
                        module_name = filename[:-3]
                        checker_key = f"{category}.{module_name}"
                        
                        # 跳过重复
                        if checker_key in seen_checkers:
                            continue
                        seen_checkers.add(checker_key)
                        
                        # 尝试多种导入路径
                        success, info = self._try_import_checker(category, module_name)
                        
                        self.checkers.append({
                            'id': checker_key,
                            'category': category,
                            'category_name': category_names[category],
                            'name': module_name.replace('_', ' ').title(),
                            'available': success,
                            'module_info': info
                        })
    
    def _try_import_checker(self, category, module_name):
        """尝试导入检测器，处理多种命名模式"""
        # 尝试多种模块路径
        module_paths = [
            f"nastool_core.checks.{category}.{module_name}",
            f"checks.{category}.{module_name}",
            # 直接从文件导入（绕过包结构问题）
        ]
        
        for mod_path in module_paths:
            try:
                module = importlib.import_module(mod_path)
                
                # 尝试多种类名模式
                class_patterns = [
                    module_name.replace('_', '').capitalize() + 'Checker',
                    module_name.replace('_', '').capitalize() + 'Check',
                    ''.join(w.capitalize() for w in module_name.split('_')) + 'Checker',
                    ''.join(w.capitalize() for w in module_name.split('_')) + 'Check',
                    module_name.capitalize(),
                    # 移除_checker后缀后的类名
                    module_name.replace('_checker', '').replace('_', '').capitalize(),
                    module_name.replace('_checker', '').replace('_', '').capitalize() + 'Checker',
                    # 移除_check后缀后的类名
                    module_name.replace('_check', '').replace('_', '').capitalize(),
                    module_name.replace('_check', '').replace('_', '').capitalize() + 'Check',
                    # 直接使用模块名（首字母大写）
                    module_name.title().replace('_', '')
                ]
                
                # 也尝试查找所有以Checker/Check/Diagnostic/Monitor/Detector结尾的类
                found_classes = []
                for attr_name in dir(module):
                    if attr_name.endswith('Checker') or attr_name.endswith('Check') or \
                       attr_name.endswith('Diagnostic') or attr_name.endswith('Monitor') or \
                       attr_name.endswith('Detector'):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type):
                            # 跳过抽象类
                            if hasattr(attr, '__abstractmethods__') and attr.__abstractmethods__:
                                continue
                            found_classes.append(attr_name)
                
                if found_classes:
                    return True, {'module': mod_path, 'classes': found_classes}
                
                # 尝试查找函数式检测器
                func_patterns = [
                    module_name,
                    module_name.replace('_check', ''),
                    module_name.replace('_checker', ''),
                    'run',
                    'check',
                    'diagnose'
                ]
                
                for func_name in func_patterns:
                    if hasattr(module, func_name):
                        obj = getattr(module, func_name)
                        if callable(obj):
                            return True, {'module': mod_path, 'function': func_name}
                
                # 检查是否有装饰器注册的检测器
                if hasattr(module, '__checks__'):
                    return True, {'module': mod_path, 'decorated': True}
                
                # 模块导入成功但未找到检测器
                return True, {'module': mod_path, 'note': '模块导入成功，但未找到检测器类/函数'}
                
            except ImportError:
                continue
        
        return False, {'error': '无法导入模块'}
    
    def execute_checker(self, checker_id):
        """执行指定检测器"""
        checker = next((c for c in self.checkers if c['id'] == checker_id), None)
        if not checker or not checker['available']:
            return {'status': 'error', 'message': '检测器不可用'}
        
        try:
            mod_info = checker['module_info']
            module = importlib.import_module(mod_info['module'])
            
            # 优先尝试类方式
            if 'classes' in mod_info:
                for class_name in mod_info['classes']:
                    try:
                        checker_class = getattr(module, class_name)
                        instance = checker_class()
                        if hasattr(instance, 'run'):
                            result = instance.run()
                            return {'status': 'success', 'result': result, 'checker': class_name}
                        elif hasattr(instance, 'check'):
                            result = instance.check()
                            return {'status': 'success', 'result': result, 'checker': class_name}
                    except:
                        continue
            
            # 尝试函数方式
            if 'function' in mod_info:
                func = getattr(module, mod_info['function'])
                result = func()
                return {'status': 'success', 'result': result, 'checker': mod_info['function']}
            
            return {'status': 'warning', 'message': '检测器已加载但无法执行'}
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def execute_category(self, category):
        """执行指定类别的所有检测器"""
        results = []
        for checker in self.checkers:
            if checker['category'] == category and checker['available']:
                result = self.execute_checker(checker['id'])
                results.append({'checker': checker['id'], **result})
        return results
    
    def execute_all(self):
        """执行所有可用检测器"""
        results = []
        for checker in self.checkers:
            if checker['available']:
                result = self.execute_checker(checker['id'])
                results.append({'checker': checker['id'], **result})
        return results
    
    def get_statistics(self):
        """获取统计信息"""
        by_category = {}
        total = len(self.checkers)
        available = sum(1 for c in self.checkers if c['available'])
        
        for checker in self.checkers:
            by_category[checker['category']] = by_category.get(checker['category'], {'total': 0, 'available': 0})
            by_category[checker['category']]['total'] += 1
            if checker['available']:
                by_category[checker['category']]['available'] += 1
        
        return {
            'total': total,
            'available': available,
            'by_category': by_category
        }
    
    def print_statistics(self):
        """打印统计信息"""
        stats = self.get_statistics()
        
        print("="*60)
        print("🔬 统一检测器执行引擎")
        print("="*60)
        print(f"\n📊 检测器统计:")
        print(f"   总数: {stats['total']}")
        print(f"   可用: {stats['available']}")
        print(f"   可用率: {stats['available']/stats['total']*100:.1f}%")
        
        category_names = {
            'ai': 'AI/机器学习',
            'nas': 'NAS服务',
            'network': '网络',
            'security': '安全',
            'storage': '存储',
            'system': '系统',
            'usb': 'USB'
        }
        
        print("\n📋 分类统计:")
        for cat, data in stats['by_category'].items():
            status = "✅" if data['available'] == data['total'] else "⚠️"
            print(f"   {status} {category_names.get(cat, cat)}: {data['available']}/{data['total']}")

def main():
    executor = UnifiedCheckerExecutor()
    executor.print_statistics()
    
    # 测试执行几个检测器
    print("\n🔍 测试执行检测器:")
    test_checkers = ['system.python_version', 'system.memory_check']
    for checker_id in test_checkers:
        result = executor.execute_checker(checker_id)
        status = "✅" if result['status'] == 'success' else "❌"
        print(f"   {status} {checker_id}: {result.get('message', result.get('status'))}")

if __name__ == '__main__':
    main()
