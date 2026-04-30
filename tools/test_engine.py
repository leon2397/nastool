#!/usr/bin/env python3
"""NASTool 测试引擎 - 统一测试接口"""

import os
import sys
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))

from device_manager import DeviceManager
from report_manager import ReportManager

class TestEngine:
    def __init__(self):
        self.dm = DeviceManager()
        self.rm = ReportManager()
        self.test_history = []
    
    def run_test(self, device_id, test_mode='quick'):
        """执行设备测试"""
        device = self.dm.get_device(device_id)
        if not device:
            return {'error': '设备不存在'}
        
        print(f'🚀 开始测试设备: {device["name"]} ({device["ip"]})')
        print(f'📋 测试模式: {test_mode}')
        
        start_time = time.time()
        
        # 根据设备类型选择测试方案
        device_type = device.get('type', 'generic')
        tests = self._get_tests_by_device_type(device_type, test_mode)
        
        # 执行测试
        results = []
        for test_name, test_func in tests.items():
            print(f'🔍 正在测试: {test_name}')
            try:
                result = test_func(device)
                results.append({
                    'name': test_name,
                    'status': result['status'],
                    'details': result.get('details', ''),
                    'duration': result.get('duration', 0)
                })
                status_icon = {'pass': '✅', 'fail': '❌', 'error': '⚠️'}.get(result['status'], '⚪')
                print(f'   {status_icon} {result.get("details", "完成")}')
            except Exception as e:
                results.append({
                    'name': test_name,
                    'status': 'error',
                    'details': str(e),
                    'duration': 0
                })
                print(f'   ⚠️ 错误: {e}')
        
        duration = time.time() - start_time
        
        # 生成报告
        report = {
            'device_id': device_id,
            'device_name': device['name'],
            'device_ip': device['ip'],
            'device_type': device_type,
            'test_mode': test_mode,
            'timestamp': datetime.now().isoformat(),
            'duration': round(duration, 2),
            'results': results,
            'summary': {
                'passed': sum(1 for r in results if r['status'] == 'pass'),
                'failed': sum(1 for r in results if r['status'] == 'fail'),
                'error': sum(1 for r in results if r['status'] == 'error'),
                'total': len(results)
            }
        }
        
        # 保存报告到数据库
        self.rm.save_report(report)
        
        # 更新设备测试时间
        self.dm.update_device(device_id, last_test=datetime.now().isoformat())
        
        print(f'\n⏱️ 测试完成，耗时: {duration:.2f}秒')
        
        return report
    
    def _get_tests_by_device_type(self, device_type, test_mode):
        """根据设备类型获取测试项"""
        base_tests = {
            '网络连接性': self.test_network_connectivity,
            '系统基础信息': self.test_system_info,
            '依赖检查': self.test_dependencies
        }
        
        if test_mode == 'quick':
            return base_tests
        
        # 根据设备类型添加专项测试
        additional_tests = {}
        
        if device_type == 'ascend' or test_mode == 'hardware':
            additional_tests.update({
                'CPU信息': self.test_cpu,
                '内存检查': self.test_memory,
                '存储检查': self.test_storage,
                '昇腾芯片检测': self.test_ascend_hardware
            })
        
        if device_type == 'jetson':
            additional_tests.update({
                'CPU信息': self.test_cpu,
                '内存检查': self.test_memory,
                'GPU检测': self.test_gpu
            })
        
        if test_mode == 'network' or test_mode == 'full':
            additional_tests.update({
                '网络接口': self.test_network_interfaces,
                '网络质量': self.test_network_quality,
                'DNS诊断': self.test_dns,
                '路由检查': self.test_routing
            })
        
        if test_mode == 'full':
            # 添加所有测试项
            additional_tests.update({
                'CPU信息': self.test_cpu,
                '内存检查': self.test_memory,
                '存储检查': self.test_storage,
                '温度检测': self.test_temperature,
                '运行时间': self.test_uptime
            })
        
        base_tests.update(additional_tests)
        return base_tests
    
    def run_batch_test(self, device_ids, test_mode='quick', parallel=True):
        """批量测试多个设备"""
        results = []
        
        if parallel and len(device_ids) > 1:
            print(f'🚀 并行测试 {len(device_ids)} 个设备...')
            with ThreadPoolExecutor(max_workers=min(len(device_ids), 5)) as executor:
                futures = {executor.submit(self.run_test, device_id, test_mode): device_id for device_id in device_ids}
                
                for future in as_completed(futures):
                    device_id = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        results.append({'device_id': device_id, 'error': str(e)})
        else:
            for device_id in device_ids:
                result = self.run_test(device_id, test_mode)
                results.append(result)
        
        return results
    
    # 测试方法
    def test_network_connectivity(self, device):
        """测试网络连接性"""
        try:
            from nastool_core.checks.network.network_status_checker import NetworkStatusChecker
            checker = NetworkStatusChecker()
            result = checker.check_connectivity()
            connected = sum(1 for c in result if c.get('connected'))
            return {
                'status': 'pass' if connected > 0 else 'fail',
                'details': f'{connected}个连接正常'
            }
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_system_info(self, device):
        """测试系统信息"""
        try:
            import platform
            info = {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine()
            }
            return {'status': 'pass', 'details': str(info)}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_dependencies(self, device):
        """测试依赖"""
        try:
            from nastool_common.utils.env_checker import EnvironmentChecker
            checker = EnvironmentChecker()
            result = checker.check_python_version()
            return {'status': 'pass' if result else 'fail', 'details': 'Python版本检查'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_network_quality(self, device):
        """测试网络质量"""
        try:
            from nastool_core.checks.network.network_quality_checker import NetworkQualityChecker
            checker = NetworkQualityChecker()
            result = checker.check_bandwidth()
            speed = result.get('download_speed_mbps', 'N/A')
            return {'status': 'pass', 'details': f"下载: {speed} Mbps"}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_dns(self, device):
        """测试DNS"""
        try:
            from nastool_core.checks.network.dns_diagnostic import DNSDiagnostic
            dns = DNSDiagnostic()
            result = dns.check_dns_configuration()
            return {'status': 'pass', 'details': f'配置检查完成，{len(result)}项'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_hardware(self, device):
        """测试硬件"""
        try:
            from nastool_core.checks.ai.ascend_checker import AscendChecker
            checker = AscendChecker()
            result = checker.detect_ascend_hardware()
            return {'status': 'pass' if result else 'fail', 'details': '昇腾芯片检测'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_storage(self, device):
        """测试存储"""
        try:
            import shutil
            disk = shutil.disk_usage('/')
            free_percent = (disk.free / disk.total) * 100
            return {'status': 'pass', 'details': f'可用空间: {free_percent:.1f}%'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_network_interfaces(self, device):
        """测试网络接口"""
        try:
            from nastool_core.checks.network.network_status_checker import NetworkStatusChecker
            checker = NetworkStatusChecker()
            interfaces = checker.check_network_interfaces()
            return {'status': 'pass', 'details': f'发现{len(interfaces)}个网络接口'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_routing(self, device):
        """测试路由"""
        try:
            import subprocess
            result = subprocess.run(['route', 'print'], capture_output=True, text=True, timeout=5)
            return {'status': 'pass', 'details': '路由表检查完成'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_cpu(self, device):
        """测试CPU"""
        try:
            import multiprocessing
            return {'status': 'pass', 'details': f'CPU核心数: {multiprocessing.cpu_count()}'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_memory(self, device):
        """测试内存"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            available_percent = (mem.available / mem.total) * 100
            return {'status': 'pass', 'details': f'可用内存: {available_percent:.1f}%'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_ascend_hardware(self, device):
        """测试昇腾硬件"""
        try:
            from nastool_core.checks.ai.ascend_checker import AscendChecker
            checker = AscendChecker()
            hardware = checker.detect_ascend_hardware()
            return {'status': 'pass' if hardware else 'fail', 'details': '昇腾芯片检测'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}
    
    def test_gpu(self, device):
        """测试GPU"""
        try:
            from nastool_core.checks.ai.gpu_detected import GPUChecker
            checker = GPUChecker()
            result = checker.detect_gpu()
            return {'status': 'pass' if result else 'fail', 'details': 'GPU检测'}
        except Exception as e:
            return {'status': 'error', 'details': str(e)}

    def test_temperature(self, device):
        """测试设备温度"""
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                # 尝试获取CPU温度（支持多种平台）
                cpu_temp = temps.get("coretemp") or temps.get("cpu_thermal") or temps.get("thermal_zone0")
                if cpu_temp:
                    temp = cpu_temp[0].current
                    status = "pass" if temp < 80 else ("warning" if temp < 90 else "fail")
                    return {"status": status, "details": f"CPU温度: {temp:.1f}°C"}
            return {"status": "info", "details": "无法获取温度信息"}
        except Exception as e:
            return {"status": "error", "details": str(e)}

    def test_uptime(self, device):
        """测试系统运行时间"""
        try:
            import psutil
            import datetime
            uptime = psutil.boot_time()
            uptime_delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(uptime)
            days = uptime_delta.days
            hours = uptime_delta.seconds // 3600
            minutes = (uptime_delta.seconds % 3600) // 60
            return {"status": "pass", "details": f"运行时间: {days}天 {hours}小时 {minutes}分钟"}
        except Exception as e:
            return {"status": "error", "details": str(e)}


    def test_temperature(self, device):
        """测试设备温度"""
        try:
            import psutil
            import platform
            
            # Windows系统特殊处理
            if platform.system() == "Windows":
                try:
                    # 使用WMIC获取温度（Windows专用）
                    import subprocess
                    result = subprocess.run(
                        ["wmic", "cpu", "get", "Temperature"],
                        capture_output=True, text=True, timeout=10
                    )
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        temp_str = lines[1].strip()
                        if temp_str.isdigit():
                            temp = int(temp_str)
                            status = "pass" if temp < 80 else ("warning" if temp < 90 else "fail")
                            return {"status": status, "details": f"CPU温度: {temp}°C"}
                except:
                    pass
                return {"status": "info", "details": "Windows系统温度检测不可用"}
            
            # Linux系统使用psutil
            temps = psutil.sensors_temperatures()
            if temps:
                # 尝试获取CPU温度（支持多种平台）
                cpu_temp = temps.get("coretemp") or temps.get("cpu_thermal") or temps.get("thermal_zone0")
                if cpu_temp:
                    temp = cpu_temp[0].current
                    status = "pass" if temp < 80 else ("warning" if temp < 90 else "fail")
                    return {"status": status, "details": f"CPU温度: {temp:.1f}°C"}
            return {"status": "info", "details": "无法获取温度信息"}
        except Exception as e:
            return {"status": "error", "details": str(e)}

    def test_uptime(self, device):
        """测试系统运行时间"""
        try:
            import psutil
            import datetime
            uptime = psutil.boot_time()
            uptime_delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(uptime)
            days = uptime_delta.days
            hours = uptime_delta.seconds // 3600
            minutes = (uptime_delta.seconds % 3600) // 60
            return {"status": "pass", "details": f"运行时间: {days}天 {hours}小时 {minutes}分钟"}
        except Exception as e:
            return {"status": "error", "details": str(e)}


def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NASTool 测试引擎')
    subparsers = parser.add_subparsers(dest='command')
    
    # 单个设备测试
    test_parser = subparsers.add_parser('test', help='测试设备')
    test_parser.add_argument('device_id', help='设备ID')
    test_parser.add_argument('-m', '--mode', default='quick', 
                            choices=['quick', 'full', 'network', 'hardware'],
                            help='测试模式')
    
    # 批量测试
    batch_parser = subparsers.add_parser('batch', help='批量测试')
    batch_parser.add_argument('device_ids', nargs='+', help='设备ID列表')
    batch_parser.add_argument('-m', '--mode', default='quick', 
                            choices=['quick', 'full', 'network', 'hardware'],
                            help='测试模式')
    batch_parser.add_argument('--sequential', action='store_true', help='顺序执行')
    
    args = parser.parse_args()
    
    engine = TestEngine()
    
    if args.command == 'test':
        report = engine.run_test(args.device_id, args.mode)
        
        # 打印报告摘要
        print('\n' + '='*60)
        print('📊 测试报告')
        print('='*60)
        print(f"设备: {report['device_name']} ({report['device_ip']})")
        print(f"模式: {report['test_mode']}")
        print(f"耗时: {report['duration']}秒")
        print('-'*60)
        
        for result in report['results']:
            status_color = {'pass': '✅', 'fail': '❌', 'error': '⚠️'}
            print(f"{status_color.get(result['status'], '⚪')} {result['name']}: {result['details']}")
        
        print('-'*60)
        summary = report['summary']
        print(f"总计: {summary['total']} | 通过: {summary['passed']} | 失败: {summary['failed']} | 错误: {summary['error']}")
        
        if summary['passed'] == summary['total']:
            print('🎉 所有测试通过!')
        else:
            print('⚠️ 部分测试失败')
        
        print('='*60)
    
    elif args.command == 'batch':
        results = engine.run_batch_test(args.device_ids, args.mode, not args.sequential)
        
        print('\n' + '='*60)
        print('📊 批量测试结果汇总')
        print('='*60)
        
        total_passed = 0
        total_failed = 0
        total_error = 0
        
        for result in results:
            if 'error' in result:
                print(f"❌ {result['device_id']}: {result['error']}")
                total_error += 1
            else:
                summary = result['summary']
                status = '✅' if summary['passed'] == summary['total'] else '⚠️'
                print(f"{status} {result['device_name']}: {summary['passed']}/{summary['total']} 通过")
                total_passed += summary['passed']
                total_failed += summary['failed']
        
        print('-'*60)
        print(f"设备总数: {len(results)} | 总通过: {total_passed} | 总失败: {total_failed} | 总错误: {total_error}")
        print('='*60)

if __name__ == '__main__':
    main()
