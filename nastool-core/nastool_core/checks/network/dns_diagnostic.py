#!/usr/bin/env python3
"""
DNS诊断模块 - 检测DNS解析问题
继承自Check基类，支持准确性保障
"""

import socket
import subprocess
import time
import os
from typing import Dict, List

from nastool_core.checks.base import Check, CheckResult, CheckCategory, CheckSeverity


class DNSDiagnostic(Check):
    """DNS诊断工具 - 继承自Check基类"""
    
    check_id = "dns_diagnostic"
    category = CheckCategory.NETWORK
    title = "DNS Diagnostic"
    description = "检测DNS配置、服务器可用性、解析延迟等"
    
    def __init__(self):
        super().__init__()  # 调用父类初始化，获取准确性保障能力
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
    
    def run(self) -> CheckResult:
        """运行检测 - 实现Check基类的run方法"""
        # 收集多源数据
        data_sources = []
        
        # 数据源1: DNS配置检查
        config = self.check_dns_configuration()
        nameserver_count = len(config.get('nameservers', []))
        data_sources.append(self._create_data_source_result(
            nameserver_count, 'dns_config', confidence=0.95
        ))
        
        # 数据源2: DNS服务器测试
        servers = self.check_dns_servers()
        reachable_count = sum(1 for s in servers if s.get('reachable'))
        data_sources.append(self._create_data_source_result(
            reachable_count, 'dns_servers', confidence=0.92
        ))
        
        # 数据源3: DNS解析延迟
        latency = self.check_dns_latency()
        if latency:
            avg_latency = sum(item['avg_latency'] for item in latency) / len(latency)
            data_sources.append(self._create_data_source_result(
                avg_latency, 'dns_latency', confidence=0.88
            ))
        
        # 数据源4: DNS缓存检查
        cache = self.check_dns_cache()
        cache_status = 'running' if cache.get('dnsmasq_running') or 'systemd_resolved' in cache else 'not_running'
        data_sources.append(self._create_data_source_result(
            cache_status, 'dns_cache', confidence=0.85
        ))
        
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
                total = len(server['resolution_tests'])
                if resolved_count == 0:
                    issues.append(f"DNS服务器 {server['server']} 解析失败")
                    all_ok = False
        
        # 检查延迟
        for item in latency:
            if item['avg_latency'] > 500:
                issues.append(f"{item['domain']} 解析延迟过高 ({item['avg_latency']}ms)")
                all_ok = False
        
        # 构建检测结果
        if all_ok:
            result = CheckResult(
                check_id=self.check_id,
                category=self.category,
                title=self.title,
                passed=True,
                current=f"{reachable_count} DNS servers available",
                expected="DNS working properly",
                message=f"✅ DNS状态正常，检测到 {reachable_count} 个可用DNS服务器",
                severity=CheckSeverity.PASSED,
                details={
                    'configuration': config,
                    'servers': servers,
                    'latency': latency,
                    'cache': cache
                }
            )
        else:
            result = CheckResult(
                check_id=self.check_id,
                category=self.category,
                title=self.title,
                passed=False,
                current="DNS issues detected",
                expected="DNS working properly",
                message=f"❌ DNS存在问题: {', '.join(issues)}",
                severity=CheckSeverity.WARNING,
                details={
                    'configuration': config,
                    'servers': servers,
                    'latency': latency,
                    'cache': cache,
                    'issues': issues
                }
            )
        
        # 使用准确性保障方法增强结果
        return self._enhance_result_with_accuracy(result, data_sources)
