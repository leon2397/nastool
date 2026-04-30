#!/usr/bin/env python3
"""NASTool v4.2 本地部署测试脚本"""

import os
import sys
import shutil

def deploy_nastool():
    """部署NASTool到tool目录"""
    print('='*60)
    print('🚀 NASTool v4.2 本地部署')
    print('='*60)
    
    # 确保在tool目录下运行
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current_dir) != 'tool':
        print('❌ 请在tool目录下运行此脚本')
        sys.exit(1)
    
    # 定义源目录和目标目录
    project_root = os.path.dirname(current_dir)
    
    modules = [
        'nastool-core',
        'nastool-common',
        'nastool-adapters',
        'nastool-reporters',
        'nastool-cli',
        'nastool-fixes'
    ]
    
    print('\n📦 复制模块...')
    for module in modules:
        src = os.path.join(project_root, module)
        dst = os.path.join(current_dir, 'bin', module)
        
        if os.path.exists(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f'✅ 复制 {module}')
        else:
            print(f'⚠️ 跳过 {module} (不存在)')
    
    # 创建启动脚本
    print('\n📝 创建启动脚本...')
    with open(os.path.join(current_dir, 'run_diagnose.py'), 'w', encoding='utf-8') as f:
        f.write('''#!/usr/bin/env python3
"""NASTool v4.2 诊断启动脚本"""

import sys
import os

# 设置模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bin', 'nastool-cli'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bin', 'nastool-core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bin', 'nastool-adapters'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bin', 'nastool-common'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bin', 'nastool-fixes'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bin', 'nastool-reporters'))

from nastool_core.quick_diagnose import QuickDiagnose

def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = 'quick'
    
    print(f'🚀 启动 {mode} 诊断模式...')
    d = QuickDiagnose(mode)
    d.run()

if __name__ == '__main__':
    main()
''')
    print('✅ 创建 run_diagnose.py')
    
    # 创建卸载脚本
    with open(os.path.join(current_dir, 'uninstall.py'), 'w', encoding='utf-8') as f:
        f.write('''#!/usr/bin/env python3
"""NASTool v4.2 卸载脚本"""

import os
import sys
import shutil

def uninstall():
    print('='*60)
    print('🗑️ NASTool v4.2 卸载')
    print('='*60)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print('\\n⚠️ 即将删除以下内容:')
    print('   - bin/ 目录 (NASTool模块)')
    print('   - run_diagnose.py')
    print('   - uninstall.py')
    print('\\n注意: 此操作不会影响系统文件')
    
    confirm = input('\\n确认卸载? [y/N]: ').strip().lower()
    if confirm != 'y':
        print('❌ 取消卸载')
        sys.exit(0)
    
    print('\\n🔄 开始卸载...')
    
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
    
    print('\\n✅ 卸载完成!')
    print('='*60)

if __name__ == '__main__':
    uninstall()
''')
    print('✅ 创建 uninstall.py')
    
    print('\n🎉 部署完成!')
    print('='*60)
    print('使用方法:')
    print('  python run_diagnose.py quick    # 快速诊断')
    print('  python run_diagnose.py full     # 完整诊断')
    print('  python run_diagnose.py network  # 网络诊断')
    print('  python run_diagnose.py hardware # 硬件诊断')
    print('  python uninstall.py             # 卸载')
    print('='*60)

if __name__ == '__main__':
    deploy_nastool()
