#!/usr/bin/env python3
"""
快速诊断模块 - 支持多种诊断模式
"""

import sys
import time
import json
from typing import Dict, Any, Optional

class QuickDiagnose:
    """快速诊断工具"""
    
    MODES = {
        'quick': {
            'name': '快速模式',
            'description': '只运行核心检测项，快速获取系统状态',
            'timeout': 30,
            'include_checks': ['system', 'network_basic', 'dependencies', 'hardware_basic']
        },
        'full': {
            'name': '完整模式',
            'description': '运行所有检测项，包括性能基准测试',
            'timeout': 120,
            'include_checks': ['system', 'network_full', 'dependencies', 'hardware_full', 'performance']
        },
        'network': {
            'name': '网络专项',
            'description': '专注于网络诊断',
            'timeout': 60,
            'include_checks': ['network_full', 'dns']
        },
        'hardware': {
            'name': '硬件专项',
            'description': '专注于硬件诊断',
            'timeout': 60,
            'include_checks': ['hardware_full', 'system']
        },
        'mock': {
            'name': '模拟模式',
            'description': '使用模拟数据进行测试，无需真实设备',
            'timeout': 10,
            'include_checks': ['mock']
        }
    }
    
    def __init__(self, mode: str = 'quick'):
        self.mode = mode
        self.results = {}
        self.start_time = 0
        self.end_time = 0
    
    def get_mode_info(self) -> Dict[str, Any]:
        """获取当前模式信息"""
        return self.MODES.get(self.mode, self.MODES['quick'])
    
    def run(self) -> Dict[str, Any]:
        """运行诊断"""
        mode_info = self.get_mode_info()
        print(f"🚀 启动 {mode_info['name']}...")
        print(f"   描述: {mode_info['description']}")
        
        self.start_time = time.time()
        checks = mode_info['include_checks']
        
        # 执行各检测项
        for check in checks:
            print(f"\n🔍 正在检测: {self._get_check_name(check)}...")
            try:
                result = self._run_check(check)
                self.results[check] = result
                print(f"   ✅ 完成")
            except Exception as e:
                print(f"   ❌ 失败: {e}")
                self.results[check] = {'error': str(e)}
        
        self.end_time = time.time()
        
        # 生成综合报告
        self._generate_summary()
        
        print(f"\n✅ 诊断完成! 耗时: {self.end_time - self.start_time:.2f}秒")
        return self.results
    
    def _get_check_name(self, check: str) -> str:
        """获取检测项名称"""
        names = {
            'system': '系统信息',
            'network_basic': '基础网络',
            'network_full': '完整网络',
            'dependencies': '依赖检查',
            'hardware_basic': '基础硬件',
            'hardware_full': '完整硬件',
            'performance': '性能测试',
            'dns': 'DNS诊断',
            'mock': '模拟数据'
        }
        return names.get(check, check)
    
    def _run_check(self, check: str) -> Dict[str, Any]:
        """执行单个检测项"""
        if check == 'system':
            return self._check_system()
        elif check == 'network_basic':
            return self._check_network_basic()
        elif check == 'network_full':
            return self._check_network_full()
        elif check == 'dependencies':
            return self._check_dependencies()
        elif check == 'hardware_basic':
            return self._check_hardware_basic()
        elif check == 'hardware_full':
            return self._check_hardware_full()
        elif check == 'performance':
            return self._check_performance()
        elif check == 'dns':
            return self._check_dns()
        elif check == 'mock':
            return self._check_mock()
        return {}
    
    def _check_system(self) -> Dict[str, Any]:
        """检查系统信息"""
        import platform
        return {
            'os': platform.system(),
            'platform': platform.platform(),
            'architecture': platform.machine(),
            'hostname': platform.node(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'python_implementation': platform.python_implementation()
        }
    
    def _check_network_basic(self) -> Dict[str, Any]:
        """基础网络检查"""
        import socket
        
        results = []
        hosts = [
            {'host': '127.0.0.1', 'port': 80, 'name': '本地回环'},
            {'host': '8.8.8.8', 'port': 53, 'name': 'Google DNS'}
        ]
        
        for item in hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((item['host'], item['port']))
                sock.close()
                results.append({
                    'name': item['name'],
                    'host': item['host'],
                    'port': item['port'],
                    'connected': result == 0
                })
            except:
                results.append({
                    'name': item['name'],
                    'host': item['host'],
                    'port': item['port'],
                    'connected': False
                })
        
        return {'connectivity': results}
    
    def _check_network_full(self) -> Dict[str, Any]:
        """完整网络检查"""
        # 导入网络诊断模块
        try:
            from nastool_core.checks.network.network_status_checker import NetworkStatusChecker
            checker = NetworkStatusChecker()
            return checker.run_full_diagnosis()
        except ImportError:
            return {'error': '网络诊断模块未找到', 'basic': self._check_network_basic()}
    
    def _check_dependencies(self) -> Dict[str, Any]:
        """检查依赖"""
        required = ['paramiko', 'requests', 'pydantic', 'rich', 'psutil']
        installed = []
        missing = []
        
        for dep in required:
            if self._is_installed(dep):
                installed.append(dep)
            else:
                missing.append(dep)
        
        return {
            'required': len(required),
            'installed': len(installed),
            'missing': missing,
            'ok': len(missing) == 0
        }
    
    def _is_installed(self, dep_name: str) -> bool:
        """检查依赖是否安装"""
        module_map = {
            'paramiko': 'paramiko',
            'pyusb': 'usb',
            'requests': 'requests',
            'pydantic': 'pydantic',
            'rich': 'rich',
            'psutil': 'psutil'
        }
        
        module_name = module_map.get(dep_name, dep_name.replace('-', '_'))
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    def _check_hardware_basic(self) -> Dict[str, Any]:
        """基础硬件检查"""
        # 检查AI硬件
        import os
        
        hardware_info = {
            'has_nvidia': False,
            'has_ascend': False,
            'has_rockchip': False,
            'has_sophon': False
        }
        
        # 检查英伟达
        try:
            import subprocess
            result = subprocess.run(['nvidia-smi', '--query-gpu=count', '--format=csv,noheader'],
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                hardware_info['has_nvidia'] = True
        except:
            pass
        
        # 检查昇腾
        if os.path.exists('/usr/local/Ascend') or os.path.exists('/usr/lib64/libascendcl.so'):
            hardware_info['has_ascend'] = True
        
        return hardware_info
    
    def _check_hardware_full(self) -> Dict[str, Any]:
        """完整硬件检查"""
        # 导入昇腾检测模块
        try:
            from nastool_core.checks.ai.ascend_checker import AscendChecker
            checker = AscendChecker()
            return checker.run_full_check()
        except ImportError:
            return {'error': '硬件诊断模块未找到', 'basic': self._check_hardware_basic()}
    
    def _check_performance(self) -> Dict[str, Any]:
        """性能测试"""
        import time
        
        # 简单的CPU性能测试
        start = time.time()
        result = sum(i*i for i in range(1, 1000000))
        cpu_time = (time.time() - start) * 1000
        
        return {
            'cpu_test_ms': round(cpu_time, 2),
            'status': 'completed'
        }
    
    def _check_dns(self) -> Dict[str, Any]:
        """DNS诊断"""
        try:
            from nastool_core.checks.network.dns_diagnostic import DNSDiagnostic
            diagnostic = DNSDiagnostic()
            return diagnostic.run_full_diagnosis()
        except ImportError:
            return {'error': 'DNS诊断模块未找到'}
    
    def _check_mock(self) -> Dict[str, Any]:
        """模拟数据测试"""
        return {
            'system': {
                'os': 'Linux',
                'platform': 'Linux-5.4.0-x86_64',
                'architecture': 'x86_64',
                'hostname': 'mock-host',
                'python_version': '3.10.0'
            },
            'network': {
                'connectivity': [
                    {'name': '本地回环', 'host': '127.0.0.1', 'connected': True},
                    {'name': 'Google DNS', 'host': '8.8.8.8', 'connected': True}
                ],
                'ping_stability': {
                    'target': '8.8.8.8',
                    'sent': 10,
                    'received': 10,
                    'loss_rate': 0.0,
                    'avg_latency': 25.5
                }
            },
            'hardware': {
                'detected': True,
                'device_count': 1,
                'devices': [{
                    'npu_id': 0,
                    'chip_name': 'Ascend 910B',
                    'series': 'Atlas 300系',
                    'tops': 376,
                    'health': 'OK'
                }]
            },
            'dependencies': {
                'required': 5,
                'installed': 5,
                'missing': [],
                'ok': True
            },
            'mock_data': True
        }
    
    def _generate_summary(self):
        """生成综合摘要"""
        # 计算评分
        score = 100
        issues = []
        
        # 检查系统
        if 'system' in self.results:
            version = self.results['system'].get('python_version', '')
            if version and int(version.split('.')[1]) < 9:
                score -= 20
                issues.append('Python版本过低')
        
        # 检查网络
        if 'network_basic' in self.results or 'network_full' in self.results:
            network = self.results.get('network_basic') or self.results.get('network_full')
            if network:
                connectivity = network.get('connectivity', [])
                if not all(c.get('connected') for c in connectivity):
                    score -= 30
                    issues.append('网络连接异常')
        
        # 检查依赖
        if 'dependencies' in self.results:
            deps = self.results['dependencies']
            if not deps.get('ok'):
                score -= len(deps.get('missing', [])) * 10
                issues.append(f'缺失依赖: {", ".join(deps.get("missing", []))}')
        
        # 检查硬件
        if 'hardware_basic' in self.results or 'hardware_full' in self.results:
            hardware = self.results.get('hardware_basic') or self.results.get('hardware_full')
            if hardware and hardware.get('error'):
                score -= 10
                issues.append('硬件检测失败')
        
        self.results['summary'] = {
            'overall_score': max(0, score),
            'issues': issues,
            'duration_ms': round((self.end_time - self.start_time) * 1000, 2),
            'mode': self.mode
        }
    
    def generate_report(self) -> str:
        """生成文本报告"""
        summary = self.results.get('summary', {})
        score = summary.get('overall_score', 0)
        
        report = []
        report.append("="*60)
        report.append(f"    NASTool {self.get_mode_info()['name']}诊断报告")
        report.append("="*60)
        
        # 摘要
        report.append(f"\n📊 诊断摘要")
        report.append(f"   综合评分: {score}/100")
        report.append(f"   耗时: {summary.get('duration_ms', 0)/1000:.2f}秒")
        
        if summary.get('issues'):
            report.append(f"\n⚠️ 发现问题:")
            for issue in summary['issues']:
                report.append(f"   - {issue}")
        
        # 系统信息
        if 'system' in self.results:
            sys_info = self.results['system']
            report.append(f"\n🖥️ 系统信息")
            report.append(f"   操作系统: {sys_info.get('os')}")
            report.append(f"   架构: {sys_info.get('architecture')}")
            report.append(f"   Python: {sys_info.get('python_version')}")
        
        # 网络信息
        if 'network_basic' in self.results or 'network_full' in self.results:
            network = self.results.get('network_basic') or self.results.get('network_full')
            report.append(f"\n🌐 网络状态")
            for conn in network.get('connectivity', []):
                status = "✅" if conn.get('connected') else "❌"
                report.append(f"   {status} {conn.get('name')}")
        
        # 依赖信息
        if 'dependencies' in self.results:
            deps = self.results['dependencies']
            report.append(f"\n📦 依赖状态")
            report.append(f"   已安装: {deps.get('installed')}/{deps.get('required')}")
        
        # 硬件信息
        if 'hardware_basic' in self.results or 'hardware_full' in self.results:
            hardware = self.results.get('hardware_basic') or self.results.get('hardware_full')
            report.append(f"\n🤖 硬件检测")
            if hardware.get('detected'):
                report.append(f"   ✅ 检测到AI硬件")
                report.append(f"   设备数量: {hardware.get('device_count', 0)}")
            else:
                report.append(f"   ❌ 未检测到AI硬件")
        
        report.append("\n" + "="*60)
        return '\n'.join(report)
    
    def save_results(self, filename: str):
        """保存结果到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"📄 结果已保存到: {filename}")

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='快速诊断工具')
    parser.add_argument('--mode', '-m', choices=['quick', 'full', 'network', 'hardware', 'mock'],
                        default='quick', help='诊断模式')
    parser.add_argument('--output', '-o', help='输出JSON文件')
    args = parser.parse_args()
    
    # 运行诊断
    diagnose = QuickDiagnose(args.mode)
    results = diagnose.run()
    
    # 打印报告
    print("\n" + diagnose.generate_report())
    
    # 保存结果
    if args.output:
        diagnose.save_results(args.output)

if __name__ == "__main__":
    main()
