#!/usr/bin/env python3
"""系统健康检查模块"""

import os
import sys
import json
import platform
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class HealthChecker:
    """健康检查器"""
    
    CHECKS = {
        'system_info': '系统信息',
        'disk_health': '磁盘健康',
        'memory_health': '内存健康',
        'network_health': '网络健康',
        'dependency_check': '依赖检查',
        'service_status': '服务状态',
        'security_check': '安全检查'
    }
    
    def __init__(self, device_id=None):
        self.device_id = device_id
        self.results = {}
    
    def run_all_checks(self):
        """运行所有检查"""
        print('🔍 正在进行系统健康检查...')
        
        for check_key, check_name in self.CHECKS.items():
            print(f'  检查 {check_name}...')
            try:
                method = getattr(self, f'_check_{check_key}')
                result = method()
                self.results[check_key] = result
            except Exception as e:
                self.results[check_key] = {
                    'status': 'error',
                    'message': str(e),
                    'details': {}
                }
        
        return self.results
    
    def _check_system_info(self):
        """检查系统信息"""
        info = {
            'os': platform.system(),
            'os_version': platform.version(),
            'release': platform.release(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version()
        }
        return {
            'status': 'ok',
            'message': '系统信息正常',
            'details': info
        }
    
    def _check_disk_health(self):
        """检查磁盘健康"""
        disks = []
        thresholds = {'warning': 80, 'critical': 90}
        
        for partition in shutil.disk_usage('/'):
            pass
        
        try:
            disk = shutil.disk_usage('/')
            percent_used = (disk.used / disk.total) * 100
            
            if percent_used >= thresholds['critical']:
                status = 'critical'
                message = f'磁盘空间严重不足 ({percent_used:.1f}%)'
            elif percent_used >= thresholds['warning']:
                status = 'warning'
                message = f'磁盘空间警告 ({percent_used:.1f}%)'
            else:
                status = 'ok'
                message = f'磁盘空间正常 ({percent_used:.1f}%)'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'total_gb': disk.total / (1024**3),
                    'used_gb': disk.used / (1024**3),
                    'free_gb': disk.free / (1024**3),
                    'percent_used': percent_used,
                    'thresholds': thresholds
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'磁盘检查失败: {str(e)}',
                'details': {}
            }
    
    def _check_memory_health(self):
        """检查内存健康"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            percent_used = memory.percent
            thresholds = {'warning': 85, 'critical': 95}
            
            if percent_used >= thresholds['critical']:
                status = 'critical'
                message = f'内存使用率过高 ({percent_used:.1f}%)'
            elif percent_used >= thresholds['warning']:
                status = 'warning'
                message = f'内存使用率警告 ({percent_used:.1f}%)'
            else:
                status = 'ok'
                message = f'内存状态正常 ({percent_used:.1f}%)'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'total_gb': memory.total / (1024**3),
                    'used_gb': memory.used / (1024**3),
                    'available_gb': memory.available / (1024**3),
                    'percent_used': percent_used,
                    'thresholds': thresholds
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'内存检查失败: {str(e)}',
                'details': {}
            }
    
    def _check_network_health(self):
        """检查网络健康"""
        import socket
        
        # 根据操作系统选择不同的测试端口
        if platform.system() == 'Windows':
            # Windows 使用 HTTP 端口进行本地测试（IIS或其他服务）
            tests = {
                'dns': ('8.8.8.8', 53),
                'gateway': ('192.168.1.1', 80)
            }
        else:
            tests = {
                'localhost': ('127.0.0.1', 22),
                'dns': ('8.8.8.8', 53)
            }
        
        results = {}
        all_passed = True
        warnings = []
        
        for name, (host, port) in tests.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    results[name] = {'status': 'ok', 'message': f'{name} 连接正常'}
                else:
                    # localhost:22 端口失败在Windows上是正常的，不影响整体状态
                    if name == 'localhost' and platform.system() != 'Windows':
                        results[name] = {'status': 'failed', 'message': f'{name} 连接失败'}
                        all_passed = False
                    else:
                        results[name] = {'status': 'warning', 'message': f'{name} 端口未开放（可能正常）'}
                        warnings.append(f'{name} 端口未开放')
            except Exception as e:
                results[name] = {'status': 'error', 'message': str(e)}
                # DNS错误才视为失败
                if name == 'dns':
                    all_passed = False
        
        # 检查基本网络连通性（ping测试）
        try:
            response = os.system(f"ping -n 1 {'8.8.8.8' if platform.system() == 'Windows' else '-c 1 8.8.8.8'}")
            if response == 0:
                results['internet'] = {'status': 'ok', 'message': '外网连接正常'}
            else:
                results['internet'] = {'status': 'failed', 'message': '无法连接外网'}
                all_passed = False
        except:
            pass
        
        if all_passed:
            return {
                'status': 'ok',
                'message': '网络状态正常' if not warnings else f'网络状态正常（{", ".join(warnings)}）',
                'details': results
            }
        else:
            return {
                'status': 'warning',
                'message': '部分网络连接异常',
                'details': results
            }
    
    def _check_dependency_check(self):
        """检查依赖"""
        required = ['paramiko', 'psutil', 'requests']
        results = {}
        
        for pkg in required:
            try:
                __import__(pkg)
                results[pkg] = {'status': 'ok', 'version': self._get_version(pkg)}
            except ImportError:
                results[pkg] = {'status': 'missing', 'version': None}
        
        missing = [k for k, v in results.items() if v['status'] != 'ok']
        
        if not missing:
            return {
                'status': 'ok',
                'message': '所有依赖已安装',
                'details': results
            }
        else:
            return {
                'status': 'warning',
                'message': f'缺少依赖: {", ".join(missing)}',
                'details': results
            }
    
    def _get_version(self, pkg):
        """获取包版本"""
        try:
            import importlib.metadata
            return importlib.metadata.version(pkg)
        except:
            return 'unknown'
    
    def _check_service_status(self):
        """检查服务状态"""
        services = {}
        
        if platform.system() == 'Linux':
            try:
                import subprocess
                result = subprocess.run(
                    ['systemctl', 'list-units', '--type=service', '--state=running'],
                    capture_output=True, text=True
                )
                services['running_count'] = len(result.stdout.strip().split('\n')) - 1
                services['status'] = 'ok'
            except Exception as e:
                services['error'] = str(e)
        
        return {
            'status': 'ok' if services else 'info',
            'message': '服务检查完成',
            'details': services
        }
    
    def _check_security_check(self):
        """检查安全状态"""
        checks = []
        
        # 检查是否以root运行（仅Linux）
        if platform.system() == 'Linux':
            try:
                if os.geteuid() == 0:
                    checks.append({'name': 'root用户', 'status': 'warning', 'message': '不建议以root用户运行'})
                else:
                    checks.append({'name': '普通用户', 'status': 'ok', 'message': '以普通用户运行'})
            except AttributeError:
                checks.append({'name': '用户检查', 'status': 'info', 'message': '无法检测用户权限'})
        else:
            checks.append({'name': '操作系统', 'status': 'info', 'message': f"{platform.system()} 系统"})
        
        return {
            'status': 'ok' if all(c['status'] == 'ok' or c['status'] == 'info' for c in checks) else 'warning',
            'message': '安全检查完成',
            'details': checks
        }
    
    def generate_report(self, format='text'):
        """生成报告"""
        if format == 'json':
            return json.dumps(self.results, ensure_ascii=False, indent=2)
        
        report = []
        report.append('='*60)
        report.append('🏥 系统健康检查报告')
        report.append('='*60)
        
        status_counts = {'ok': 0, 'warning': 0, 'critical': 0, 'error': 0}
        
        for check_key, check_name in self.CHECKS.items():
            result = self.results.get(check_key, {})
            status = result.get('status', 'unknown')
            
            if status in status_counts:
                status_counts[status] += 1
            
            status_icon = {
                'ok': '✅',
                'warning': '⚠️',
                'critical': '🔴',
                'error': '❌'
            }.get(status, '❓')
            
            report.append(f'\n{status_icon} {check_name}')
            report.append(f'   {result.get("message", "无信息")}')
            
            details = result.get('details', {})
            if details:
                if isinstance(details, list):
                    # 处理列表类型的details（如安全检查）
                    for item in details:
                        if isinstance(item, dict):
                            name = item.get('name', '未知')
                            status = item.get('status', 'unknown')
                            message = item.get('message', '')
                            report.append(f'   - {name}: {message}')
                        else:
                            report.append(f'   - {item}')
                elif isinstance(details, dict):
                    # 处理字典类型的details
                    for key, value in details.items():
                        if isinstance(value, dict):
                            report.append(f'   - {key}:')
                            for k, v in value.items():
                                report.append(f'       {k}: {v}')
                        else:
                            report.append(f'   - {key}: {value}')
        
        report.append('\n' + '='*60)
        report.append(f'📊 检查结果: 正常 {status_counts["ok"]} | 警告 {status_counts["warning"]} | 严重 {status_counts["critical"]} | 错误 {status_counts["error"]}')
        
        overall_status = '✅' if status_counts['critical'] == 0 and status_counts['error'] == 0 else '⚠️'
        report.append(f'{overall_status} 系统状态: {"健康" if overall_status == "✅" else "存在问题"}')
        report.append('='*60)
        
        return '\n'.join(report)

def main():
    """命令行接口"""
    import argparse
    parser = argparse.ArgumentParser(description='系统健康检查工具')
    parser.add_argument('-f', '--format', choices=['text', 'json'], default='text', help='输出格式')
    parser.add_argument('-o', '--output', help='输出文件')
    
    args = parser.parse_args()
    
    checker = HealthChecker()
    checker.run_all_checks()
    report = checker.generate_report(args.format)
    
    print(report)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f'\n📊 报告已保存到 {args.output}')

if __name__ == '__main__':
    main()
