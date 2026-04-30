#!/usr/bin/env python3
"""
网络质量检查器 - 评估网络连接质量
"""

import subprocess
import time
import os
import sys
from typing import Dict, List

class NetworkQualityChecker:
    """网络质量检查器"""
    
    def __init__(self):
        self.results = {}
    
    def check_bandwidth(self):
        """检查网络带宽"""
        results = {
            'upload_speed_mbps': None,
            'download_speed_mbps': None,
            'latency_ms': None,
            'jitter_ms': None,
            'packet_loss': None
        }
        
        # 尝试使用speedtest-cli
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'speedtest', '--simple'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Download' in line:
                        results['download_speed_mbps'] = float(line.split()[1])
                    elif 'Upload' in line:
                        results['upload_speed_mbps'] = float(line.split()[1])
                    elif 'Ping' in line:
                        results['latency_ms'] = float(line.split()[1])
        except:
            pass
        
        # 如果speedtest不可用，使用简单的curl测试
        if results['download_speed_mbps'] is None:
            try:
                # 使用curl下载一个小文件来估计速度
                start_time = time.time()
                result = subprocess.run(
                    ['curl', '-s', '-o', '/dev/null', '-w', '%{speed_download}', 
                     'http://speedtest.ftp.otenet.gr/files/test100k.db'],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    download_bytes_per_sec = float(result.stdout)
                    results['download_speed_mbps'] = (download_bytes_per_sec * 8) / (1024 * 1024)
            except:
                pass
        
        self.results['bandwidth'] = results
        return results
    
    def check_network_stability(self, duration=30):
        """检查网络稳定性"""
        results = {
            'duration': duration,
            'total_packets': 0,
            'lost_packets': 0,
            'loss_rate': 0.0,
            'min_latency': None,
            'max_latency': None,
            'avg_latency': None,
            'jitter': None,
            'disconnections': 0
        }
        
        latencies = []
        disconnections = 0
        
        for i in range(duration):
            try:
                # 简单的ping测试
                param = '-n' if sys.platform == 'win32' else '-c'
                result = subprocess.run(
                    ['ping', param, '1', '-W', '1', '8.8.8.8'],
                    capture_output=True, text=True, timeout=2
                )
                
                results['total_packets'] += 1
                
                if result.returncode != 0:
                    results['lost_packets'] += 1
                    disconnections += 1
                else:
                    # 解析延迟
                    output = result.stdout
                    if 'time=' in output.lower():
                        try:
                            latency_part = output.lower().split('time=')[1]
                            latency = float(latency_part.split(' ')[0])
                            latencies.append(latency)
                        except:
                            pass
                
                time.sleep(1)
            except Exception as e:
                results['lost_packets'] += 1
                disconnections += 1
        
        if latencies:
            results['min_latency'] = min(latencies)
            results['max_latency'] = max(latencies)
            results['avg_latency'] = sum(latencies) / len(latencies)
            # 计算抖动
            if len(latencies) > 1:
                jitter_sum = 0
                for i in range(1, len(latencies)):
                    jitter_sum += abs(latencies[i] - latencies[i-1])
                results['jitter'] = jitter_sum / (len(latencies) - 1)
        
        results['loss_rate'] = (results['lost_packets'] / results['total_packets']) * 100
        results['disconnections'] = disconnections
        
        self.results['stability'] = results
        return results
    
    def check_tcp_connections(self):
        """检查TCP连接状态"""
        results = {
            'total_connections': 0,
            'established': 0,
            'syn_sent': 0,
            'syn_recv': 0,
            'fin_wait': 0,
            'time_wait': 0,
            'closed': 0
        }
        
        try:
            result = subprocess.run(
                ['ss', '-tn'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('ESTAB'):
                        results['established'] += 1
                    elif line.startswith('SYN-SENT'):
                        results['syn_sent'] += 1
                    elif line.startswith('SYN-RECV'):
                        results['syn_recv'] += 1
                    elif line.startswith('FIN-WAIT'):
                        results['fin_wait'] += 1
                    elif line.startswith('TIME-WAIT'):
                        results['time_wait'] += 1
                    elif line.startswith('CLOSED'):
                        results['closed'] += 1
            
            results['total_connections'] = sum(results.values())
        except:
            pass
        
        self.results['tcp_connections'] = results
        return results
    
    def check_network_performance(self):
        """检查网络性能指标"""
        results = {}
        
        # 检查网络缓冲区
        try:
            with open('/proc/sys/net/core/netdev_max_backlog', 'r') as f:
                results['netdev_max_backlog'] = int(f.read().strip())
            
            with open('/proc/sys/net/ipv4/tcp_max_syn_backlog', 'r') as f:
                results['tcp_max_syn_backlog'] = int(f.read().strip())
            
            with open('/proc/sys/net/ipv4/tcp_syncookies', 'r') as f:
                results['tcp_syncookies'] = int(f.read().strip())
        except:
            pass
        
        # 检查网络软中断
        try:
            with open('/proc/net/softnet_stat', 'r') as f:
                lines = f.readlines()
                if lines:
                    stats = lines[0].split()
                    results['softnet_packets'] = int(stats[0], 16)
                    results['softnet_dropped'] = int(stats[1], 16)
                    results['softnet_time_squeeze'] = int(stats[2], 16)
        except:
            pass
        
        self.results['performance'] = results
        return results
    
    def run_full_check(self):
        """运行完整的网络质量检查"""
        print("🔍 开始网络质量检查...")
        
        print("  📊 检查带宽...")
        self.check_bandwidth()
        
        print("  ⚖️ 检查网络稳定性...")
        self.check_network_stability()
        
        print("  🔗 检查TCP连接...")
        self.check_tcp_connections()
        
        print("  ⚡ 检查网络性能...")
        self.check_network_performance()
        
        print("✅ 网络质量检查完成!")
        return self.results
    
    def generate_report(self):
        """生成网络质量报告"""
        report = []
        report.append("="*60)
        report.append("    网络质量报告")
        report.append("="*60)
        
        # 带宽信息
        bandwidth = self.results.get('bandwidth', {})
        report.append(f"\n📊 带宽测试")
        if bandwidth.get('download_speed_mbps'):
            report.append(f"   下载速度: {bandwidth['download_speed_mbps']:.2f} Mbps")
        else:
            report.append(f"   下载速度: 无法测试")
        
        if bandwidth.get('upload_speed_mbps'):
            report.append(f"   上传速度: {bandwidth['upload_speed_mbps']:.2f} Mbps")
        else:
            report.append(f"   上传速度: 无法测试")
        
        # 稳定性测试
        stability = self.results.get('stability', {})
        report.append(f"\n⚖️ 网络稳定性 ({stability.get('duration', 0)}秒)")
        report.append(f"   发送包数: {stability.get('total_packets', 0)}")
        report.append(f"   丢失包数: {stability.get('lost_packets', 0)}")
        report.append(f"   丢包率: {stability.get('loss_rate', 0):.1f}%")
        
        if stability.get('avg_latency'):
            report.append(f"   延迟范围: {stability.get('min_latency'):.1f}ms - {stability.get('max_latency'):.1f}ms")
            report.append(f"   平均延迟: {stability.get('avg_latency'):.1f}ms")
        
        if stability.get('jitter'):
            report.append(f"   抖动: {stability.get('jitter'):.1f}ms")
        
        if stability.get('disconnections') > 0:
            report.append(f"   ⚠️ 断网次数: {stability.get('disconnections')}")
        
        # TCP连接
        tcp = self.results.get('tcp_connections', {})
        report.append(f"\n🔗 TCP连接状态")
        report.append(f"   总数: {tcp.get('total_connections', 0)}")
        report.append(f"   已建立: {tcp.get('established', 0)}")
        report.append(f"   SYN-SENT: {tcp.get('syn_sent', 0)}")
        report.append(f"   SYN-RECV: {tcp.get('syn_recv', 0)}")
        report.append(f"   FIN-WAIT: {tcp.get('fin_wait', 0)}")
        report.append(f"   TIME-WAIT: {tcp.get('time_wait', 0)}")
        
        # 性能指标
        perf = self.results.get('performance', {})
        report.append(f"\n⚡ 网络性能指标")
        if 'netdev_max_backlog' in perf:
            report.append(f"   网络设备队列长度: {perf['netdev_max_backlog']}")
        if 'tcp_max_syn_backlog' in perf:
            report.append(f"   TCP SYN队列长度: {perf['tcp_max_syn_backlog']}")
        if 'softnet_dropped' in perf:
            report.append(f"   软中断丢包: {perf['softnet_dropped']}")
        
        report.append("\n" + "="*60)
        
        # 综合评分
        score = self._calculate_score()
        report.append(f"综合评分: {score}/100")
        
        if score >= 80:
            report.append("✅ 网络质量优秀")
        elif score >= 60:
            report.append("⚠️ 网络质量一般")
        else:
            report.append("❌ 网络质量较差")
        
        report.append("="*60)
        
        return '\n'.join(report)
    
    def _calculate_score(self):
        """计算网络质量评分"""
        score = 100
        
        # 带宽评分
        bandwidth = self.results.get('bandwidth', {})
        download = bandwidth.get('download_speed_mbps', 0)
        if download < 1:
            score -= 30
        elif download < 10:
            score -= 15
        elif download < 100:
            score -= 5
        
        # 稳定性评分
        stability = self.results.get('stability', {})
        loss_rate = stability.get('loss_rate', 0)
        if loss_rate > 10:
            score -= 30
        elif loss_rate > 5:
            score -= 15
        elif loss_rate > 1:
            score -= 5
        
        disconnections = stability.get('disconnections', 0)
        score -= disconnections * 10
        
        # 延迟评分
        avg_latency = stability.get('avg_latency', 0)
        if avg_latency > 500:
            score -= 20
        elif avg_latency > 200:
            score -= 10
        elif avg_latency > 100:
            score -= 5
        
        return max(0, score)

def main():
    """命令行入口"""
    checker = NetworkQualityChecker()
    checker.run_full_check()
    print(checker.generate_report())

if __name__ == "__main__":
    main()
