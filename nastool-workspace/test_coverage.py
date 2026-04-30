"""
test_coverage.py - 测试覆盖率提升工具

自动化测试生成和覆盖率检查。
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Set


class TestCoverageAnalyzer:
    """测试覆盖率分析器"""
    
    def __init__(self, module_path: str):
        self.module_path = Path(module_path)
        self.module_name = self.module_path.name
        
    def analyze(self) -> Dict[str, any]:
        """分析模块测试覆盖情况"""
        # 获取所有函数和类
        functions, classes = self._extract_module_items()
        
        # 获取已有测试
        tested_items = self._get_tested_items()
        
        # 计算覆盖率
        total = len(functions) + len(classes)
        tested = len(tested_items)
        coverage = (tested / total * 100) if total > 0 else 0
        
        # 未测试项
        untested_functions = functions - tested_items
        untested_classes = classes - tested_items
        
        return {
            "module": self.module_name,
            "total_items": total,
            "tested_items": tested,
            "coverage": round(coverage, 1),
            "functions": len(functions),
            "classes": len(classes),
            "untested_functions": sorted(untested_functions),
            "untested_classes": sorted(untested_classes)
        }
    
    def _extract_module_items(self) -> (Set[str], Set[str]):
        """提取模块中的函数和类"""
        functions = set()
        classes = set()
        
        for py_file in self.module_path.rglob("*.py"):
            if py_file.name.startswith("test_"):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # 跳过私有函数
                        if not node.name.startswith('_'):
                            functions.add(node.name)
                    elif isinstance(node, ast.ClassDef):
                        classes.add(node.name)
            except:
                pass
        
        return functions, classes
    
    def _get_tested_items(self) -> Set[str]:
        """获取已测试的项"""
        tested = set()
        test_dir = self.module_path / "tests"
        
        if not test_dir.exists():
            return tested
        
        for test_file in test_dir.rglob("test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 简单提取测试的函数名
                import re
                # 匹配 test_xxx 或 TestXxx 中的被测对象
                patterns = [
                    r'def test_(\w+)',
                    r'test_(\w+)',
                    r'class Test(\w+)',
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    tested.update(matches)
            except:
                pass
        
        return tested
    
    def generate_missing_tests(self) -> str:
        """生成缺失测试的模板代码"""
        analysis = self.analyze()
        
        lines = [
            f"# Auto-generated tests for {self.module_name}",
            f"# Coverage: {analysis['coverage']}%",
            "",
            "import pytest",
            f"from {self.module_name} import *",
            "",
        ]
        
        # 为未测试的函数生成测试模板
        for func in analysis['untested_functions'][:10]:  # 最多10个
            lines.extend([
                f"",
                f"def test_{func}():",
                f"    \"\"\"Test {func}\"\"\"",
                f"    # TODO: Implement test",
                f"    result = {func}()",
                f"    assert result is not None",
                f"",
            ])
        
        # 为未测试的类生成测试模板
        for cls in analysis['untested_classes'][:5]:  # 最多5个
            lines.extend([
                f"",
                f"class Test{cls}:",
                f"    \"\"\"Test {cls}\"\"\"",
                f"    ",
                f"    def test_init(self):",
                f"        obj = {cls}()",
                f"        assert obj is not None",
                f"",
            ])
        
        return '\n'.join(lines)


def analyze_all_modules(base_path: str) -> List[Dict]:
    """分析所有模块的测试覆盖率"""
    modules = [
        "nastool-common/nastool_common",
        "nastool-core/nastool_core", 
        "nastool-adapters/nastool_adapters",
        "nastool-reporters/nastool_reporters",
        "nastool-fixes/nastool_fixes",
        "nastool-cli/nastool_cli"
    ]
    
    results = []
    for module in modules:
        path = Path(base_path) / module
        if path.exists():
            analyzer = TestCoverageAnalyzer(path)
            results.append(analyzer.analyze())
    
    return results


if __name__ == "__main__":
    import sys
    
    base = r"C:\tools416\nastool-v3.0.0"
    
    print("=" * 70)
    print("NASTool v4.0 - 测试覆盖率分析")
    print("=" * 70)
    
    results = analyze_all_modules(base)
    
    print(f"\n{'Module':<30} {'Coverage':>10} {'Items':>8} {'Tested':>8}")
    print("-" * 70)
    
    total_items = 0
    total_tested = 0
    
    for r in results:
        print(f"{r['module']:<30} {r['coverage']:>9.1f}% {r['total_items']:>8} {r['tested_items']:>8}")
        total_items += r['total_items']
        total_tested += r['tested_items']
    
    overall = (total_tested / total_items * 100) if total_items > 0 else 0
    
    print("-" * 70)
    print(f"{'Overall':<30} {overall:>9.1f}% {total_items:>8} {total_tested:>8}")
    
    print("\n" + "=" * 70)
    print("目标: v3.0 65% → v4.0 85%")
    print("=" * 70)
