#!/usr/bin/env python3
"""NASTool v4.2 局域网扫描工具"""

from nastool_core.checks.network.network_status_checker import NetworkStatusChecker
import subprocess
import platform

def scan_local_network():
    """扫描局域网设备"""
    print('🔍 正在扫描局域网...')
    
    if platform.system() == 'Windows':
        ping_cmd = 'ping -n 1 -w 500'
    else:
        ping_cmd = 'ping -c 1 -W 1'
    
    devices = {}
    # 扫描常见IP范围
    for i in range(1, 255):
        ip = f'192.168.1.{i}'
        try:
            result = subprocess.run(
                f'{ping_cmd} {ip}',
                shell=True,
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                devices[ip] = {'status': 'reachable'}
                print(f'✅ {ip}')
        except:
            pass
    
    return devices

def main():
    print('='*60)
    print('📡 NASTool v4.2 网络诊断')
    print('='*60)
    
    # 使用NetworkStatusChecker检查网络状态
    checker = NetworkStatusChecker()
    
    print('\n[1/3] 检查网络接口...')
    interfaces = checker.check_network_interfaces()
    if interfaces:
        print(f'发现 {len(interfaces)} 个网络接口:')
        for iface in interfaces:
            status = iface.get('status', 'unknown')
            print(f'  - {iface["name"]}: {status}')
    
    print('\n[2/3] 检查网络连接性...')
    connectivity = checker.check_connectivity()
    print('连接测试结果:')
    for conn in connectivity:
        status = '✅' if conn['connected'] else '❌'
        latency = conn['latency_ms']
        print(f'  {status} {conn["name"]} ({conn["host"]}): {latency}ms')
    
    print('\n[3/3] 扫描局域网设备...')
    devices = scan_local_network()
    
    if devices:
        print(f'\n🎉 发现 {len(devices)} 个设备:')
        print('-' * 50)
        for ip in devices.keys():
            print(f'  {ip}')
        print('-' * 50)
    else:
        print('⚠️ 未发现局域网设备')
    
    print('\n' + '='*60)
    print('✅ 诊断完成')
    print('='*60)

if __name__ == '__main__':
    main()
