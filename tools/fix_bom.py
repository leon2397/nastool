#!/usr/bin/env python3
"""
修复UTF-8 BOM字符问题
"""
import os
import sys

PROJECT_ROOT = 'D:\\project\\nastool7'

def has_bom(filepath):
    """检查文件是否有BOM"""
    with open(filepath, 'rb') as f:
        bytes = f.read(3)
        return bytes == b'\xef\xbb\xbf'

def remove_bom(filepath):
    """移除BOM"""
    with open(filepath, 'rb') as f:
        content = f.read()
    
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    
    with open(filepath, 'wb') as f:
        f.write(content)
    
    return True

def fix_bom_files():
    """修复所有BOM问题"""
    print("🔧 修复UTF-8 BOM字符问题")
    print("="*70)
    
    fixed_count = 0
    total_files = 0
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        if 'archive' in root or '.git' in root:
            continue
        
        for f in files:
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                total_files += 1
                
                if has_bom(filepath):
                    print(f"   🛠️ 修复: {os.path.relpath(filepath, PROJECT_ROOT)}")
                    remove_bom(filepath)
                    fixed_count += 1
    
    print(f"\n✅ 完成！修复了 {fixed_count}/{total_files} 个文件")
    return fixed_count

if __name__ == '__main__':
    fix_bom_files()
