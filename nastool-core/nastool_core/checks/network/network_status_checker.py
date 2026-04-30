#!/usr/bin/env python3
"""
网络状态检查器 - 检测网络连接稳定性和断网问题
"""

import os
import sys
import socket
import time
import subprocess
from typing import Dict, List, Tuple

class NetworkStatusChecker:
    """网络状态检查器"""
    
    def __init__(self):
        self.results = {}
    
    def check_network_interfaces(self):
        """检查所有网络接口状态"""
        interfaces = []
        
        # Linux系统
        if sys.platform.startswith('linux'):
            try:
                # 读取/proc/net/dev获取接口统计
                with open('/proc/net/dev', 'r') as f:
                    lines = f.readlines()
                
                for line in lines[2:]:  # 跳过前两行标题
                    parts = line.split()
                    if len(parts) >= 17:
                        iface = parts[0].strip(':')
                        rx_bytes = int(parts[1])
                        rx_packets = int(parts[2])
                        rx_errs = int(parts[3])
                        rx_drop = int(parts[4])
                        tx_bytes = int(parts[9])
                        tx_packets = int(parts[10])
                        tx_errs = int(parts[11])
                        tx_drop = int(parts[12])
                        
                        interfaces.append({
                            'name': iface,
                            'rx_bytes': rx_bytes,
                            'rx_packets': rx_packets,
                            'rx_errors': rx_errs,
                            'rx_drops': rx_drop,
                            'tx_bytes': tx_bytes,
                            'tx_packets': tx_packets,
                            'tx_errors': tx_errs,
                            'tx_drops': tx_drop
                        })
            except Exception as e:
                pass
        
        # 尝试使用ip命令获取更详细信息
        try:
            result = subprocess.run(
                ['ip', 'link', 'show'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith(' '):
                        continue
                    parts = line.split(':')
                    if len(parts) >= 2:
                        iface_idx = parts[0].strip()
                        iface_name = parts[1].strip()
                        # 查找对应接口并添加状态
                        for iface in interfaces:
                            if iface['name'] == iface_name:
                                if 'UP' in line:
                                    iface['status'] = 'up'
                                else:
                                    iface['status'] = 'down'
        except:
            pass
        
        self.results['interfaces'] = interfaces
        return interfaces
    
    def check_link_status(self):
        """检查网络链路状态"""
        links = []
        
        try:
            result = subprocess.run(
                ['ethtool', '--help'],
                capture_output=True, text=True, timeout=2
            )
            has_ethtool = result.returncode == 0
            
            if has_ethtool:
                interfaces = self.check_network_interfaces()
                for iface in interfaces:
                    try:
                        result = subprocess.run(
                            ['ethtool', iface['name']],
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            output = result.stdout
                            link_detected = 'Link detected: yes' in output
                            speed = 'unknown'
                            duplex = 'unknown'
                            
                            for line in output.split('\n'):
                                if 'Speed:' in line:
                                    speed = line.split(':')[1].strip()
                                if 'Duplex:' in line:
                                    duplex = line.split(':')[1].strip()
                            
                            links.append({
                                'interface': iface['name'],
                                'link_detected': link_detected,
                                'speed': speed,
                                'duplex': duplex
                            })
                    except:
                        pass
        except:
            pass
        
        self.results['links'] = links
        return links
    
    def check_connectivity(self, hosts=None, timeout=3):
        """检查网络连接性"""
        hosts = hosts or [
            {'host': '192.168.1.1', 'port': 80, 'name': '内网网关', 'type': 'local'},
            {'host': '8.8.8.8', 'port': 53, 'name': 'Google DNS', 'type': 'external'},
            {'host': '223.5.5.5', 'port': 53, 'name': '阿里DNS', 'type': 'external'},
            {'host': 'www.baidu.com', 'port': 80, 'name': '百度', 'type': 'external'},
            {'host': 'www.github.com', 'port': 443, 'name': 'GitHub', 'type': 'external'}
        ]
        
        results = []
        for item in hosts:
            result = self._test_connectivity(item['host'], item['port'], timeout)
            result.update({
                'name': item['name'],
                'type': item['type']
            })
            results.append(result)
        
        self.results['connectivity'] = results
        return results
    
    def _test_connectivity(self, host, port, timeout):
        """测试单个主机连接性"""
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            latency = (time.time() - start_time) * 1000
            sock.close()
            
            return {
                'host': host,
                'port': port,
                'connected': result == 0,
                'latency_ms': round(latency, 2),
                'error': None if result == 0 else f"连接失败 (code: {result})"
            }
        except Exception as e:
            return {
                'host': host,
                'port': port,
                'connected': False,
                'latency_ms': None,
                'error': str(e)
            }
    
    def check_ping_stability(self, target, count=10, timeout=1):
        """检查ping稳定性"""
        results = {
            'target': target,
            'sent': count,
            'received': 0,
            'lost': 0,
            'loss_rate': 0.0,
            'min_latency': None,
            'avg_latency': None,
            'max_latency': None,
            'latencies': []
        }
        
        try:
            param = '-n' if sys.platform == 'win32' else '-c'
            result = subprocess.run(
                ['ping', param, str(count), '-W', str(timeout), target],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0 or result.returncode == 1:  # 1表示有丢包但命令成功
                output = result.stdout
                
                # 解析Linux ping输出
                if 'received' in output:
                    # Linux格式
                    for line in output.split('\n'):
                        if 'packets transmitted' in line:
                            parts = line.split(',')
                            for part in parts:
                                if 'received' in part:
                                    results['received'] = int(part.strip().split()[0])
                                elif 'transmitted' in part:
                                    results['sent'] = int(part.strip().split()[0])
                        elif 'rtt' in line or 'round-trip' in line:
                            # 解析延迟信息
                            if '=' in line:
                                rtt_part = line.split('=')[1]
                                if '/' in rtt_part:
                                    rtt_values = rtt_part.split('/')
                                    if len(rtt_values) >= 3:
                                        results['min_latency'] = float(rtt_values[0].strip())
                                        results['avg_latency'] = float(rtt_values[1].strip())
                                        results['max_latency'] = float(rtt_values[2].split()[0])
                
                # 提取每个ping的延迟
                for line in output.split('\n'):
                    if 'time=' in line.lower():
                        try:
                            latency_part = line.lower().split('time=')[1]
                            latency = float(latency_part.split(' ')[0])
                            results['latencies'].append(latency)
                        except:
                            pass
                
                results['lost'] = results['sent'] - results['received']
                results['loss_rate'] = (results['lost'] / results['sent']) * 100
                
        except Exception as e:
            results['error'] = str(e)
        
        self.results['ping_stability'] = results
        return results
    
    def check_dns_resolution(self, domains=None):
        """检查DNS解析"""
        domains = domains or ['www.baidu.com', 'www.google.com', 'github.com']
        
        results = []
        for domain in domains:
            try:
                start_time = time.time()
                ip = socket.gethostbyname(domain)
                latency = (time.time() - start_time) * 1000
                
                results.append({
                    'domain': domain,
                    'resolved': True,
                    'ip': ip,
                    'latency_ms': round(latency, 2)
                })
            except socket.gaierror as e:
                results.append({
                    'domain': domain,
                    'resolved': False,
                    'ip': None,
                    'latency_ms': None,
                    'error': str(e)
                })
        
        self.results['dns'] = results
        return results
    
    def check_network_statistics(self):
        """检查网络统计信息"""
        stats = {}
        
        try:
            with open('/proc/net/sockstat', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        stats[parts[0].strip(':')] = parts[1]
        except:
            pass
        
        try:
            with open('/proc/net/softnet_stat', 'r') as f:
                lines = f.readlines()
                if lines:
                    stats['softnet_stat'] = lines[0].strip()
        except:
            pass
        
        self.results['statistics'] = stats
        return stats
    
    def run_full_diagnosis(self):
        """运行完整的网络诊断"""
        print("🔍 开始网络诊断...")
        
        print("  📡 检查网络接口...")
        self.check_network_interfaces()
        
        print("  🔗 检查链路状态...")
        self.check_link_status()
        
        print("  🌐 检查连接性...")
        self.check_connectivity()
        
        print("  📊 检查ping稳定性...")
        self.check_ping_stability('8.8.8.8', count=10)
        
        print("  �DNS 检查DNS解析...")
        self.check_dns_resolution()
        
        print("  📈 检查网络统计...")
        self.check_network_statistics()
        
        print("✅ 网络诊断完成!")
        return self.results
    
    def generate_report(self):
        """生成诊断报告"""
        report = []
        report.append("="*60)
        report.append("    网络诊断报告")
        report.append("="*60)
        
        # 网络接口
        interfaces = self.results.get('interfaces', [])
        report.append(f"\n📡 网络接口状态")
        for iface in interfaces:
            status = iface.get('status', 'unknown')
            status_icon = "✅" if status == 'up' else "❌"
            report.append(f"   {status_icon} {iface['name']} ({status})")
            report.append(f"      接收: {self._format_bytes(iface['rx_bytes'])} | 发送: {self._format_bytes(iface['tx_bytes'])}")
            if iface['rx_errors'] > 0 or iface['tx_errors'] > 0:
                report.append(f"      ⚠️ 错误: RX={iface['rx_errors']} TX={iface['tx_errors']}")
        
        # 链路状态
        links = self.results.get('links', [])
        if links:
            report.append(f"\n🔗 链路状态")
            for link in links:
                status = "✅" if link['link_detected'] else "❌"
                report.append(f"   {status} {link['interface']}: {link['speed']} / {link['duplex']}")
        
        # 连接性
        connectivity = self.results.get('connectivity', [])
        report.append(f"\n🌐 网络连接性测试")
        local_ok = True
        external_ok = True
        
        for conn in connectivity:
            status = "✅" if conn['connected'] else "❌"
            latency = conn.get('latency_ms')
            latency_str = f" ({latency}ms)" if latency else ""
            report.append(f"   {status} {conn['name']}{latency_str}")
            
            if conn['type'] == 'local' and not conn['connected']:
                local_ok = False
            if conn['type'] == 'external' and not conn['connected']:
                external_ok = False
        
        # Ping稳定性
        ping = self.results.get('ping_stability', {})
        report.append(f"\n📊 Ping稳定性测试")
        report.append(f"   目标: {ping.get('target', '未知')}")
        report.append(f"   发送: {ping.get('sent', 0)} | 接收: {ping.get('received', 0)} | 丢失: {ping.get('lost', 0)}")
        report.append(f"   丢包率: {ping.get('loss_rate', 0):.1f}%")
        
        if ping.get('avg_latency'):
            report.append(f"   延迟: {ping.get('min_latency')}ms / {ping.get('avg_latency')}ms / {ping.get('max_latency')}ms")
        
        if ping.get('loss_rate', 0) > 0:
            report.append(f"   ⚠️ 存在丢包，网络不稳定")
        
        # DNS解析
        dns = self.results.get('dns', [])
        report.append(f"\n🔤 DNS解析测试")
        for entry in dns:
            status = "✅" if entry['resolved'] else "❌"
            ip = entry.get('ip', '解析失败')
            latency = entry.get('latency_ms')
            latency_str = f" ({latency}ms)" if latency else ""
            report.append(f"   {status} {entry['domain']} -> {ip}{latency_str}")
        
        report.append("\n" + "="*60)
        
        # 综合评估
        all_ok = True
        issues = []
        
        if not local_ok:
            issues.append("内网连接失败")
            all_ok = False
        if not external_ok:
            issues.append("外网连接失败")
            all_ok = False
        if ping.get('loss_rate', 0) > 10:
            issues.append("网络丢包率过高")
            all_ok = False
        
        if all_ok:
            report.append("✅ 网络状态正常")
        else:
            report.append("❌ 网络存在问题: " + ", ".join(issues))
        
        report.append("="*60)
        
        return '\n'.join(report)
    
    def _format_bytes(self, bytes_count):
        """格式化字节数"""
        if bytes_count < 1024:
            return f"{bytes_count} B"
        elif bytes_count < 1024 * 1024:
            return f"{bytes_count / 1024:.2f} KB"
        elif bytes_count < 1024 * 1024 * 1024:
            return f"{bytes_count / (1024 * 1024):.2f} MB"
        else:
            return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"

def main():
    """命令行入口"""
    checker = NetworkStatusChecker()
    checker.run_full_diagnosis()
    print(checker.generate_report())

if __name__ == "__main__":
    main()
