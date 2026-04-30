#!/usr/bin/env python3
"""NASTool v4.5 - 智能诊断工具 (完整功能版)
整合所有144个检测功能、修复引擎和报告器
"""

import os
import sys
import time

# 添加工具路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

def main():
    """主入口函数"""
    print_banner()
    
    while True:
        print_main_menu()
        choice = input('\n输入选择 [0-13]: ').strip()
        
        if choice == '1':
            run_device_manager()
        elif choice == '2':
            run_test_engine()
        elif choice == '3':
            run_deploy_manager()
        elif choice == '4':
            run_report_manager()
        elif choice == '5':
            run_network_scan()
        elif choice == '6':
            run_setup_wizard()
        elif choice == '7':
            run_performance_monitor()
        elif choice == '8':
            run_health_checker()
        elif choice == '9':
            run_checker_registry()
        elif choice == '10':
            run_adapter_registry()
        elif choice == '11':
            run_fix_engine()
        elif choice == '12':
            run_cli_registry()
        elif choice == '13':
            run_feature_summary()
        elif choice == '0':
            print('\n👋 再见!')
            break
        else:
            print('❌ 无效选择，请重新输入')

def print_banner():
    """打印欢迎横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                      NASTool v4.5                           ║
║              智能设备诊断工具 (整合144个功能)                ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_main_menu():
    """打印主菜单"""
    menu = """
