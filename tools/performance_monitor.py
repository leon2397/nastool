#!/usr/bin/env python3
"""性能监控与分析模块"""

import os
import sys
import time
import json
import psutil
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, device_id=None):
        self.device_id = device_id
        self.running = False
        self.data = []
        self.lock = threading.Lock()
        self.interval = 1  # 采样间隔（秒）
    
    def start(self, duration=60):
        """开始监控"""
        self.running = True
        self.data = []
        
        def monitor():
            start_time = time.time()
            while self.running and (time.time() - start_time) < duration:
                snapshot = self._take_snapshot()
                with self.lock:
                    self.data.append(snapshot)
                time.sleep(self.interval)
        
        thread = threading.Thread(target=monitor)
        thread.start()
        return thread
    
    def stop(self):
        """停止监控"""
        self.running = False
    
    def _take_snapshot(self):
        """采集性能快照"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / (1024 ** 3),
            'memory_total_gb': memory.total / (1024 ** 3),
            'disk_percent': disk.percent,
            'disk_used_gb': disk.used / (1024 ** 3),
            'disk_total_gb': disk.total / (1024 ** 3),
            'net_sent_mb': net_io.bytes_sent / (1024 ** 2),
            'net_recv_mb': net_io.bytes_recv / (1024 ** 2)
        }
    
    def get_report(self):
        """生成性能报告"""
        if not self.data:
            return {'error': 'No data collected'}
        
        data = self.data
        metrics = {
            'device': self.device_id or 'localhost',
            'start_time': data[0]['timestamp'],
            'end_time': data[-1]['timestamp'],
            'samples': len(data),
            'duration': (len(data) - 1) * self.interval,
            'cpu': {
                'avg': sum(d['cpu_percent'] for d in data) / len(data),
                'max': max(d['cpu_percent'] for d in data),
                'min': min(d['cpu_percent'] for d in data),
                'peak': self._find_peak(data, 'cpu_percent')
            },
            'memory': {
                'avg': sum(d['memory_percent'] for d in data) / len(data),
                'max': max(d['memory_percent'] for d in data),
                'min': min(d['memory_percent'] for d in data),
                'peak_used_gb': max(d['memory_used_gb'] for d in data)
            },
            'disk': {
                'avg': sum(d['disk_percent'] for d in data) / len(data),
                'max': max(d['disk_percent'] for d in data),
                'min': min(d['disk_percent'] for d in data)
            },
            'network': {
                'total_sent_mb': data[-1]['net_sent_mb'] - data[0]['net_sent_mb'],
                'total_recv_mb': data[-1]['net_recv_mb'] - data[0]['net_recv_mb']
            }
        }
        
        return metrics
    
    def _find_peak(self, data, key):
        """查找峰值时间点"""
        max_val = max(d[key] for d in data)
        for d in data:
            if d[key] == max_val:
                return {'value': max_val, 'time': d['timestamp']}
        return None
    
    def save_report(self, filepath=None):
        """保存报告到文件"""
        report = self.get_report()
        if filepath is None:
            filepath = f"perf_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return filepath

class RemotePerformanceMonitor(PerformanceMonitor):
    """远程性能监控器"""
    
    def __init__(self, device_id):
        super().__init__(device_id)
        from device_manager import DeviceManager
        self.device_manager = DeviceManager()
        self.device = self.device_manager.get_device(device_id)
    
    def _take_snapshot(self):
        """通过SSH采集远程设备性能快照"""
        if not self.device:
            return super()._take_snapshot()
        
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=self.device['ip'],
                port=self.device.get('port', 22),
                username=self.device['username'],
                password=self.device.get('password'),
                timeout=10
            )
            
            # CPU使用率
            stdin, stdout, stderr = client.exec_command('top -bn1 | grep Cpu | awk \'{print $2}\'')
            cpu_percent = float(stdout.read().decode().strip().replace(',', '.'))
            
            # 内存信息
            stdin, stdout, stderr = client.exec_command('free -g | grep Mem')
            mem_line = stdout.read().decode().strip().split()
            mem_total = int(mem_line[1])
            mem_used = int(mem_line[2])
            mem_percent = (mem_used / mem_total) * 100
            
            # 磁盘信息
            stdin, stdout, stderr = client.exec_command('df -h / | grep /')
            disk_line = stdout.read().decode().strip().split()
            disk_percent = int(disk_line[-1].replace('%', ''))
            
            client.close()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': mem_percent,
                'memory_used_gb': mem_used,
                'memory_total_gb': mem_total,
                'disk_percent': disk_percent,
                'disk_used_gb': 0,
                'disk_total_gb': 0,
                'net_sent_mb': 0,
                'net_recv_mb': 0
            }
        except Exception as e:
            print(f"Remote monitoring error: {e}")
            return super()._take_snapshot()

def main():
    """命令行接口"""
    import argparse
    parser = argparse.ArgumentParser(description='性能监控工具')
    parser.add_argument('action', choices=['start', 'report'], help='操作')
    parser.add_argument('-d', '--duration', type=int, default=10, help='监控时长(秒)')
    parser.add_argument('-o', '--output', help='输出文件')
    parser.add_argument('-dev', '--device', help='远程设备ID')
    
    args = parser.parse_args()
    
    if args.device:
        monitor = RemotePerformanceMonitor(args.device)
    else:
        monitor = PerformanceMonitor()
    
    if args.action == 'start':
        print(f'🚀 开始性能监控，时长 {args.duration} 秒...')
        thread = monitor.start(args.duration)
        thread.join()
        
        report = monitor.get_report()
        print_report(report)
        
        if args.output:
            monitor.save_report(args.output)
            print(f'📊 报告已保存到 {args.output}')
    
    elif args.action == 'report':
        report = monitor.get_report()
        print_report(report)

def print_report(report):
    """打印报告"""
    print('='*60)
    print('📊 性能监控报告')
    print('='*60)
    print(f"设备: {report.get('device', 'localhost')}")
    print(f"时间范围: {report.get('start_time', '-')} ~ {report.get('end_time', '-')}")
    print(f"采样数: {report.get('samples', 0)} | 时长: {report.get('duration', 0)}秒")
    print()
    print('--- CPU ---')
    cpu = report.get('cpu', {})
    print(f"  平均: {cpu.get('avg', 0):.1f}% | 最大: {cpu.get('max', 0):.1f}% | 最小: {cpu.get('min', 0):.1f}%")
    print()
    print('--- 内存 ---')
    mem = report.get('memory', {})
    print(f"  平均: {mem.get('avg', 0):.1f}% | 最大: {mem.get('max', 0):.1f}% | 峰值: {mem.get('peak_used_gb', 0):.2f}GB")
    print()
    print('--- 网络 ---')
    net = report.get('network', {})
    print(f"  发送: {net.get('total_sent_mb', 0):.2f}MB | 接收: {net.get('total_recv_mb', 0):.2f}MB")
    print('='*60)

if __name__ == '__main__':
    main()
