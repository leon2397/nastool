#!/usr/bin/env python3
"""
网络质量检查器 - 评估网络连接质量
继承自Check基类，支持准确性保障
"""

import subprocess
import time
import os
import sys
from typing import Dict, List

from nastool_core.checks.base import Check, CheckResult, CheckCategory, CheckSeverity


class NetworkQualityChecker(Check):
    """网络质量检查器 - 继承自Check基类"""
    
    check_id = "network_quality_check"
    category = CheckCategory.NETWORK
    title = "Network Quality Check"
    description = "评估网络带宽、稳定性、TCP连接和性能指标"
    
    def __init__(self):
        super().__init__()  # 调用父类初始化，获取准确性保障能力
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
    
    def check_network_stability(self, duration=10):
        """检查网络稳定性（缩短测试时间）"""
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
        
        for i in range(min(duration, 10)):  # 限制最多10次测试
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
                
                time.sleep(0.5)
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
        
        if results['total_packets'] > 0:
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
        if avg_latency:
            if avg_latency > 500:
                score -= 20
            elif avg_latency > 200:
                score -= 10
            elif avg_latency > 100:
                score -= 5
        
        return max(0, score)
    
    def run(self) -> CheckResult:
        """运行检测 - 实现Check基类的run方法"""
        # 收集多源数据
        data_sources = []
        
        # 数据源1: 带宽测试
        bandwidth = self.check_bandwidth()
        download_speed = bandwidth.get('download_speed_mbps', 0)
        data_sources.append(self._create_data_source_result(
            download_speed, 'bandwidth_test', confidence=0.85
        ))
        
        # 数据源2: 网络稳定性
        stability = self.check_network_stability()
        loss_rate = stability.get('loss_rate', 100)
        data_sources.append(self._create_data_source_result(
            loss_rate, 'stability_test', confidence=0.9
        ))
        
        # 数据源3: TCP连接
        tcp = self.check_tcp_connections()
        established_count = tcp.get('established', 0)
        data_sources.append(self._create_data_source_result(
            established_count, 'tcp_connections', confidence=0.88
        ))
        
        # 数据源4: 网络性能
        performance = self.check_network_performance()
        dropped_packets = performance.get('softnet_dropped', 0)
        data_sources.append(self._create_data_source_result(
            dropped_packets, 'performance_metrics', confidence=0.82
        ))
        
        # 计算综合评分
        score = self._calculate_score()
        
        # 构建检测结果
        if score >= 80:
            result = CheckResult(
                check_id=self.check_id,
                category=self.category,
                title=self.title,
                passed=True,
                current=f"Score: {score}/100",
                expected="Network quality >= 80",
                message=f"✅ 网络质量优秀，综合评分: {score}/100",
                severity=CheckSeverity.PASSED,
                details={
                    'bandwidth': bandwidth,
                    'stability': stability,
                    'tcp_connections': tcp,
                    'performance': performance,
                    'score': score
                }
            )
        elif score >= 60:
            result = CheckResult(
                check_id=self.check_id,
                category=self.category,
                title=self.title,
                passed=True,
                current=f"Score: {score}/100",
                expected="Network quality >= 80",
                message=f"⚠️ 网络质量一般，综合评分: {score}/100",
                severity=CheckSeverity.WARNING,
                details={
                    'bandwidth': bandwidth,
                    'stability': stability,
                    'tcp_connections': tcp,
                    'performance': performance,
                    'score': score
                }
            )
        else:
            result = CheckResult(
                check_id=self.check_id,
                category=self.category,
                title=self.title,
                passed=False,
                current=f"Score: {score}/100",
                expected="Network quality >= 80",
                message=f"❌ 网络质量较差，综合评分: {score}/100",
                severity=CheckSeverity.WARNING,
                details={
                    'bandwidth': bandwidth,
                    'stability': stability,
                    'tcp_connections': tcp,
                    'performance': performance,
                    'score': score
                }
            )
        
        # 使用准确性保障方法增强结果
        return self._enhance_result_with_accuracy(result, data_sources)