┌────────────────────────────────────────────────────────────┐
│                      主菜单                                │
├────────────────────────────────────────────────────────────┤
│  1 📋 设备管理          管理测试设备列表                    │
│  2 🧪 设备测试          执行设备诊断测试                    │
│  3 📦 设备部署          部署NASTool到设备                  │
│  4 📊 报告管理          查看和管理测试报告                  │
│  5 🔍 网络扫描          扫描局域网设备                      │
│  6 ⚙️ 系统配置          配置系统参数                        │
│  7 📈 性能监控          实时性能监控                        │
│  8 🏥 健康检查          系统健康诊断                        │
│  9 🔍 检测器列表        查看所有92个检测功能                │
│ 10 🔌 适配器列表        查看所有30个硬件适配器              │
│ 11 🔧 修复引擎          运行自动修复功能(15个)              │
│ 12 💻 CLI命令          命令行工具(8个)                     │
│ 13 📊 功能汇总          查看所有156个功能统计               │
│  0 🚪 退出              退出程序                            │
└────────────────────────────────────────────────────────────┘
    """
    print(menu)

def run_device_manager():
    """运行设备管理"""
    clear_screen()
    print('='*60)
    print('📋 设备管理')
    print('='*60)
    
    while True:
        print('\n设备管理操作:')
        print('┌─────────────────────────────────┐')
        print('│ 1. 添加设备                     │')
        print('│ 2. 删除设备                     │')
        print('│ 3. 更新设备                     │')
        print('│ 4. 查看设备列表                 │')
        print('│ 5. 检查设备状态                 │')
        print('│ 0. 返回主菜单                   │')
        print('└─────────────────────────────────┘')
        
        choice = input('\n输入选择 [0-5]: ').strip()
        
        if choice == '1':
            add_device()
        elif choice == '2':
            remove_device()
        elif choice == '3':
            update_device()
        elif choice == '4':
            list_devices()
        elif choice == '5':
            check_status()
        elif choice == '0':
            clear_screen()
            break
        else:
            print('❌ 无效选择')

def add_device():
    """添加设备"""
    print('\n--- 添加新设备 ---')
    name = input('设备名称: ').strip()
    if not name:
        print('❌ 设备名称不能为空')
        return
    
    ip = input('IP地址: ').strip()
    if not ip:
        print('❌ IP地址不能为空')
        return
    
    username = input('用户名 (默认 root): ').strip() or 'root'
    password = input('密码: ').strip()
    device_type = input('设备类型 (ascend/jetson/generic, 默认 generic): ').strip() or 'generic'
    
    cmd = f'{sys.executable} tools/device_manager.py add "{name}" "{ip}" -u "{username}" -pw "{password}" -t "{device_type}"'
    os.system(cmd)
    wait_for_enter()

def remove_device():
    """删除设备"""
    list_devices()
    device_id = input('\n输入要删除的设备ID: ').strip()
    if device_id:
        cmd = f'{sys.executable} tools/device_manager.py remove "{device_id}"'
        os.system(cmd)
    wait_for_enter()

def update_device():
    """更新设备"""
    list_devices()
    device_id = input('\n输入要更新的设备ID: ').strip()
    if not device_id:
        return
    
    print('\n输入新信息 (回车跳过表示不修改):')
    name = input('新名称: ').strip()
    ip = input('新IP地址: ').strip()
    
    cmd = f'{sys.executable} tools/device_manager.py update "{device_id}"'
    if name: cmd += f' -n "{name}"'
    if ip: cmd += f' -i "{ip}"'
    
    os.system(cmd)
    wait_for_enter()

def list_devices():
    """列出设备"""
    os.system(f'{sys.executable} tools/device_manager.py list')

def check_status():
    """检查设备状态"""
    os.system(f'{sys.executable} tools/device_manager.py status')
    wait_for_enter()

def run_test_engine():
    """运行测试引擎"""
    clear_screen()
    print('='*60)
    print('🧪 设备测试')
    print('='*60)
    
    # 列出设备
    list_devices()
    
    print('\n测试模式:')
    print('┌─────────────────────────────────┐')
    print('│ 1. quick   - 快速诊断           │')
    print('│ 2. full    - 完整诊断           │')
    print('│ 3. network - 网络专项           │')
    print('│ 4. hardware - 硬件专项          │')
    print('└─────────────────────────────────┘')
    
    mode_choice = input('\n输入模式 [1-4]: ').strip()
    modes = {'1': 'quick', '2': 'full', '3': 'network', '4': 'hardware'}
    mode = modes.get(mode_choice, 'quick')
    
    print('\n测试方式:')
    print('┌─────────────────────────────────┐')
    print('│ 1. 单个设备测试                 │')
    print('│ 2. 批量设备测试                 │')
    print('└─────────────────────────────────┘')
    
    test_type = input('输入测试方式 [1-2]: ').strip()
    
    if test_type == '1':
        device_id = input('输入设备ID: ').strip()
        if device_id:
            print(f'\n🚀 开始测试设备 {device_id}...')
            cmd = f'{sys.executable} tools/test_engine.py test "{device_id}" -m {mode}'
            os.system(cmd)
        else:
            print('❌ 设备ID不能为空')
    elif test_type == '2':
        device_ids = input('输入设备ID列表 (空格分隔): ').strip()
        if device_ids:
            print(f'\n🚀 开始批量测试...')
            cmd = f'{sys.executable} tools/test_engine.py batch {device_ids} -m {mode}'
            os.system(cmd)
        else:
            print('❌ 设备ID列表不能为空')
    
    wait_for_enter()

def run_deploy_manager():
    """运行部署管理器"""
    clear_screen()
    print('='*60)
    print('📦 设备部署')
    print('='*60)
    
    list_devices()
    
    while True:
        print('\n部署操作:')
        print('┌─────────────────────────────────┐')
        print('│ 1. 部署到单个设备               │')
        print('│ 2. 批量部署                     │')
        print('│ 3. 从设备卸载                   │')
        print('│ 4. 检查设备环境                 │')
        print('│ 0. 返回主菜单                   │')
        print('└─────────────────────────────────┘')
        
        choice = input('\n输入选择 [0-4]: ').strip()
        
        if choice == '1':
            device_id = input('设备ID: ').strip()
            if device_id:
                cmd = f'{sys.executable} tools/deploy/deploy_manager.py deploy "{device_id}"'
                os.system(cmd)
        elif choice == '2':
            device_ids = input('设备ID列表 (空格分隔): ').strip()
            if device_ids:
                cmd = f'{sys.executable} tools/deploy/deploy_manager.py batch {device_ids}'
                os.system(cmd)
        elif choice == '3':
            device_id = input('设备ID: ').strip()
            if device_id:
                cmd = f'{sys.executable} tools/deploy/deploy_manager.py uninstall "{device_id}"'
                os.system(cmd)
        elif choice == '4':
            device_id = input('设备ID: ').strip()
            if device_id:
                cmd = f'{sys.executable} tools/deploy/deploy_manager.py check "{device_id}"'
                os.system(cmd)
        elif choice == '0':
            clear_screen()
            break
        else:
            print('❌ 无效选择')
        
        if choice in ['1', '2', '3', '4']:
            wait_for_enter()

def run_report_manager():
    """运行报告管理器"""
    clear_screen()
    print('='*60)
    print('📊 报告管理')
    print('='*60)
    
    os.system(f'{sys.executable} tools/report_manager.py list')
    
    while True:
        print('\n报告操作:')
        print('┌─────────────────────────────────┐')
        print('│ 1. 查看报告详情                 │')
        print('│ 2. 对比报告                     │')
        print('│ 3. 导出报告                     │')
        print('│ 4. 设备测试汇总                 │')
        print('│ 0. 返回主菜单                   │')
        print('└─────────────────────────────────┘')
        
        choice = input('\n输入选择 [0-4]: ').strip()
        
        if choice == '1':
            report_id = input('报告ID: ').strip()
            if report_id:
                cmd = f'{sys.executable} tools/report_manager.py show "{report_id}"'
                os.system(cmd)
                wait_for_enter()
        elif choice == '2':
            report_ids = input('报告ID列表 (空格分隔): ').strip()
            if report_ids:
                cmd = f'{sys.executable} tools/report_manager.py compare {report_ids}'
                os.system(cmd)
                wait_for_enter()
        elif choice == '3':
            report_id = input('报告ID: ').strip()
            if report_id:
                fmt = input('导出格式 (json/html, 默认 json): ').strip() or 'json'
                cmd = f'{sys.executable} tools/report_manager.py export "{report_id}" -f {fmt}'
                os.system(cmd)
                wait_for_enter()
        elif choice == '4':
            device_id = input('设备ID: ').strip()
            if device_id:
                cmd = f'{sys.executable} tools/report_manager.py summary "{device_id}"'
                os.system(cmd)
                wait_for_enter()
        elif choice == '0':
            clear_screen()
            break
        else:
            print('❌ 无效选择')

def run_network_scan():
    """运行网络扫描"""
    clear_screen()
    print('='*60)
    print('🔍 网络扫描')
    print('='*60)
    
    subnet = input('输入子网 (默认: 192.168.1.): ').strip() or '192.168.1.'
    print(f'\n正在扫描子网 {subnet}...')
    os.system(f'{sys.executable} tools/device_manager.py scan --subnet "{subnet}"')
    
    wait_for_enter()

def run_setup_wizard():
    """运行配置向导"""
    clear_screen()
    os.system(f'{sys.executable} tools/setup_wizard.py')
    wait_for_enter()
    clear_screen()

def run_performance_monitor():
    """运行性能监控"""
    clear_screen()
    print('='*60)
    print('📈 性能监控')
    print('='*60)
    
    print('\n性能监控操作:')
    print('┌─────────────────────────────────┐')
    print('│ 1. 本地性能监控                 │')
    print('│ 2. 远程设备性能监控             │')
    print('│ 0. 返回主菜单                   │')
    print('└─────────────────────────────────┘')
    
    choice = input('\n输入选择 [0-2]: ').strip()
    
    if choice == '1':
        duration = input('监控时长(秒，默认10): ').strip() or '10'
        cmd = f'{sys.executable} tools/performance_monitor.py start -d {duration}'
        os.system(cmd)
    elif choice == '2':
        list_devices()
        device_id = input('\n输入设备ID: ').strip()
        if device_id:
            duration = input('监控时长(秒，默认10): ').strip() or '10'
            cmd = f'{sys.executable} tools/performance_monitor.py start -d {duration} -dev {device_id}'
            os.system(cmd)
    
    wait_for_enter()

def run_health_checker():
    """运行健康检查"""
    clear_screen()
    print('='*60)
    print('🏥 系统健康检查')
    print('='*60)
    
    cmd = f'{sys.executable} tools/health_checker.py'
    os.system(cmd)
    
    wait_for_enter()

def list_tools():
    """列出工具目录"""
    clear_screen()
    print('='*60)
    print('📁 工具目录结构')
    print('='*60)
    
    tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools')
    
    for root, dirs, files in os.walk(tools_dir):
        level = root.replace(tools_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f'{subindent}{file}')
    
    print('='*60)
    wait_for_enter()

def run_checker_registry():
    """运行检测器注册表"""
    clear_screen()
    os.system(f'{sys.executable} tools/checker_registry.py')
    wait_for_enter()

def run_adapter_registry():
    """运行适配器注册表"""
    clear_screen()
    os.system(f'{sys.executable} tools/adapter_registry.py')
    wait_for_enter()

def run_fix_engine():
    """运行修复引擎"""
    clear_screen()
    print('='*60)
    print('🔧 修复引擎')
    print('='*60)
    
    os.system(f'{sys.executable} tools/fix_registry.py')
    wait_for_enter()

def run_cli_registry():
    """运行CLI命令注册表"""
    clear_screen()
    os.system(f'{sys.executable} tools/cli_registry.py')
    wait_for_enter()

def run_feature_summary():
    """运行功能汇总"""
    clear_screen()
    os.system(f'{sys.executable} tools/feature_manager.py')
    wait_for_enter()

def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')

def wait_for_enter():
    """等待用户按回车"""
    input('\n按 Enter 键继续...')
    clear_screen()

if __name__ == '__main__':
    main()
