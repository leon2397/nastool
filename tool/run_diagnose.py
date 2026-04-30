#!/usr/bin/env python3
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
