#!/usr/bin/env python3
"""
NASTool 智能功能整合系统
自动处理命名变体，确保所有功能都能被发现和调用
"""
import os
import sys
import importlib

# 添加所有路径
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-adapters'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-adapters'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-fixes'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-reporters'))

class SmartFeatureRegistry:
    """智能功能注册表"""
    
    def __init__(self):
        self.all_features = []
        self._discover_all()
    
    def _discover_all(self):
        """发现所有功能"""
        self._discover_checkers()
        self._discover_adapters()
        self._discover_fixes()
        self._discover_reporters()
    
    def _discover_checkers(self):
        """智能发现检测器"""
        base_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nastool-core', 'nastool_core', 'checks'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nastool-v4.0.0', 'nastool-core', 'nastool_core', 'checks')
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
                        feature_id = f"checker.{category}.{module_name}"
                        
                        # 检查是否已存在
                        if any(f['id'] == feature_id for f in self.all_features):
                            continue
                        
                        # 尝试多种导入路径
                        module_paths = [
                            f"nastool_core.checks.{category}.{module_name}"
                        ]
                        
                        found = False
                        error = None
                        for mod_path in module_paths:
                            try:
                                module = importlib.import_module(mod_path)
                                # 尝试找到检测器类
                                checker_class = None
                                for attr in dir(module):
                                    if attr.endswith('Checker') or attr.endswith('Check'):
                                        obj = getattr(module, attr)
                                        if isinstance(obj, type):
                                            checker_class = attr
                                            break
                                
                                if checker_class:
                                    found = True
                                    break
                            except Exception as e:
                                error = str(e)
                        
                        self.all_features.append({
                            'id': feature_id,
                            'type': 'checker',
                            'category': category,
                            'category_name': category_names[category],
                            'name': module_name.replace('_', ' ').title(),
                            'available': found,
                            'error': error if not found else None
                        })
    
    def _discover_adapters(self):
        """智能发现适配器"""
        base_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nastool-adapters', 'nastool_adapters'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nastool-v4.0.0', 'nastool-adapters', 'nastool_adapters')
        ]
        
        category_map = {
            'ascend': ('ascend', '昇腾'),
            'jetson': ('jetson', 'Jetson'),
            'synology': ('synology', '群晖'),
            'qnap': ('qnap', '威联通'),
            'rockchip': ('rockchip', '瑞芯微'),
            'sophon': ('sophon', '算能'),
            'generic': ('generic', '通用')
        }
        
        for base_path in base_paths:
            if not os.path.exists(base_path):
                continue
            
            # 扫描顶层文件
            for filename in os.listdir(base_path):
                if filename.endswith('.py') and not filename.startswith('_') and filename != 'base.py':
                    module_name = filename[:-3]
                    
                    # 确定类别
                    category = 'other'
                    category_name = '其他'
                    for key, (cat, name) in category_map.items():
                        if key in module_name.lower():
                            category = cat
                            category_name = name
                            break
                    
                    feature_id = f"adapter.{category}.{module_name}"
                    
                    if any(f['id'] == feature_id for f in self.all_features):
                        continue
                    
                    # 尝试导入
                    try:
                        importlib.import_module(f"nastool_adapters.{module_name}")
                        available = True
                        error = None
                    except Exception as e:
                        available = False
                        error = str(e)
                    
                    self.all_features.append({
                        'id': feature_id,
                        'type': 'adapter',
                        'category': category,
                        'category_name': category_name,
                        'name': module_name.replace('_', ' ').title(),
                        'available': available,
                        'error': error
                    })
            
            # 扫描子目录
            for sub_dir in ['ascend', 'jetson']:
                sub_path = os.path.join(base_path, sub_dir)
                if os.path.exists(sub_path):
                    for filename in os.listdir(sub_path):
                        if filename.endswith('.py') and not filename.startswith('_'):
                            module_name = filename[:-3]
                            feature_id = f"adapter.{sub_dir}.{module_name}"
                            
                            if any(f['id'] == feature_id for f in self.all_features):
                                continue
                            
                            try:
                                importlib.import_module(f"nastool_adapters.{sub_dir}.{module_name}")
                                available = True
                                error = None
                            except Exception as e:
                                available = False
                                error = str(e)
                            
                            self.all_features.append({
                                'id': feature_id,
                                'type': 'adapter',
                                'category': sub_dir,
                                'category_name': category_map.get(sub_dir, (sub_dir, sub_dir))[1],
                                'name': f"{sub_dir.capitalize()}.{module_name.replace('_', ' ').title()}",
                                'available': available,
                                'error': error
                            })
    
    def _discover_fixes(self):
        """智能发现修复引擎"""
        try:
            from nastool_fixes.registry import list_available_fixes
            
            # 动态导入触发注册
            fixes_list = [
                'nastool_fixes.network.config_dns',
                'nastool_fixes.security.disable_root_login',
                'nastool_fixes.security.enable_fail2ban',
                'nastool_fixes.security.enforce_password_policy',
                'nastool_fixes.security.renew_ssl_cert',
                'nastool_fixes.storage.cleanup_docker_images',
                'nastool_fixes.storage.cleanup_logs',
                'nastool_fixes.storage.cleanup_tmp_space',
                'nastool_fixes.storage.config_raid_recovery',
                'nastool_fixes.storage.create_paths',
                'nastool_fixes.system.check_versions',
                'nastool_fixes.system.install_docker',
                'nastool_fixes.system.install_python',
                'nastool_fixes.system.setup_logrotate',
                'nastool_fixes.ai.install_cuda',
                'nastool_fixes.nas.config_ups_shutdown'
            ]
            
            for fix_path in fixes_list:
                try:
                    module = importlib.import_module(fix_path)
                    parts = fix_path.split('.')
                    category = parts[-2]
                    name = parts[-1]
                    feature_id = f"fix.{category}.{name}"
                    
                    if any(f['id'] == feature_id for f in self.all_features):
                        continue
                    
                    self.all_features.append({
                        'id': feature_id,
                        'type': 'fix',
                        'category': category,
                        'category_name': {
                            'network': '网络',
                            'security': '安全',
                            'storage': '存储',
                            'system': '系统',
                            'ai': 'AI',
                            'nas': 'NAS'
                        }.get(category, category),
                        'name': name.replace('_', ' ').title(),
                        'available': True,
                        'error': None
                    })
                except Exception as e:
                    pass
        except:
            pass
    
    def _discover_reporters(self):
        """智能发现报告器"""
        reporters = [
            ('file', '文件报告'),
            ('friendly', '友好报告'),
            ('health_dashboard', '健康仪表盘'),
            ('html', 'HTML报告'),
            ('json', 'JSON报告'),
            ('pdf', 'PDF报告'),
            ('rich', 'Rich报告'),
            ('rk', 'RK报告'),
            ('summary', '摘要报告'),
            ('terminal', '终端报告')
        ]
        
        for name, display_name in reporters:
            try:
                importlib.import_module(f"nastool_reporters.{name}_reporter")
                self.all_features.append({
                    'id': f"reporter.{name}",
                    'type': 'reporter',
                    'category': 'report',
                    'category_name': '报告',
                    'name': display_name,
                    'available': True,
                    'error': None
                })
            except:
                try:
                    importlib.import_module(f"nastool_reporters.{name}")
                    self.all_features.append({
                        'id': f"reporter.{name}",
                        'type': 'reporter',
                        'category': 'report',
                        'category_name': '报告',
                        'name': display_name,
                        'available': True,
                        'error': None
                    })
                except Exception as e:
                    self.all_features.append({
                        'id': f"reporter.{name}",
                        'type': 'reporter',
                        'category': 'report',
                        'category_name': '报告',
                        'name': display_name,
                        'available': False,
                        'error': str(e)
                    })
    
    def get_summary(self):
        """获取功能汇总"""
        by_type = {}
        by_category = {}
        
        for feature in self.all_features:
            # 按类型统计
            by_type[feature['type']] = by_type.get(feature['type'], {'total': 0, 'available': 0})
            by_type[feature['type']]['total'] += 1
            if feature['available']:
                by_type[feature['type']]['available'] += 1
            
            # 按类别统计
            cat_key = f"{feature['type']}.{feature['category']}"
            by_category[cat_key] = by_category.get(cat_key, {'name': feature['category_name'], 'total': 0, 'available': 0})
            by_category[cat_key]['total'] += 1
            if feature['available']:
                by_category[cat_key]['available'] += 1
        
        return {
            'by_type': by_type,
            'by_category': by_category,
            'total': len(self.all_features),
            'available': sum(1 for f in self.all_features if f['available'])
        }
    
    def print_summary(self):
        """打印功能汇总"""
        summary = self.get_summary()
        
        print("="*70)
        print("🔮 NASTool 智能功能注册表")
        print("="*70)
        
        print(f"\n📊 总体统计:")
        print(f"   功能总数: {summary['total']}")
        print(f"   可用功能: {summary['available']}")
        print(f"   可用率: {summary['available']/summary['total']*100:.1f}%")
        
        print("\n📋 按类型统计:")
        type_names = {
            'checker': '检测器',
            'adapter': '适配器',
            'fix': '修复引擎',
            'reporter': '报告器'
        }
        for type_key, stats in summary['by_type'].items():
            print(f"   {type_names.get(type_key, type_key)}: {stats['available']}/{stats['total']}")
        
        print("\n🔍 详细分类:")
        for cat_key, stats in sorted(summary['by_category'].items()):
            status = "✅" if stats['available'] == stats['total'] else "⚠️"
            print(f"   {status} {stats['name']}: {stats['available']}/{stats['total']}")

def main():
    registry = SmartFeatureRegistry()
    registry.print_summary()

if __name__ == '__main__':
    main()
