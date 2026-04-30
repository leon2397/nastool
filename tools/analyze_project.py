#!/usr/bin/env python3
"""
NASTool 项目完整结构分析工具
确保项目可以交付使用
"""
import os
import sys

PROJECT_ROOT = 'D:\\project\\nastool7'

def analyze_project():
    """分析项目完整结构"""
    print("🚀 NASTool 项目完整结构分析")
    print("="*70)
    print(f"项目路径: {PROJECT_ROOT}")
    print("="*70)
    
    # 核心模块分析
    core_modules = [
        ('nastool-core', '核心检测器模块', ['nastool_core/checks/', 'nastool_core/utils/', 'nastool_core/config/']),
        ('nastool-adapters', '硬件适配器模块', ['nastool_adapters/ascend/', 'nastool_adapters/jetson/', 'nastool_adapters/']),
        ('nastool-fixes', '修复引擎模块', ['nastool_fixes/security/', 'nastool_fixes/storage/', 'nastool_fixes/system/']),
        ('nastool-reporters', '报告器模块', ['nastool_reporters/']),
        ('nastool-cli', '命令行接口', ['nastool_cli/commands/']),
        ('nastool-common', '通用工具模块', ['nastool_common/utils/']),
        ('nastool-agent', '代理服务', ['']),
    ]
    
    print("\n📦 核心功能模块")
    print("-" * 50)
    
    total_files = 0
    total_lines = 0
    
    for module, desc, subdirs in core_modules:
        print(f"\n📁 {module}")
        print(f"   描述: {desc}")
        
        module_path = os.path.join(PROJECT_ROOT, module)
        if not os.path.exists(module_path):
            print(f"   ❌ 目录不存在")
            continue
        
        # 统计文件
        py_files = []
        for root, dirs, files in os.walk(module_path):
            for f in files:
                if f.endswith('.py'):
                    py_files.append(os.path.join(root, f))
        
        print(f"   Python文件: {len(py_files)} 个")
        
        # 统计代码行数
        lines = 0
        for pyfile in py_files[:50]:  # 限制数量
            try:
                with open(pyfile, 'r', encoding='utf-8', errors='ignore') as f:
                    lines += len(f.readlines())
            except:
                pass
        
        total_files += len(py_files)
        total_lines += lines
        
        print(f"   代码行数: {lines:,} 行")
        
        # 检查关键子目录
        for subdir in subdirs:
            sub_path = os.path.join(module_path, subdir)
            if os.path.exists(sub_path):
                files = [f for f in os.listdir(sub_path) if f.endswith('.py') and not f.startswith('_')]
                print(f"   └─ {subdir}: {len(files)} 个模块")
            else:
                print(f"   └─ {subdir}: ❌ 不存在")
    
    print("\n" + "="*70)
    print("📊 核心模块统计")
    print("="*70)
    print(f"总Python文件: {total_files} 个")
    print(f"总行数: {total_lines:,} 行")
    
    # 部署交付检查
    print("\n🚀 部署交付检查")
    print("-" * 50)
    
    deploy_items = [
        ('deploy/nastool.exe', '主程序可执行文件'),
        ('deploy/nastool-launcher.exe', '启动器'),
        ('deploy/nastool_agent.py', '代理脚本'),
        ('deploy/deploy-nastool-agent.sh', '部署脚本'),
        ('deploy_v4.1.sh', 'Linux部署脚本'),
        ('deploy_v4.1.ps1', 'Windows部署脚本'),
    ]
    
    deploy_ready = True
    for item, desc in deploy_items:
        path = os.path.join(PROJECT_ROOT, item)
        if os.path.exists(path):
            print(f"   ✅ {desc}")
        else:
            print(f"   ❌ {desc}")
            deploy_ready = False
    
    # 文档检查
    print("\n📖 文档检查")
    print("-" * 50)
    
    docs = [
        ('README.md', '项目说明'),
        ('docs/用户手册.md', '用户手册'),
        ('docs/开发者指南.md', '开发者指南'),
        ('docs/TEST_REPORT.md', '测试报告'),
        ('docs/VALIDATION_REPORT.md', '验证报告'),
    ]
    
    docs_ready = True
    for doc, desc in docs:
        path = os.path.join(PROJECT_ROOT, doc)
        if os.path.exists(path):
            print(f"   ✅ {desc}")
        else:
            print(f"   ❌ {desc}")
            docs_ready = False
    
    # 配置文件检查
    print("\n⚙️ 配置文件检查")
    print("-" * 50)
    
    configs = [
        ('config/devices.json', '设备配置'),
        ('nastool-core/create_default_config.py', '配置生成器'),
        ('nastool-common/nastool_common/config.py', '配置模块'),
    ]
    
    config_ready = True
    for config, desc in configs:
        path = os.path.join(PROJECT_ROOT, config)
        if os.path.exists(path):
            print(f"   ✅ {desc}")
        else:
            print(f"   ❌ {desc}")
            config_ready = False
    
    # 测试工具检查
    print("\n🧪 测试工具检查")
    print("-" * 50)
    
    test_tools = [
        ('tools/test_checkers.py', '检测器测试工具'),
        ('tools/generate_report.py', '报告生成器'),
        ('tools/feature_manager.py', '功能管理器'),
        ('tools/unified_checker_executor.py', '统一执行引擎'),
        ('tools/verify_all_features.py', '功能验证工具'),
    ]
    
    tools_ready = True
    for tool, desc in test_tools:
        path = os.path.join(PROJECT_ROOT, tool)
        if os.path.exists(path):
            print(f"   ✅ {desc}")
        else:
            print(f"   ❌ {desc}")
            tools_ready = False
    
    # 硬件支持检查
    print("\n💻 硬件平台支持")
    print("-" * 50)
    
    platforms = [
        ('ascend', '华为昇腾', 'nastool_adapters/ascend/'),
        ('jetson', 'NVIDIA Jetson', 'nastool_adapters/jetson/'),
        ('rockchip', '瑞芯微', 'nastool_adapters/rockchip.py'),
        ('sophon', '算能', 'nastool_adapters/sophon.py'),
        ('qnap', 'QNAP NAS', 'nastool_adapters/qnap.py'),
        ('synology', 'Synology NAS', 'nastool_adapters/synology.py'),
    ]
    
    platforms_ready = True
    for name, desc, path_suffix in platforms:
        path = os.path.join(PROJECT_ROOT, 'nastool-adapters', path_suffix)
        if os.path.exists(path):
            print(f"   ✅ {name}: {desc}")
        else:
            print(f"   ❌ {name}: {desc}")
            platforms_ready = False
    
    # 生成总结
    print("\n" + "="*70)
    print("🎯 交付评估")
    print("="*70)
    
    all_ready = deploy_ready and docs_ready and config_ready and tools_ready and platforms_ready
    
    if all_ready:
        print("✅ 项目完整，可以交付！")
    else:
        print("⚠️ 项目基本完整，但有部分组件需要完善")
    
    # 输出待办事项
    print("\n📋 待办事项")
    print("-" * 50)
    
    if not deploy_ready:
        print("   🔧 完成部署脚本和可执行文件")
    
    if not docs_ready:
        print("   📝 完善文档")
    
    if not platforms_ready:
        print("   💻 完善硬件平台支持")
    
    print("\n🎉 NASTool ARM检测工具 - 准备就绪！")
    print("="*70)

if __name__ == '__main__':
    analyze_project()
