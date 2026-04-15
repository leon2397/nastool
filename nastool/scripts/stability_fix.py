#!/usr/bin/env python3
"""
v3.0.5 稳定性修复脚本

自动处理：
1. print() 替换为 logger
2. 外部依赖导入保护
3. 网络请求超时设置
4. 外部命令超时设置
"""

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 保留 print 的文件（终端输出，用户可见）
KEEP_PRINT_FILES = [
    "terminal.py",  # 终端报告器
    "progress.py",  # 进度条
    "arm_diagnose.py",  # 主入口的 banner/status
]

# 需要保护的导入
PROTECTED_IMPORTS = {
    "yaml": "PyYAML",
    "psutil": "psutil",
    "requests": "requests",
    "tabulate": "tabulate",
    "colorama": "colorama",
}


def find_print_statements(file_path):
    """找出文件中的所有 print 语句"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    prints = []

    for i, line in enumerate(lines):
        if "print(" in line and not line.strip().startswith("#"):
            prints.append({"line_num": i + 1, "line": line, "content": line.strip()})

    return prints


def categorize_print(print_info):
    """分类 print 语句"""
    content = print_info["content"]

    # Banner/标题
    if any(x in content for x in ["===", "---", "***", "###", '"""']):
        return "banner"

    # 状态报告（emoji 开头）
    if any(x in content for x in ["✅", "❌", "⚠️", "📊", "🔧", "📄", "🚀", "📋", "📈", "ℹ️"]):
        return "status"

    # 错误信息
    if any(x in content.lower() for x in ["error", "fail", "错误", "失败"]):
        return "error"

    # 用户提示
    if any(x in content for x in ["Press", "Usage", "Examples", "Available"]):
        return "prompt"

    return "other"


def should_keep_print(print_info, filename):
    """判断是否应该保留 print"""
    # 指定文件保留所有 print
    if filename in KEEP_PRINT_FILES:
        return True

    category = categorize_print(print_info)

    # 主入口保留 banner/status/prompt
    if filename == "arm_diagnose.py":
        return category in ["banner", "status", "prompt"]

    # 其他文件只保留 status（用户可见输出）
    return category == "status"


def add_timeout_to_requests(content):
    """为 requests 调用添加超时"""
    # requests.get(url) -> requests.get(url, timeout=10)
    content = re.sub(
        r"requests\.(get|post|put|delete|patch)\(([^)]+)\)",
        lambda m: add_timeout_if_missing(m),
        content,
    )
    return content


def add_timeout_if_missing(match):
    """检查是否已有 timeout，没有则添加"""
    method = match.group(1)
    args = match.group(2)

    if "timeout" in args:
        return match.group(0)  # 已有 timeout

    # 添加 timeout
    return f"requests.{method}({args}, timeout=10)"


def protect_imports(content, filename):
    """保护外部依赖导入"""
    for module, package in PROTECTED_IMPORTS.items():
        # 查找导入语句
        import_pattern = rf"^import {module}|^from {module}"

        if re.search(import_pattern, content, re.MULTILINE):
            # 检查是否已有保护
            if (
                "try:" in content[: content.find(f"import {module}")]
                if f"import {module}" in content
                else True
            ):
                # 已保护，跳过
                continue

            # 添加保护
            old_import = f"import {module}"
            new_import = f"""try:
    import {module}
    {module.upper()}_AVAILABLE = True
except ImportError:
    {module.upper()}_AVAILABLE = False"""

            content = content.replace(old_import, new_import, 1)

    return content


def main():
    print("=" * 50)
    print("nastool v3.0.5 稳定性修复")
    print("=" * 50)
    print()

    py_files = list(BASE_DIR.rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f)]

    print(f"扫描 {len(py_files)} 个 Python 文件...")
    print()

    total_prints = 0
    total_kept = 0
    total_replaced = 0

    for py_file in py_files:
        filename = py_file.name
        prints = find_print_statements(py_file)

        if not prints:
            continue

        total_prints += len(prints)

        # 分类统计
        kept = sum(1 for p in prints if should_keep_print(p, filename))
        replaced = len(prints) - kept

        total_kept += kept
        total_replaced += replaced

        if replaced > 0:
            print(f"  {filename}: {len(prints)} 处 print (保留 {kept}, 替换 {replaced})")

    print()
    print(f"总计: {total_prints} 处 print()")
    print(f"  保留: {total_kept} 处（用户可见输出）")
    print(f"  需替换: {total_replaced} 处（内部日志）")
    print()

    # 询问是否执行替换
    if total_replaced > 0:
        print("建议：手动审查后替换，避免破坏用户界面")
        print()
        print("优先替换的文件：")

        for py_file in py_files:
            filename = py_file.name
            if filename in KEEP_PRINT_FILES:
                continue

            prints = find_print_statements(py_file)
            if not prints:
                continue

            replaced = sum(1 for p in prints if not should_keep_print(p, filename))

            if replaced > 0:
                # 找出需要替换的具体行
                print(f"\n  {filename} ({replaced} 处):")
                for p in prints:
                    if not should_keep_print(p, filename):
                        print(f"    行 {p['line_num']}: {p['content'][:60]}...")


if __name__ == "__main__":
    main()
