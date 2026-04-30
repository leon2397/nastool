#!/usr/bin/env python3
"""NASTool v4.2 卸载脚本"""

import os
import sys
import shutil

def uninstall():
    print('='*60)
    print('🗑️ NASTool v4.2 卸载')
    print('='*60)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print('\n⚠️ 即将删除以下内容:')
    print('   - bin/ 目录 (NASTool模块)')
    print('   - run_diagnose.py')
    print('   - uninstall.py')
    print('\n注意: 此操作不会影响系统文件')
    
    confirm = input('\n确认卸载? [y/N]: ').strip().lower()
    if confirm != 'y':
        print('❌ 取消卸载')
        sys.exit(0)
    
    print('\n🔄 开始卸载...')
    
    # 删除bin目录
    bin_dir = os.path.join(current_dir, 'bin')
    if os.path.exists(bin_dir):
        shutil.rmtree(bin_dir)
        print('✅ 删除 bin/')
    
    # 删除启动脚本
    for file in ['run_diagnose.py', 'uninstall.py', 'test_report.json']:
        filepath = os.path.join(current_dir, file)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f'✅ 删除 {file}')
    
    print('\n✅ 卸载完成!')
    print('='*60)

if __name__ == '__main__':
    uninstall()
