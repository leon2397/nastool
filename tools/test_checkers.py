#!/usr/bin/env python3
"""
NASTool 检测器实际测试工具
在局域网内测试所有检测器的功能
"""
import os
import sys
import time
import subprocess

# 设置路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'nastool-core'))

def test_local_checkers():
    """测试本地检测器"""
    print("🔍 开始测试本地检测器...")
    print("="*60)
    
    from unified_checker_executor import UnifiedCheckerExecutor
    executor = UnifiedCheckerExecutor()
    
    # 按类别测试
    categories = ['system', 'network', 'storage', 'security', 'ai', 'nas', 'usb']
    
    for category in categories:
        print(f"\n📁 测试 {category} 类别检测器:")
        print("-" * 40)
        
        # 获取该类别的检测器
        category_checkers = [c for c in executor.checkers if c.get('category') == category]
        
        if not category_checkers:
            print(f"   ❌ 没有找到 {category} 类别的检测器")
            continue
        
        passed = 0
        failed = 0
        
        for checker in category_checkers:
            checker_id = checker['id']
            name = checker.get('name', checker_id)
            
            try:
                # 执行检测器
                result = executor.execute_checker(checker_id)
                
                if result.get('status') == 'success':
                    status = "✅"
                    passed += 1
                    result_data = result.get('result', {})
                    if isinstance(result_data, dict):
                        detail = result_data.get('summary', result_data.get('message', '检测通过'))
                    else:
                        detail = str(result_data)[:50]
                elif result.get('status') == 'warning':
                    status = "⚠️"
                    failed += 1
                    detail = result.get('message', '检测警告')
                else:
                    status = "❌"
                    failed += 1
                    detail = result.get('message', '检测失败')
                
                print(f"   {status} {name}: {detail}")
                
            except Exception as e:
                status = "❌"
                failed += 1
                print(f"   {status} {name}: 异常 - {str(e)}")
        
        print(f"\n   📊 统计: {passed} 通过, {failed} 失败")
    
    print("\n" + "="*60)
    print("✅ 本地检测器测试完成")

def test_network_scan():
    """测试网络扫描功能"""
    print("\n🌐 开始网络扫描测试...")
    print("="*60)
    
    # 测试网络相关检测器
    from unified_checker_executor import UnifiedCheckerExecutor
    executor = UnifiedCheckerExecutor()
    
    network_checkers = [
        'network.network_status_checker',
        'network.dns_diagnostic',
        'network.network_quality_checker'
    ]
    
    print("\n测试网络检测器:")
    for checker_id in network_checkers:
        try:
            print(f"\n   🔍 正在测试 {checker_id}...")
            result = executor.execute_checker(checker_id)
            
            if result.get('status') == 'success':
                print(f"   ✅ {checker_id}: 成功")
                if 'result' in result:
                    result_data = result['result']
                    if isinstance(result_data, dict):
                        for key, value in result_data.items():
                            if isinstance(value, dict):
                                for k, v in value.items():
                                    print(f"      - {k}: {v}")
                            else:
                                print(f"      - {key}: {value}")
                    else:
                        print(f"      - 结果: {result_data}")
            else:
                print(f"   ❌ {checker_id}: {result.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"   ❌ {checker_id}: 异常 - {str(e)}")
    
    print("\n" + "="*60)
    print("✅ 网络扫描测试完成")

def test_system_info():
    """测试系统信息收集"""
    print("\n🖥️ 开始系统信息收集测试...")
    print("="*60)
    
    from unified_checker_executor import UnifiedCheckerExecutor
    executor = UnifiedCheckerExecutor()
    
    system_checkers = [
        'system.cpu_info',
        'system.memory_check',
        'system.disk_usage',
        'system.python_version',
        'system.os_info'
    ]
    
    print("\n测试系统信息检测器:")
    for checker_id in system_checkers:
        try:
            print(f"\n   🔍 正在测试 {checker_id}...")
            result = executor.execute_checker(checker_id)
            
            if result.get('status') == 'success':
                print(f"   ✅ {checker_id}: 成功")
                if 'result' in result:
                    # 格式化输出结果
                    result_data = result['result']
                    if isinstance(result_data, dict):
                        for key, value in result_data.items():
                            # 跳过复杂对象
                            if isinstance(value, (dict, list)) and len(str(value)) > 50:
                                print(f"      - {key}: (复杂数据)")
                            else:
                                print(f"      - {key}: {value}")
                    else:
                        print(f"      - 结果: {result_data}")
                else:
                    print(f"      - 无返回数据")
            else:
                print(f"   ❌ {checker_id}: {result.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"   ❌ {checker_id}: 异常 - {str(e)}")
    
    print("\n" + "="*60)
    print("✅ 系统信息测试完成")

def main():
    """主测试函数"""
    print("🚀 NASTool 实际功能测试")
    print("="*60)
    print("测试环境: 局域网本地机器")
    print("时间: " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    # 测试本地检测器
    test_local_checkers()
    
    # 测试网络扫描
    test_network_scan()
    
    # 测试系统信息
    test_system_info()
    
    print("\n🎉 所有测试完成！")
    print("="*60)

if __name__ == '__main__':
    main()
