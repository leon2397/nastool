#!/usr/bin/env python3
"""NASTool v4.2 本地功能测试套件"""

import sys
import os

# 添加NASTool模块路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_quick_diagnose():
    """测试快速诊断模块"""
    print('🔍 [1/6] 测试快速诊断模块...')
    try:
        from nastool_core.quick_diagnose import QuickDiagnose
        
        # 测试快速模式
        d = QuickDiagnose('quick')
        results = d.run()
        print('✅ 快速诊断模块正常')
        return True
    except Exception as e:
        print(f'❌ 快速诊断模块异常: {e}')
        return False

def test_network_diagnostic():
    """测试网络诊断模块"""
    print('🔍 [2/6] 测试网络诊断模块...')
    try:
        from nastool_core.checks.network.network_status_checker import NetworkStatusChecker
        
        checker = NetworkStatusChecker()
        
        # 测试网络接口检查
        interfaces = checker.check_network_interfaces()
        print(f'  - 网络接口检查: 发现 {len(interfaces)} 个接口')
        
        # 测试连接性检查
        connectivity = checker.check_connectivity()
        print(f'  - 连接性检查: {sum(1 for c in connectivity if c["connected"])} 个连接正常')
        
        # 测试Ping稳定性
        result = checker.check_ping_stability('8.8.8.8', count=3)
        print(f'  - Ping稳定性: {result.get("packet_loss", "N/A")}% 丢包率')
        
        # 测试DNS解析
        dns_result = checker.check_dns_resolution()
        print(f'  - DNS解析: {len(dns_result)} 个域名')
        
        print('✅ 网络诊断模块正常')
        return True
    except Exception as e:
        print(f'❌ 网络诊断模块异常: {e}')
        return False

def test_network_quality():
    """测试网络质量检查模块"""
    print('🔍 [3/6] 测试网络质量检查模块...')
    try:
        from nastool_core.checks.network.network_quality_checker import NetworkQualityChecker
        
        checker = NetworkQualityChecker()
        
        # 测试带宽检查
        result = checker.check_bandwidth()
        if result['download_speed_mbps']:
            print(f'  - 下载速度: {result["download_speed_mbps"]} Mbps')
        else:
            print(f'  - 带宽测试: 跳过(需要speedtest-cli)')
        
        print('✅ 网络质量检查模块正常')
        return True
    except Exception as e:
        print(f'❌ 网络质量检查模块异常: {e}')
        return False

def test_dns_diagnostic():
    """测试DNS诊断模块"""
    print('🔍 [4/6] 测试DNS诊断模块...')
    try:
        from nastool_core.checks.network.dns_diagnostic import DNSDiagnostic
        
        dns = DNSDiagnostic()
        
        # 测试DNS配置检查
        config = dns.check_dns_configuration()
        print(f'  - DNS配置检查: {len(config)} 项')
        
        # 测试DNS服务器检查
        servers = dns.check_dns_servers()
        print(f'  - DNS服务器检查: {len(servers)} 个服务器')
        
        print('✅ DNS诊断模块正常')
        return True
    except Exception as e:
        print(f'❌ DNS诊断模块异常: {e}')
        return False

def test_ascend_checker():
    """测试昇腾芯片检测模块"""
    print('🔍 [5/6] 测试昇腾芯片检测模块...')
    try:
        from nastool_core.checks.ai.ascend_checker import AscendChecker
        
        checker = AscendChecker()
        hardware = checker.detect_ascend_hardware()
        print(f'  - 硬件检测: {"发现昇腾芯片" if hardware else "未发现昇腾芯片"}')
        
        print('✅ 昇腾芯片检测模块正常')
        return True
    except Exception as e:
        print(f'❌ 昇腾芯片检测模块异常: {e}')
        return False

def test_progress():
    """测试进度可视化模块"""
    print('🔍 [6/6] 测试进度可视化模块...')
    try:
        from nastool_common.utils.progress import ProgressBar, ProgressTracker
        
        pb = ProgressBar(total=100)
        pb.update(50, '测试中')
        pb.update(100, '完成')
        
        print('✅ 进度可视化模块正常')
        return True
    except Exception as e:
        print(f'❌ 进度可视化模块异常: {e}')
        return False

def main():
    print('='*60)
    print('🚀 NASTool v4.2 本地功能测试')
    print('='*60)
    
    tests = [
        test_quick_diagnose,
        test_network_diagnostic,
        test_network_quality,
        test_dns_diagnostic,
        test_ascend_checker,
        test_progress
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print('\n' + '='*60)
    print('📊 测试结果汇总')
    print('='*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f'通过: {passed}/{total}')
    
    if passed == total:
        print('🎉 所有测试通过!')
    else:
        print(f'⚠️ 有 {total - passed} 个测试失败')
    
    print('='*60)
    
    # 生成测试报告
    report = {
        'version': '4.2',
        'passed': passed,
        'total': total,
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }
    
    # 保存报告
    with open('test_report.json', 'w', encoding='utf-8') as f:
        __import__('json').dump(report, f, ensure_ascii=False, indent=2)
    
    print('📝 测试报告已保存到 test_report.json')

if __name__ == '__main__':
    main()
