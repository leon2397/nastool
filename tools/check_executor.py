#!/usr/bin/env python3
"""
NASTool 检测执行器
将所有92个检测器整合到统一的执行框架中
"""
import os
import sys
import importlib
from typing import Dict, List, Any, Optional

# 添加核心模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-core'))
sys.path.insert(0, os.path.dirname(__file__))

import checker_registry

class CheckExecutor:
    """检测执行器"""

    def __init__(self):
        self._results = []

    def execute_check(self, checker_id: str, device_info: Optional[Dict] = None) -> Dict[str, Any]:
        """执行单个检测器"""
        try:
            category, module_name = checker_id.split('.', 1)
            
            # 动态导入模块
            module = importlib.import_module(f"nastool_core.checks.{category}.{module_name}")
            
            # 尝试查找类方式的检测器
            checker_class = None
            for attr_name in dir(module):
                if attr_name.endswith('Checker') or attr_name.endswith('Check'):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type):
                        # 检查是否是抽象类
                        if hasattr(attr, '__abstractmethods__') and attr.__abstractmethods__:
                            continue
                        checker_class = attr
                        break
            
            if checker_class:
                # 类方式检测器
                checker = checker_class()
                result = checker.run()
            else:
                # 尝试函数方式的检测器
                # 查找以模块名命名的函数（去掉_check或_checker后缀）
                func_name = module_name.replace('_check', '').replace('_checker', '')
                check_func = getattr(module, func_name, None)
                
                if not check_func:
                    # 尝试其他函数名
                    for attr_name in dir(module):
                        if callable(getattr(module, attr_name)) and not attr_name.startswith('_'):
                            check_func = getattr(module, attr_name)
                            break
                
                if not check_func:
                    return {
                        'checker_id': checker_id,
                        'status': 'error',
                        'message': '无法找到检测器'
                    }
                
                # 创建模拟上下文对象
                class MockContext:
                    def passed(self, **kwargs):
                        return {'status': 'pass', **kwargs}
                    def failed(self, **kwargs):
                        return {'status': 'fail', **kwargs}
                    def warning(self, **kwargs):
                        return {'status': 'warning', **kwargs}
                
                result = check_func(MockContext())
            
            # 转换结果格式
            if hasattr(result, 'passed'):
                # CheckResult 对象
                status = 'pass' if result.passed else 'fail'
                if hasattr(result, 'severity'):
                    severity = str(result.severity).lower()
                    if severity == 'warning':
                        status = 'warning'
                    elif severity == 'critical':
                        status = 'fail'
                
                message = str(result.message) if hasattr(result, 'message') else ''
                title = str(result.title) if hasattr(result, 'title') else checker_id
                
                return {
                    'checker_id': checker_id,
                    'title': title,
                    'status': status,
                    'message': message,
                    'details': getattr(result, 'details', {})
                }
            elif isinstance(result, dict):
                # 字典格式结果
                return {
                    'checker_id': checker_id,
                    'title': result.get('title', checker_id),
                    'status': result.get('status', 'info'),
                    'message': result.get('message', ''),
                    'details': result.get('details', {})
                }
            else:
                return {
                    'checker_id': checker_id,
                    'title': checker_id,
                    'status': 'info',
                    'message': str(result),
                    'details': {}
                }
        
        except Exception as e:
            return {
                'checker_id': checker_id,
                'title': checker_id,
                'status': 'error',
                'message': str(e)
            }

    def execute_category(self, category: str, device_info: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行指定类别的所有检测器"""
        registry = checker_registry.CheckerRegistry()
        checkers = registry.list_checkers(category)
        
        results = []
        for checker in checkers:
            if checker['available']:
                result = self.execute_check(checker['id'], device_info)
                results.append(result)
        
        return results

    def execute_all(self, device_info: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行所有检测器"""
        registry = checker_registry.CheckerRegistry()
        all_checkers = registry.list_checkers()
        
        results = []
        for checker in all_checkers:
            if checker['available']:
                result = self.execute_check(checker['id'], device_info)
                results.append(result)
        
        return results

def main():
    """主函数 - 演示检测执行器"""
    print("="*60)
    print("🚀 NASTool 检测执行器")
    print("="*60)

    executor = CheckExecutor()
    
    # 执行系统检测类别
    print("\n🔍 正在执行系统检测...")
    results = executor.execute_category('system')
    
    for result in results:
        status_icon = {
            'pass': '✅',
            'ok': '✅',
            'warning': '⚠️',
            'fail': '❌',
            'error': '❌',
            'info': '⚪'
        }.get(result['status'], '⚪')
        
        title = result.get('title', result['checker_id'])
        print(f"  {status_icon} {title}: {result['message']}")

if __name__ == '__main__':
    main()
