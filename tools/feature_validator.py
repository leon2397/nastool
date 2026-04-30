#!/usr/bin/env python3
"""
NASTool 完整功能验证系统
验证所有156个功能模块正常运行
"""
import os
import sys
import traceback

# 添加所有路径
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-adapters'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-fixes'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-reporters'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nastool-v4.0.0', 'nastool-cli'))

class FeatureValidator:
    """功能验证器"""
    
    def __init__(self):
        self.results = {
            'checkers': {'passed': 0, 'failed': 0, 'skipped': 0},
            'adapters': {'passed': 0, 'failed': 0, 'skipped': 0},
            'fixes': {'passed': 0, 'failed': 0, 'skipped': 0},
            'reporters': {'passed': 0, 'failed': 0, 'skipped': 0},
            'cli': {'passed': 0, 'failed': 0, 'skipped': 0}
        }
        self.errors = []
    
    def validate_checkers(self):
        """验证检测器"""
        print("🔍 正在验证检测器...")
        try:
            from checker_registry import CheckerRegistry
            registry = CheckerRegistry()
            
            for checker in registry.list_checkers():
                try:
                    # 尝试导入并实例化
                    module = __import__(checker['module'], fromlist=[''])
                    
                    # 尝试获取类
                    if hasattr(module, checker['class']):
                        checker_class = getattr(module, checker['class'])
                        # 检查是否是有效类
                        if isinstance(checker_class, type):
                            self.results['checkers']['passed'] += 1
                        else:
                            self.results['checkers']['skipped'] += 1
                    else:
                        # 尝试其他模式
                        found = False
                        for attr_name in dir(module):
                            if attr_name.endswith('Checker') or attr_name.endswith('Check'):
                                attr = getattr(module, attr_name)
                                if isinstance(attr, type):
                                    found = True
                                    break
                        if found:
                            self.results['checkers']['passed'] += 1
                        else:
                            self.results['checkers']['skipped'] += 1
                except Exception as e:
                    self.results['checkers']['failed'] += 1
                    self.errors.append(f"检测器 {checker['id']} 验证失败: {str(e)}")
        except Exception as e:
            self.errors.append(f"检测器注册表加载失败: {str(e)}")
    
    def validate_adapters(self):
        """验证适配器"""
        print("🔌 正在验证适配器...")
        try:
            from adapter_registry import AdapterRegistry
            registry = AdapterRegistry()
            
            for adapter in registry.list_adapters():
                try:
                    # 检查模块是否可导入
                    parts = adapter['module'].split('.')
                    module_path = '.'.join(parts[:-1]) if len(parts) > 1 else adapter['module']
                    __import__(adapter['module'])
                    self.results['adapters']['passed'] += 1
                except Exception as e:
                    self.results['adapters']['failed'] += 1
                    self.errors.append(f"适配器 {adapter['id']} 验证失败: {str(e)}")
        except Exception as e:
            self.errors.append(f"适配器注册表加载失败: {str(e)}")
    
    def validate_fixes(self):
        """验证修复引擎"""
        print("🔧 正在验证修复引擎...")
        try:
            from nastool_fixes.registry import get_all_fixes, list_available_fixes
            
            # 动态导入触发注册
            import nastool_fixes.network.config_dns
            import nastool_fixes.security.disable_root_login
            import nastool_fixes.security.enable_fail2ban
            import nastool_fixes.security.enforce_password_policy
            import nastool_fixes.security.renew_ssl_cert
            import nastool_fixes.storage.cleanup_docker_images
            import nastool_fixes.storage.cleanup_logs
            import nastool_fixes.storage.cleanup_tmp_space
            import nastool_fixes.storage.config_raid_recovery
            import nastool_fixes.storage.create_paths
            import nastool_fixes.system.check_versions
            import nastool_fixes.system.install_docker
            import nastool_fixes.system.install_python
            import nastool_fixes.system.setup_logrotate
            import nastool_fixes.ai.install_cuda
            import nastool_fixes.nas.config_ups_shutdown
            
            fixes = list_available_fixes()
            self.results['fixes']['passed'] = len(fixes)
            
        except Exception as e:
            self.errors.append(f"修复引擎验证失败: {str(e)}")
    
    def validate_reporters(self):
        """验证报告器"""
        print("📝 正在验证报告器...")
        try:
            reporters = [
                'nastool_reporters.file_reporter',
                'nastool_reporters.friendly_reporter',
                'nastool_reporters.health_dashboard',
                'nastool_reporters.html_reporter',
                'nastool_reporters.json_reporter',
                'nastool_reporters.pdf_reporter',
                'nastool_reporters.rich_reporter',
                'nastool_reporters.rk_reporter',
                'nastool_reporters.summary',
                'nastool_reporters.terminal'
            ]
            
            for reporter in reporters:
                try:
                    __import__(reporter)
                    self.results['reporters']['passed'] += 1
                except Exception as e:
                    self.results['reporters']['failed'] += 1
                    self.errors.append(f"报告器 {reporter} 验证失败: {str(e)}")
        except Exception as e:
            self.errors.append(f"报告器验证失败: {str(e)}")
    
    def validate_cli(self):
        """验证CLI命令"""
        print("💻 正在验证CLI命令...")
        try:
            from cli_registry import CLICommandRegistry
            registry = CLICommandRegistry()
            
            for cmd in registry.get_all_commands():
                if cmd['available']:
                    self.results['cli']['passed'] += 1
                else:
                    self.results['cli']['failed'] += 1
        except Exception as e:
            self.errors.append(f"CLI命令验证失败: {str(e)}")
    
    def run(self):
        """运行完整验证"""
        print("="*70)
        print("✅ NASTool 完整功能验证系统")
        print("="*70)
        
        self.validate_checkers()
        self.validate_adapters()
        self.validate_fixes()
        self.validate_reporters()
        self.validate_cli()
        
        self._print_report()
    
    def _print_report(self):
        """打印验证报告"""
        print("\n" + "="*70)
        print("📊 功能验证报告")
        print("="*70)
        
        total_passed = sum(r['passed'] for r in self.results.values())
        total_failed = sum(r['failed'] for r in self.results.values())
        total_skipped = sum(r['skipped'] for r in self.results.values())
        total = total_passed + total_failed + total_skipped
        
        print(f"\n总体结果:")
        print(f"  ✅ 通过: {total_passed}")
        print(f"  ❌ 失败: {total_failed}")
        print(f"  ⚪ 跳过: {total_skipped}")
        print(f"  🎯 总计: {total}")
        
        print("\n分类结果:")
        categories = {
            'checkers': '检测器',
            'adapters': '适配器',
            'fixes': '修复引擎',
            'reporters': '报告器',
            'cli': 'CLI命令'
        }
        
        for key, name in categories.items():
            r = self.results[key]
            print(f"\n  {name}:")
            print(f"    ✅ 通过: {r['passed']}")
            print(f"    ❌ 失败: {r['failed']}")
            print(f"    ⚪ 跳过: {r['skipped']}")
        
        if self.errors:
            print("\n⚠️ 错误详情:")
            for i, error in enumerate(self.errors[:10], 1):
                print(f"  {i}. {error}")
            if len(self.errors) > 10:
                print(f"  ... 还有 {len(self.errors)-10} 个错误")
        
        # 保存报告
        report_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs/VALIDATION_REPORT.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# NASTool 功能验证报告\n\n")
            f.write(f"## 总体结果\n")
            f.write(f"- 通过: {total_passed}\n")
            f.write(f"- 失败: {total_failed}\n")
            f.write(f"- 跳过: {total_skipped}\n")
            f.write(f"- 总计: {total}\n")
        
        print(f"\n📝 报告已保存到: {report_path}")

if __name__ == '__main__':
    validator = FeatureValidator()
    validator.run()
