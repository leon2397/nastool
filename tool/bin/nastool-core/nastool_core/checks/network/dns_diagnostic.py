#!/usr/bin/env python3
"""
DNS诊断模块 - 检测DNS解析问题
"""

import socket
import subprocess
import time
import os
from typing import Dict, List

class DNSDiagnostic:
    """DNS诊断工具"""
    
    def __init__(self):
        self.results = {}
    
    def check_dns_configuration(self):
        """检查DNS配置"""
        config = {
            'resolv_conf': None,
            'nameservers': [],
            'search_domains': [],
            'options': []
        }
        
        # 读取/etc/resolv.conf
        try:
            with open('/etc/resolv.conf', 'r') as f:
                content = f.read()
                config['resolv_conf'] = content
                
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('nameserver'):
                        parts = line.split()
                        if len(parts) >= 2:
                            config['nameservers'].append(parts[1])
                    elif line.startswith('search'):
                        parts = line.split()
                        if len(parts) >= 2:
                            config['search_domains'].extend(parts[1:])
                    elif line.startswith('options'):
                        parts = line.split()
                        if len(parts) >= 2:
                            config['options'].extend(parts[1:])
        except Exception as e:
            config['error'] = str(e)
        
        self.results['configuration'] = config
        return config
    
    def check_dns_servers(self, servers=None):
        """检查DNS服务器可用性"""
        if servers is None:
            config = self.check_dns_configuration()
            servers = config.get('nameservers', [])
        
        # 添加一些公共DNS作为对比
        public_servers = ['8.8.8.8', '8.8.4.4', '223.5.5.5', '114.114.114.114']
        all_servers = list(set(servers + public_servers))
        
        results = []
        for server in all_servers:
            result = self._test_dns_server(server)
            results.append(result)
        
        self.results['servers'] = results
        return results
    
    def _test_dns_server(self, server):
        """测试单个DNS服务器"""
        result = {
            'server': server,
            'reachable': False,
            'latency_ms': None,
            'resolution_tests': []
        }
        
        # 测试服务器是否可达
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            start_time = time.time()
            sock.sendto(b'', (server, 53))
            result['reachable'] = True
            latency = (time.time() - start_time) * 1000
            result['latency_ms'] = round(latency, 2)
            sock.close()
        except Exception as e:
            result['error'] = str(e)
            return result
        
        # 测试解析
        test_domains = ['www.baidu.com', 'www.google.com', 'github.com', 'www.microsoft.com']
        for domain in test_domains:
            try:
                start_time = time.time()
                ip = socket.gethostbyname_ex(domain)[2][0]
                latency = (time.time() - start_time) * 1000
                result['resolution_tests'].append({
                    'domain': domain,
                    'resolved': True,
                    'ip': ip,
                    'latency_ms': round(latency, 2)
                })
            except Exception as e:
                result['resolution_tests'].append({
                    'domain': domain,
                    'resolved': False,
                    'ip': None,
                    'error': str(e)
                })
        
        return result
    
    def check_dns_cache(self):
        """检查DNS缓存状态"""
        cache_info = {}
        
        # 检查systemd-resolved缓存
        try:
            result = subprocess.run(
                ['systemd-resolve', '--statistics'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                cache_info['systemd_resolved'] = result.stdout
        except:
            pass
        
        # 检查dnsmasq缓存
        try:
            result = subprocess.run(
                ['pgrep', 'dnsmasq'],
                capture_output=True, text=True, timeout=2
            )
            cache_info['dnsmasq_running'] = result.returncode == 0
        except:
            pass
        
        self.results['cache'] = cache_info
        return cache_info
    
    def check_dns_latency(self, iterations=5):
        """检查DNS解析延迟"""
        results = []
        test_domains = ['www.baidu.com', 'www.google.com', 'github.com']
        
        for domain in test_domains:
            latencies = []
            for _ in range(iterations):
                try:
                    start_time = time.time()
                    socket.gethostbyname(domain)
                    latency = (time.time() - start_time) * 1000
                    latencies.append(latency)
                    time.sleep(0.1)
                except:
                    pass
            
            if latencies:
                results.append({
                    'domain': domain,
                    'min_latency': round(min(latencies), 2),
                    'max_latency': round(max(latencies), 2),
                    'avg_latency': round(sum(latencies) / len(latencies), 2),
                    'iterations': len(latencies)
                })
        
        self.results['latency'] = results
        return results
    
    def run_full_diagnosis(self):
        """运行完整的DNS诊断"""
        print("🔍 开始DNS诊断...")
        
        print("  📋 检查DNS配置...")
        self.check_dns_configuration()
        
        print("  🚀 检查DNS服务器...")
        self.check_dns_servers()
        
        print("  📊 检查DNS解析延迟...")
        self.check_dns_latency()
        
        print("  💾 检查DNS缓存...")
        self.check_dns_cache()
        
        print("✅ DNS诊断完成!")
        return self.results
    
    def generate_report(self):
        """生成DNS诊断报告"""
        report = []
        report.append("="*60)
        report.append("    DNS诊断报告")
        report.append("="*60)
        
        # DNS配置
        config = self.results.get('configuration', {})
        report.append(f"\n📋 DNS配置")
        report.append(f"   配置服务器: {', '.join(config.get('nameservers', ['无']))}")
        if config.get('search_domains'):
            report.append(f"   搜索域: {', '.join(config['search_domains'])}")
        if config.get('options'):
            report.append(f"   选项: {', '.join(config['options'])}")
        
        # DNS服务器测试
        servers = self.results.get('servers', [])
        report.append(f"\n🚀 DNS服务器测试")
        for server in servers:
            status = "✅" if server['reachable'] else "❌"
            latency = server.get('latency_ms')
            latency_str = f" ({latency}ms)" if latency else ""
            report.append(f"   {status} {server['server']}{latency_str}")
            
            # 解析测试结果
            if server.get('resolution_tests'):
                resolved_count = sum(1 for t in server['resolution_tests'] if t['resolved'])
                total = len(server['resolution_tests'])
                report.append(f"      解析成功率: {resolved_count}/{total}")
        
        # DNS延迟
        latency = self.results.get('latency', [])
        report.append(f"\n⏱️ DNS解析延迟")
        for item in latency:
            report.append(f"   {item['domain']}: {item['avg_latency']}ms (范围: {item['min_latency']}-{item['max_latency']}ms)")
        
        # DNS缓存
        cache = self.results.get('cache', {})
        report.append(f"\n💾 DNS缓存状态")
        report.append(f"   systemd-resolved: {'运行中' if 'systemd_resolved' in cache else '未运行'}")
        report.append(f"   dnsmasq: {'运行中' if cache.get('dnsmasq_running') else '未运行'}")
        
        report.append("\n" + "="*60)
        
        # 综合评估
        issues = []
        all_ok = True
        
        # 检查是否有可用的DNS服务器
        servers_ok = any(s.get('reachable') for s in servers)
        if not servers_ok:
            issues.append("没有可用的DNS服务器")
            all_ok = False
        
        # 检查解析成功率
        for server in servers:
            if server.get('reachable'):
                resolved_count = sum(1 for t in server['resolution_tests'] if t['resolved'])
                if resolved_count == 0:
                    issues.append(f"DNS服务器 {server['server']} 解析失败")
                    all_ok = False
        
        # 检查延迟
        for item in latency:
            if item['avg_latency'] > 500:
                issues.append(f"{item['domain']} 解析延迟过高 ({item['avg_latency']}ms)")
                all_ok = False
        
        if all_ok:
            report.append("✅ DNS状态正常")
        else:
            report.append("❌ DNS存在问题:")
            for issue in issues:
                report.append(f"   - {issue}")
        
        report.append("="*60)
        
        return '\n'.join(report)

def main():
    """命令行入口"""
    diagnostic = DNSDiagnostic()
    diagnostic.run_full_diagnosis()
    print(diagnostic.generate_report())

if __name__ == "__main__":
    main()
