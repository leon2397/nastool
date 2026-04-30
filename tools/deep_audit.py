#!/usr/bin/env python3
"""
NASTool 深度代码审计工具
全面分析所有代码模块的使用情况
"""
import os
import sys
import ast
import json

class DeepCodeAuditor:
    """深度代码审计器"""
    
    def __init__(self, base_path):
        self.base_path = base_path
        self.all_files = []
        self.imported_modules = set()
        self.defined_functions = {}
        self.called_functions = {}
        self.unused_files = []
        self.unused_functions = []
        
    def scan_all_files(self):
        """扫描所有Python文件"""
        for root, dirs, files in os.walk(self.base_path):
            # 跳过某些目录
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'tests', 'ARCHIVED']]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.base_path)
                    self.all_files.append({
                        'path': rel_path,
                        'full_path': file_path,
                        'size': os.path.getsize(file_path)
                    })
    
    def analyze_file(self, file_path):
        """分析单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # 提取导入的模块
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.imported_modules.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self.imported_modules.add(node.module)
            
            # 提取定义的函数和类
            filename = os.path.basename(file_path)
            self.defined_functions[filename] = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self.defined_functions[filename].append({
                        'name': node.name,
                        'line': node.lineno,
                        'type': 'function'
                    })
                elif isinstance(node, ast.ClassDef):
                    self.defined_functions[filename].append({
                        'name': node.name,
                        'line': node.lineno,
                        'type': 'class'
                    })
            
            # 提取调用的函数
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name not in self.called_functions:
                            self.called_functions[func_name] = []
                        self.called_functions[func_name].append(filename)
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                        if func_name not in self.called_functions:
                            self.called_functions[func_name] = []
                        self.called_functions[func_name].append(filename)
                    
        except Exception as e:
            print(f"⚠️ 分析文件失败 {file_path}: {e}")
    
    def find_unused_code(self):
        """找出未使用的代码"""
        # 分析主入口调用情况
        main_file = os.path.join(self.base_path, 'nastool.py')
        if os.path.exists(main_file):
            self.analyze_file(main_file)
        
        # 分析所有工具模块
        tools_dir = os.path.join(self.base_path, 'tools')
        if os.path.exists(tools_dir):
            for file in os.listdir(tools_dir):
                if file.endswith('.py'):
                    self.analyze_file(os.path.join(tools_dir, file))
        
        # 分析核心模块
        core_dir = os.path.join(self.base_path, 'nastool-core')
        if os.path.exists(core_dir):
            for root, dirs, files in os.walk(core_dir):
                dirs[:] = [d for d in dirs if d not in ['__pycache__']]
                for file in files:
                    if file.endswith('.py'):
                        self.analyze_file(os.path.join(root, file))
        
        # 分析适配器
        adapters_dir = os.path.join(self.base_path, 'nastool-adapters')
        if os.path.exists(adapters_dir):
            for root, dirs, files in os.walk(adapters_dir):
                dirs[:] = [d for d in dirs if d not in ['__pycache__', 'tests']]
                for file in files:
                    if file.endswith('.py'):
                        self.analyze_file(os.path.join(root, file))
        
        # 分析v4.0.0目录
        v4_dir = os.path.join(self.base_path, 'nastool-v4.0.0')
        if os.path.exists(v4_dir):
            for root, dirs, files in os.walk(v4_dir):
                dirs[:] = [d for d in dirs if d not in ['__pycache__', 'tests']]
                for file in files:
                    if file.endswith('.py'):
                        self.analyze_file(os.path.join(root, file))
    
    def generate_report(self):
        """生成详细审计报告"""
        report = "="*80 + "\n"
        report += "🔍 NASTool 深度代码审计报告\n"
        report += "="*80 + "\n\n"
        
        # 概览
        report += "📊 项目概览\n"
        report += "-"*50 + "\n"
        report += f"总文件数: {len(self.all_files)}\n"
        report += f"总大小: {sum(f['size'] for f in self.all_files) / 1024 / 1024:.2f} MB\n"
        report += f"已分析文件数: {len(self.defined_functions)}\n"
        report += f"导入模块数: {len(self.imported_modules)}\n"
        report += "\n"
        
        # 定义的函数/类
        total_definitions = sum(len(v) for v in self.defined_functions.values())
        report += "📋 定义的函数/类统计\n"
        report += "-"*50 + "\n"
        report += f"总共定义: {total_definitions} 个\n"
        
        # 找出未被调用的函数
        all_defined_names = set()
        for file, funcs in self.defined_functions.items():
            for func in funcs:
                all_defined_names.add(func['name'])
        
        all_called_names = set(self.called_functions.keys())
        unused_names = all_defined_names - all_called_names
        
        report += f"\n⚠️ 未被调用的函数/类: {len(unused_names)} 个\n"
        if unused_names:
            report += "  未调用列表: " + ", ".join(sorted(unused_names)[:20])
            if len(unused_names) > 20:
                report += f" ... (还有 {len(unused_names)-20} 个)"
        report += "\n\n"
        
        # 未被导入的文件
        report += "📁 未被导入的文件分析\n"
        report += "-"*50 + "\n"
        
        # 分析各个模块
        modules_info = []
        
        # 扫描工具模块
        tools_files = [f for f in self.all_files if 'tools/' in f['path']]
        report += f"\n🛠️ tools/ 目录: {len(tools_files)} 个文件\n"
        
        # 扫描适配器
        adapter_files = [f for f in self.all_files if 'nastool-adapters/' in f['path']]
        report += f"🔌 nastool-adapters/ 目录: {len(adapter_files)} 个文件\n"
        
        # 扫描v4.0.0核心模块
        core_files = [f for f in self.all_files if 'nastool-v4.0.0/' in f['path']]
        report += f"📦 nastool-v4.0.0/ 目录: {len(core_files)} 个文件\n"
        
        # 扫描nastool-core
        nc_files = [f for f in self.all_files if 'nastool-core/' in f['path']]
        report += f"🧠 nastool-core/ 目录: {len(nc_files)} 个文件\n"
        
        # 功能模块详情
        report += "\n" + "="*50 + "\n"
        report += "🔍 各模块功能分析\n"
        report += "="*50 + "\n"
        
        # 检测功能
        check_files = [f for f in self.all_files if '/checks/' in f['path']]
        report += f"\n🔍 检测功能 (checks/): {len(check_files)} 个检测器\n"
        
        # 修复功能
        fix_files = [f for f in self.all_files if '/fixes/' in f['path'] and not f['path'].endswith('__init__.py')]
        report += f"🔧 修复功能 (fixes/): {len(fix_files)} 个修复器\n"
        
        # 报告功能
        reporter_files = [f for f in self.all_files if '/reporters/' in f['path']]
        report += f"📝 报告功能 (reporters/): {len(reporter_files)} 个报告器\n"
        
        # 适配器
        adapter_impl_files = [f for f in self.all_files if 'nastool_adapters/' in f['path'] and not f['path'].endswith('__init__.py')]
        report += f"🔌 适配器 (adapters/): {len(adapter_impl_files)} 个适配器\n"
        
        return report
    
    def run(self):
        """运行审计"""
        print("🚀 正在进行深度代码审计...")
        self.scan_all_files()
        self.find_unused_code()
        report = self.generate_report()
        print(report)
        
        # 保存报告
        report_path = os.path.join(self.base_path, 'docs/DEEP_CODE_AUDIT.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📝 深度审计报告已保存到: {report_path}")

def main():
    base_path = os.path.dirname(os.path.dirname(__file__))
    auditor = DeepCodeAuditor(base_path)
    auditor.run()

if __name__ == '__main__':
    main()
