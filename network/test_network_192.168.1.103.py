#!/usr/bin/env python3
"""
测试到192.168.1.103的网络连接
"""

from nastool_core.checks.network.network_status_checker import NetworkStatusChecker

def main():
    # 创建网络状态检查器
    checker = NetworkStatusChecker()
    
    print("=" * 60)
    print(f"    网络测试: 192.168.1.103")
    print("=" * 60)
    
    # 检查到192.168.1.103的网络连接
    print("\n🔍 连接性测试:")
    hosts = [
        {'host': '192.168.1.103', 'port': 22, 'name': 'SSH端口', 'type': 'local'},
        {'host': '192.168.1.103', 'port': 80, 'name': 'HTTP端口', 'type': 'local'},
        {'host': '192.168.1.103', 'port': 443, 'name': 'HTTPS端口', 'type': 'local'},
    ]
    result = checker.check_connectivity(hosts)
    
    for r in result:
        status = "✅" if r['connected'] else "❌"
        latency = r.get('latency_ms')
        latency_str = f" ({latency}ms)" if latency else ""
        print(f"   {status} {r['name']}: {r['host']}:{r['port']}{latency_str}")
    
    # Ping测试到192.168.1.103
    print("\n📊 Ping稳定性测试:")
    ping_result = checker.check_ping_stability('192.168.1.103', count=5)
    print(f"   目标: {ping_result['target']}")
    print(f"   发送: {ping_result['sent']} | 接收: {ping_result['received']} | 丢失: {ping_result['lost']}")
    print(f"   丢包率: {ping_result['loss_rate']:.1f}%")
    if ping_result.get('avg_latency'):
        print(f"   延迟: {ping_result['min_latency']}ms / {ping_result['avg_latency']}ms / {ping_result['max_latency']}ms")
    
    # 检查DNS解析
    print("\n🔤 DNS解析测试:")
    dns_result = checker.check_dns_resolution(['www.baidu.com', '192.168.1.103'])
    for entry in dns_result:
        status = "✅" if entry['resolved'] else "❌"
        ip = entry.get('ip', '解析失败')
        latency = entry.get('latency_ms')
        latency_str = f" ({latency}ms)" if latency else ""
        print(f"   {status} {entry['domain']} -> {ip}{latency_str}")
    
    print("\n" + "=" * 60)
    
    # 综合评估
    all_connected = all(r['connected'] for r in result)
    ping_ok = ping_result['loss_rate'] < 20
    
    if all_connected and ping_ok:
        print("✅ 网络连接正常")
    else:
        issues = []
        if not all_connected:
            issues.append("部分端口连接失败")
        if not ping_ok:
            issues.append("Ping丢包率过高")
        print("❌ 网络存在问题: " + ", ".join(issues))
    
    print("=" * 60)

if __name__ == "__main__":
    main()
