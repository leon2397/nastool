#!/usr/bin/env python3
"""NASTool项目文件归类整理脚本"""

import os
import shutil

# 文件归类规则
CATEGORIES = {
    'tools': [
        'install_deps.py',
        'install_pip.py',
        'install_pip_apt.py',
        'install_pip_curl.py',
        'install_deps_apt.py',
        'install_python_deps.py',
        'copy_deps.py',
        'copy_all_deps.py',
        'copy_more_deps.py',
        'copy_typing_ext.py',
        'check_pip.py',
        'check_python.py',
        'fix_venv.py',
        'reinstall_crypto.py',
        'deploy_v4.1.py',
        'deploy_v4.2.py',
        'update_runsh.py',
        'update_runsh2.py',
        'update_runsh_final.py',
        'update_remote_scripts.py',
        'reupload_files.py',
        'check_upload.py',
        'check_device_packages.py',
        'setup_ascend.py'
    ],
    'diagnostics': [
        'full_ascend_test.py',
        'simple_diag.py',
        'remote_diagnose.py',
        'remote_diagnosis.py',
        'jetson_full_test_v4.py',
        'test_ascend.py',
        'check_results.py',
        'check_remote.py'
    ],
    'network': [
        'lan_scan.py',
        'scan_ports.py',
        'deep_network_diagnosis.py',
        'test_network_192.168.1.103.py',
        'test_network_hardware.py',
        'scan_and_test.py'
    ],
    'remote': [
        'remote_test.py',
        'remote_test_new.py',
        'remote_test_100.py',
        'run_remote.py',
        'test_connect.py',
        'test_ssh_connect.py',
        'uninstall_remote.py',
        'remote_uninstall.py',
        'run_test.py'
    ],
    'debug': [
        'debug_ssh.py',
        'test_passwords.py',
        'test_pydantic.py'
    ],
    'tests': [
        # tests目录已有，不需要移动
    ]
}

def organize_files():
    """执行文件归类"""
    print('🚀 开始NASTool项目文件归类整理...')
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建目录
    for category in CATEGORIES.keys():
        cat_dir = os.path.join(root_dir, category)
        os.makedirs(cat_dir, exist_ok=True)
        print(f'📁 确保目录存在: {category}/')
    
    # 移动文件
    moved_count = 0
    skipped_count = 0
    
    for category, files in CATEGORIES.items():
        cat_dir = os.path.join(root_dir, category)
        
        for filename in files:
            src_path = os.path.join(root_dir, filename)
            dst_path = os.path.join(cat_dir, filename)
            
            if os.path.exists(src_path):
                if os.path.exists(dst_path):
                    # 如果目标已存在，检查是否相同
                    if os.path.samefile(src_path, dst_path):
                        print(f'⚠️ 跳过 (已在目标位置): {filename}')
                        skipped_count += 1
                        continue
                    else:
                        # 目标存在但不同，重命名源文件
                        base, ext = os.path.splitext(filename)
                        new_name = f'{base}_old{ext}'
                        new_path = os.path.join(root_dir, new_name)
                        os.rename(src_path, new_path)
                        print(f'📝 重命名已存在文件: {filename} -> {new_name}')
                        skipped_count += 1
                        continue
                
                shutil.move(src_path, dst_path)
                print(f'✅ 移动: {filename} -> {category}/')
                moved_count += 1
            else:
                print(f'🔍 文件不存在: {filename}')
                skipped_count += 1
    
    print()
    print('='*60)
    print(f'📊 归类完成!')
    print(f'   移动文件: {moved_count}')
    print(f'   跳过/忽略: {skipped_count}')
    print('='*60)
    
    # 显示剩余的根目录文件
    show_remaining_files(root_dir)

def show_remaining_files(root_dir):
    """显示根目录剩余文件"""
    print('\n📋 根目录剩余文件:')
    print('-'*40)
    
    remaining = []
    for item in os.listdir(root_dir):
        item_path = os.path.join(root_dir, item)
        if os.path.isfile(item_path) and item.endswith('.py'):
            remaining.append(item)
    
    if remaining:
        for item in sorted(remaining):
            print(f'  {item}')
    else:
        print('  (无剩余Python文件)')
    
    print('-'*40)

if __name__ == '__main__':
    organize_files()
