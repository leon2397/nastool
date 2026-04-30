#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量改造检测器工具 - 为所有检测器添加准确性保障方法

Usage:
    python batch_upgrade_checkers.py
"""

import os
import sys
import re

def find_check_files(checks_dir):
    """查找所有检测器文件"""
    check_files = []
    for root, dirs, files in os.walk(checks_dir):
        for f in files:
            if f.endswith('.py') and not f.startswith('_') and f != 'base.py' and f != 'decorators.py':
                check_files.append(os.path.join(root, f))
    return check_files

def analyze_checker(filepath):
    """分析检测器文件类型和结构"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 判断类型：类式还是函数式
    is_class_based = 'class ' in content and 'def run(self)' in content
    is_func_based = '@check(' in content
    
    # 检查是否已使用准确性保障
    has_accuracy = 'create_source_result' in content or 'data_sources' in content or 'confidence' in content
    
    return {
        'path': filepath,
        'is_class_based': is_class_based,
        'is_func_based': is_func_based,
        'has_accuracy': has_accuracy
    }

def upgrade_class_checker(filepath):
    """升级类式检测器，添加准确性保障"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 添加导入
    if 'from nastool_core.checks.base import' in content:
        content = content.replace(
            'from nastool_core.checks.base import',
            'from nastool_core.checks.base import Check, CheckResult, CheckCategory, CheckSeverity'
        )
    
    # 在run方法中添加准确性保障逻辑
    if 'def run(self) -> CheckResult:' in content:
        # 找到run方法
        pattern = r'(def run\(self\) -> CheckResult:.*?return )(CheckResult\()'
        replacement = r'\1self._enhance_result_with_accuracy(\2'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    return content

def upgrade_func_checker(filepath):
    """升级函数式检测器，添加准确性保障"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 添加 enable_accuracy=True 参数到 @check 装饰器
    if '@check(' in content:
        # 查找装饰器参数
        pattern = r'@check\(([^)]+)\)'
        match = re.search(pattern, content)
        if match:
            args = match.group(1)
            # 如果没有 enable_accuracy 参数，添加它
            if 'enable_accuracy' not in args:
                new_args = args.rstrip(',') + ', enable_accuracy=True)'
                content = content.replace(f'@check({args})', f'@check({new_args}')
    
    return content

def main():
    checks_dir = os.path.join(os.path.dirname(__file__), '..', 'nastool-core', 'nastool_core', 'checks')
    checks_dir = os.path.abspath(checks_dir)
    
    print(f"🔍 扫描检测器目录: {checks_dir}")
    check_files = find_check_files(checks_dir)
    print(f"📊 发现 {len(check_files)} 个检测器文件")
    
    # 分析每个检测器
    class_based = []
    func_based = []
    needs_upgrade = []
    
    for filepath in check_files:
        info = analyze_checker(filepath)
        if info['is_class_based']:
            class_based.append(filepath)
        elif info['is_func_based']:
            func_based.append(filepath)
        
        if not info['has_accuracy']:
            needs_upgrade.append(filepath)
    
    print(f"\n📋 检测器类型分布:")
    print(f"   - 类式检测器: {len(class_based)}")
    print(f"   - 函数式检测器: {len(func_based)}")
    print(f"   - 需要升级: {len(needs_upgrade)}")
    
    # 批量升级
    print(f"\n🚀 开始批量升级...")
    upgraded = 0
    skipped = 0
    
    for filepath in check_files:
        info = analyze_checker(filepath)
        
        if info['has_accuracy']:
            print(f"⏭️ 已跳过: {os.path.basename(filepath)} (已使用准确性保障)")
            skipped += 1
            continue
        
        try:
            if info['is_class_based']:
                new_content = upgrade_class_checker(filepath)
            elif info['is_func_based']:
                new_content = upgrade_func_checker(filepath)
            else:
                print(f"❓ 未知类型: {os.path.basename(filepath)}")
                skipped += 1
                continue
            
            # 写入升级后的内容
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ 已升级: {os.path.basename(filepath)}")
            upgraded += 1
        except Exception as e:
            print(f"❌ 升级失败: {os.path.basename(filepath)} - {str(e)}")
            skipped += 1
    
    print(f"\n📊 升级完成!")
    print(f"   - 已升级: {upgraded}")
    print(f"   - 已跳过: {skipped}")

if __name__ == '__main__':
    main()
