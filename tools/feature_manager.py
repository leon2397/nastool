#!/usr/bin/env python3
"""
NASTool 统一功能管理器 - 自动扫描版本
整合所有已开发的功能模块
"""
import os
import sys
import glob
import importlib
import re

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# 添加所有子模块路径
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-core'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-adapters'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-fixes'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-reporters'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-cli'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool-core'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool-adapters'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool-fixes'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool-reporters'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-v4.0.0', 'nastool-cli'))

class FeatureManager:
    """统一功能管理器 - 自动扫描版本"""
    
    def __init__(self):
        self.checkers = []           # 检测器
        self.adapters = []           # 适配器
        self.fixes = []              # 修复引擎
        self.reporters = []          # 报告器
        self.cli_commands = []       # CLI命令
        self.monitors = []           # 监控器
        self.detectors = []          # 探测器
        self.diagnostics = []        # 诊断器
        self._load_all_features()
    
    def _scan_directory(self, base_dir):
        """扫描目录中的所有Python文件"""
        files = []
        full_path = os.path.join(PROJECT_ROOT, base_dir)
        if os.path.exists(full_path):
            for pyfile in glob.glob(os.path.join(full_path, '**/*.py'), recursive=True):
                if '__pycache__' not in pyfile and not pyfile.endswith('__init__.py'):
                    rel_path = os.path.relpath(pyfile, PROJECT_ROOT)
                    files.append(rel_path)
        return files
    
    def _extract_classes_from_file(self, filepath):
        """从文件中提取功能类"""
        classes = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            class_pattern = r'class\s+(\w+)\s*[:(]'
            for match in re.finditer(class_pattern, content):
                class_name = match.group(1)
                func_type = self._get_function_type(class_name)
                if func_type:
                    classes.append({
                        'name': class_name,
                        'type': func_type,
                        'file': filepath
                    })
        except Exception as e:
            pass
        return classes
    
    def _get_function_type(self, class_name):
        """根据类名判断功能类型"""
        if class_name.endswith('Checker') or class_name.endswith('Check'):
            return 'checker'
        elif class_name.endswith('Adapter'):
            return 'adapter'
        elif class_name.endswith('Fix') and not class_name.startswith('Fix'):
            return 'fix'
        elif class_name.endswith('Reporter'):
            return 'reporter'
        elif class_name.endswith('Command') and not class_name.startswith('Command'):
            return 'command'
        elif class_name.endswith('Monitor'):
            return 'monitor'
        elif class_name.endswith('Detector') and not class_name.endswith('Checker'):
            return 'detector'
        elif class_name.endswith('Diagnostic'):
            return 'diagnostic'
        return None
    
    def _load_all_features(self):
        """加载所有功能模块"""
        print("🔍 开始自动扫描所有功能模块...")
        
        # 扫描所有目录
        scan_dirs = [
            'nastool-core',
            'nastool-adapters',
            'nastool-fixes',
            'nastool-reporters',
            'nastool-cli',
            'nastool-v4.0.0/nastool-core',
            'nastool-v4.0.0/nastool-adapters',
            'nastool-v4.0.0/nastool-fixes',
            'nastool-v4.0.0/nastool-reporters',
            'nastool-v4.0.0/nastool-cli',
        ]
        
        # 收集所有功能类
        all_classes = []
        for scan_dir in scan_dirs:
            files = self._scan_directory(scan_dir)
            for filepath in files:
                full_path = os.path.join(PROJECT_ROOT, filepath)
                classes = self._extract_classes_from_file(full_path)
                all_classes.extend(classes)
        
        # 去重（基于类名+文件路径）
        seen = set()
        unique_classes = []
        for cls in all_classes:
            key = f"{cls['name']}-{cls['file']}"
            if key not in seen:
                seen.add(key)
                unique_classes.append(cls)
        
        # 按类型分类加载
        self._categorize_features(unique_classes)
        
        # 额外加载统一检测器执行引擎中的检测器（已包含所有标准检测器）
        self._load_unified_checkers()
        
        print("\n✅ 功能扫描完成！")
    
    def _categorize_features(self, classes):
        """将功能分类"""
        for cls in classes:
            func_type = cls['type']
            if func_type == 'monitor':
                self.monitors.append({
                    'id': f"monitor.{cls['name'].lower()}",
                    'name': cls['name'],
                    'module': self._file_to_module(cls['file']),
                    'available': True
                })
            elif func_type == 'detector':
                self.detectors.append({
                    'id': f"detector.{cls['name'].lower()}",
                    'name': cls['name'],
                    'module': self._file_to_module(cls['file']),
                    'available': True
                })
            elif func_type == 'diagnostic':
                self.diagnostics.append({
                    'id': f"diagnostic.{cls['name'].lower()}",
                    'name': cls['name'],
                    'module': self._file_to_module(cls['file']),
                    'available': True
                })
            elif func_type == 'fix':
                self.fixes.append({
                    'id': f"fix.{cls['name'].lower()}",
                    'name': cls['name'],
                    'module': self._file_to_module(cls['file']),
                    'available': True
                })
            elif func_type == 'reporter':
                self.reporters.append({
                    'id': f"reporter.{cls['name'].lower()}",
                    'name': cls['name'],
                    'module': self._file_to_module(cls['file']),
                    'available': True
                })
            elif func_type == 'command':
                self.cli_commands.append({
                    'id': f"command.{cls['name'].lower()}",
                    'name': cls['name'],
                    'module': self._file_to_module(cls['file']),
                    'available': True
                })
    
    def _file_to_module(self, filepath):
        """将文件路径转换为模块路径"""
        # 移除扩展名
        module_path = filepath.replace('.py', '')
        # 替换路径分隔符
        module_path = module_path.replace('/', '.').replace('\\', '.')
        # 处理v4.0.0目录
        if module_path.startswith('nastool-v4.0.0.'):
            module_path = module_path.replace('nastool-v4.0.0.', '', 1)
        return module_path
    
    def _load_unified_checkers(self):
        """加载统一检测器执行引擎中的检测器"""
        try:
            from unified_checker_executor import UnifiedCheckerExecutor
            executor = UnifiedCheckerExecutor()
            self.checkers = executor.checkers
            print(f"   ✅ 检测器: {len(self.checkers)} 个")
        except Exception as e:
            print(f"   ⚠️ 加载检测器失败: {e}")
        
        # 加载适配器注册表
        try:
            from adapter_registry import AdapterRegistry
            registry = AdapterRegistry()
            self.adapters = registry.list_adapters()
            print(f"   ✅ 适配器: {len(self.adapters)} 个")
        except Exception as e:
            print(f"   ⚠️ 加载适配器失败: {e}")
    
    def get_feature_summary(self):
        """获取功能汇总"""
        return {
            'checkers': len(self.checkers),
            'adapters': len(self.adapters),
            'fixes': len(self.fixes),
            'reporters': len(self.reporters),
            'cli_commands': len(self.cli_commands),
            'monitors': len(self.monitors),
            'detectors': len(self.detectors),
            'diagnostics': len(self.diagnostics),
            'total': len(self.checkers) + len(self.adapters) + len(self.fixes) + 
                     len(self.reporters) + len(self.cli_commands) + len(self.monitors) +
                     len(self.detectors) + len(self.diagnostics)
        }
    
    def show_feature_summary(self):
        """显示功能汇总"""
        summary = self.get_feature_summary()
        print("\n" + "="*65)
        print("📊 NASTool 完整功能汇总")
        print("="*65)
        print(f"   🔍 检测器: {summary['checkers']} 个")
        print(f"   🔌 适配器: {summary['adapters']} 个")
        print(f"   🔧 修复引擎: {summary['fixes']} 个")
        print(f"   📝 报告器: {summary['reporters']} 个")
        print(f"   💻 CLI命令: {summary['cli_commands']} 个")
        print(f"   📈 监控器: {summary['monitors']} 个")
        print(f"   🔎 探测器: {summary['detectors']} 个")
        print(f"   🩺 诊断器: {summary['diagnostics']} 个")
        print(f"   🎯 总计: {summary['total']} 个功能")
        print("="*65)
    
    def show_detailed_summary(self):
        """显示详细功能汇总"""
        self.show_feature_summary()
        
        # 检测器分类
        print("\n🔍 检测器分类:")
        cat_counts = {}
        for checker in self.checkers:
            cat = checker.get('category', 'unknown')
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        for cat, count in sorted(cat_counts.items()):
            print(f"   {cat}: {count} 个")
        
        # 适配器分类
        print("\n🔌 适配器分类:")
        cat_counts = {}
        for adapter in self.adapters:
            cat = adapter.get('category', 'unknown')
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        for cat, count in sorted(cat_counts.items()):
            print(f"   {cat}: {count} 个")
        
        # 监控器列表
        if self.monitors:
            print("\n📈 监控器列表:")
            for monitor in self.monitors[:10]:
                print(f"   ✅ {monitor['name']}")
            if len(self.monitors) > 10:
                print(f"   ... 还有 {len(self.monitors) - 10} 个")
        
        # 探测器列表
        if self.detectors:
            print("\n🔎 探测器列表:")
            for detector in self.detectors[:10]:
                print(f"   ✅ {detector['name']}")
            if len(self.detectors) > 10:
                print(f"   ... 还有 {len(self.detectors) - 10} 个")

def main():
    """主函数"""
    manager = FeatureManager()
    manager.show_detailed_summary()

if __name__ == '__main__':
    main()
