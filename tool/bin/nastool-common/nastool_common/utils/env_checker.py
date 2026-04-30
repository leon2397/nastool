#!/usr/bin/env python3
"""
环境自检模块 - 检测设备兼容性
支持检测Python版本、系统类型、架构、网络连接等
"""

import os
import sys
import platform
import subprocess
import socket
from typing import Dict, List, Tuple

class EnvChecker:
    """环境检查器"""
    
    def __init__(self):
        self.results = {
            'python': {},
            'system': {},
            'network': {},
            'dependencies': {},
            'compatibility': {}
        }
    
    def check_python_version(self, min_version=(3, 9)):
        """检查Python版本"""
        version = sys.version_info
        is_ok = version >= min_version
        
        self.results['python'] = {
            'version': f"{version.major}.{version.minor}.{version.micro}",
            'required': f"{min_version[0]}.{min_version[1]}",
            'ok': is_ok,
            'architecture': platform.architecture()[0],
            'implementation': platform.python_implementation()
        }
        
        return is_ok
    
    def check_system_info(self):
        """检查系统信息"""
        self.results['system'] = {
            'os': platform.system(),
            'os_version': platform.version(),
            'platform': platform.platform(),
            'architecture': platform.machine(),
            'hostname': platform.node(),
            'processor': platform.processor(),
            'release': platform.release()
        }
        
        return self.results['system']
    
    def check_network(self, hosts=None):
        """检查网络连接"""
        hosts = hosts or [
            ('192.168.1.1', 22, '内网网关'),
            ('8.8.8.8', 53, '外网DNS'),
            ('www.baidu.com', 80, '百度')
        ]
        
        network_results = []
        all_ok = True
        
        for host, port, desc in hosts:
            result = self._check_host_connectivity(host, port, desc)
            network_results.append(result)
            if not result['ok']:
                all_ok = False
        
        self.results['network'] = {
            'tests': network_results,
            'all_ok': all_ok
        }
        
        return all_ok
    
    def _check_host_connectivity(self, host, port, desc):
        """检查单个主机连接性"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return {
                'host': host,
                'port': port,
                'description': desc,
                'ok': result == 0,
                'error': None if result == 0 else f"连接失败 (code: {result})"
            }
        except Exception as e:
            return {
                'host': host,
                'port': port,
                'description': desc,
                'ok': False,
                'error': str(e)
            }
    
    def check_dependencies(self, required_deps):
        """检查依赖是否安装"""
        missing = []
        installed = []
        
        for dep in required_deps:
            if self._is_dep_installed(dep):
                installed.append(dep)
            else:
                missing.append(dep)
        
        self.results['dependencies'] = {
            'required': len(required_deps),
            'installed': len(installed),
            'missing': missing,
            'ok': len(missing) == 0
        }
        
        return len(missing) == 0
    
    def _is_dep_installed(self, dep_name):
        """检查单个依赖是否安装"""
        module_map = {
            'paramiko': 'paramiko',
            'pyusb': 'usb',
            'requests': 'requests',
            'websocket-client': 'websocket',
            'pydantic': 'pydantic',
            'rich': 'rich',
            'psutil': 'psutil',
            'typing-extensions': 'typing_extensions',
            'packaging': 'packaging'
        }
        
        module_name = module_map.get(dep_name, dep_name.replace('-', '_'))
        
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    def check_disk_space(self, path='.', min_mb=500):
        """检查磁盘空间"""
        try:
            disk = os.statvfs(path)
            free_mb = (disk.f_frsize * disk.f_bfree) / (1024 * 1024)
            
            return {
                'path': path,
                'free_mb': round(free_mb, 2),
                'min_required_mb': min_mb,
                'ok': free_mb >= min_mb
            }
        except Exception as e:
            return {
                'path': path,
                'free_mb': None,
                'min_required_mb': min_mb,
                'ok': False,
                'error': str(e)
            }
    
    def check_ai_hardware(self):
        """检查AI硬件（昇腾、英伟达等）"""
        hardware_info = {
            'has_nvidia': False,
            'has_ascend': False,
            'has_rockchip': False,
            'has_sophon': False,
            'gpu_count': 0,
            'npu_count': 0
        }
        
        # 检查英伟达
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=count', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                hardware_info['has_nvidia'] = True
                hardware_info['gpu_count'] = int(result.stdout.strip())
        except:
            pass
        
        # 检查昇腾
        if os.path.exists('/usr/local/Ascend') or os.path.exists('/usr/lib64/libascendcl.so'):
            hardware_info['has_ascend'] = True
            # 尝试检测NPU数量
            try:
                result = subprocess.run(
                    ['lsusb'], capture_output=True, text=True, timeout=5
                )
                if 'Ascend' in result.stdout:
                    hardware_info['npu_count'] = result.stdout.count('Ascend')
            except:
                pass
        
        # 检查瑞芯微
        try:
            result = subprocess.run(
                ['cat', '/proc/cpuinfo'], capture_output=True, text=True, timeout=5
            )
            if 'rockchip' in result.stdout.lower():
                hardware_info['has_rockchip'] = True
        except:
            pass
        
        # 检查算能
        try:
            result = subprocess.run(
                ['lsusb'], capture_output=True, text=True, timeout=5
            )
            if 'Sophon' in result.stdout:
                hardware_info['has_sophon'] = True
        except:
            pass
        
        self.results['hardware'] = hardware_info
        return hardware_info
    
    def check_compatibility(self):
        """综合检查兼容性"""
        issues = []
        warnings = []
        
        # 检查架构兼容性
        arch = platform.machine()
        supported_arches = ['x86_64', 'aarch64', 'armv7l']
        
        if arch not in supported_arches:
            issues.append(f"不支持的架构: {arch}")
        else:
            warnings.append(f"架构: {arch} (支持)")
        
        # 检查系统类型
        os_type = platform.system()
        if os_type not in ['Linux']:
            issues.append(f"不支持的操作系统: {os_type}")
        else:
            warnings.append(f"操作系统: {os_type} (支持)")
        
        # 检查Python版本
        version = sys.version_info
        if version < (3, 9):
            issues.append(f"Python版本过低: {version.major}.{version.minor} (需要 >= 3.9)")
        else:
            warnings.append(f"Python版本: {version.major}.{version.minor}.{version.micro} (支持)")
        
        self.results['compatibility'] = {
            'issues': issues,
            'warnings': warnings,
            'ok': len(issues) == 0
        }
        
        return len(issues) == 0
    
    def run_full_check(self):
        """运行完整的环境检查"""
        print("🔍 开始环境自检...")
        
        # 检查Python版本
        print("  🐍 检查Python版本...")
        self.check_python_version()
        
        # 检查系统信息
        print("  🖥️ 检查系统信息...")
        self.check_system_info()
        
        # 检查兼容性
        print("  ✅ 检查兼容性...")
        self.check_compatibility()
        
        # 检查网络
        print("  🌐 检查网络连接...")
        self.check_network()
        
        # 检查依赖
        print("  📦 检查依赖...")
        required_deps = ['paramiko', 'requests', 'pydantic', 'rich', 'psutil']
        self.check_dependencies(required_deps)
        
        # 检查磁盘空间
        print("  💾 检查磁盘空间...")
        disk_info = self.check_disk_space('/')
        self.results['disk'] = disk_info
        
        # 检查AI硬件
        print("  🤖 检查AI硬件...")
        self.check_ai_hardware()
        
        print("✅ 环境自检完成!")
        return self.results
    
    def generate_report(self):
        """生成检查报告"""
        report = []
        report.append("="*60)
        report.append("    NASTool 环境自检报告")
        report.append("="*60)
        
        # Python信息
        py = self.results.get('python', {})
        status = "✅" if py.get('ok') else "❌"
        report.append(f"\n{status} Python环境")
        report.append(f"   版本: {py.get('version', '未知')}")
        report.append(f"   要求: >= {py.get('required', '3.9')}")
        report.append(f"   架构: {py.get('architecture', '未知')}")
        
        # 系统信息
        sys_info = self.results.get('system', {})
        report.append(f"\n🖥️ 系统信息")
        report.append(f"   操作系统: {sys_info.get('os', '未知')}")
        report.append(f"   平台: {sys_info.get('platform', '未知')}")
        report.append(f"   架构: {sys_info.get('architecture', '未知')}")
        
        # 兼容性检查
        compat = self.results.get('compatibility', {})
        report.append(f"\n✅ 兼容性检查")
        if compat.get('ok'):
            report.append(f"   状态: 兼容")
            for w in compat.get('warnings', []):
                report.append(f"   ⚠️ {w}")
        else:
            report.append(f"   状态: 不兼容")
            for issue in compat.get('issues', []):
                report.append(f"   ❌ {issue}")
        
        # 网络检查
        network = self.results.get('network', {})
        report.append(f"\n🌐 网络连接")
        for test in network.get('tests', []):
            status = "✅" if test['ok'] else "❌"
            report.append(f"   {status} {test['description']} ({test['host']}:{test['port']})")
        
        # 依赖检查
        deps = self.results.get('dependencies', {})
        report.append(f"\n📦 依赖状态")
        report.append(f"   已安装: {deps.get('installed', 0)}/{deps.get('required', 0)}")
        if deps.get('missing'):
            report.append(f"   缺失: {', '.join(deps['missing'])}")
        
        # 磁盘空间
        disk = self.results.get('disk', {})
        report.append(f"\n💾 磁盘空间")
        status = "✅" if disk.get('ok') else "❌"
        report.append(f"   {status} 可用空间: {disk.get('free_mb', 0):.2f} MB")
        
        # AI硬件
        hardware = self.results.get('hardware', {})
        report.append(f"\n🤖 AI硬件检测")
        if hardware.get('has_nvidia'):
            report.append(f"   ✅ 英伟达 GPU x {hardware.get('gpu_count', 0)}")
        if hardware.get('has_ascend'):
            report.append(f"   ✅ 昇腾 NPU x {hardware.get('npu_count', 0)}")
        if hardware.get('has_rockchip'):
            report.append(f"   ✅ 瑞芯微")
        if hardware.get('has_sophon'):
            report.append(f"   ✅ 算能")
        if not any([hardware.get('has_nvidia'), hardware.get('has_ascend'), 
                   hardware.get('has_rockchip'), hardware.get('has_sophon')]):
            report.append(f"   ⚠️ 未检测到AI加速硬件")
        
        report.append("\n" + "="*60)
        
        # 综合评估
        all_ok = all([
            self.results.get('python', {}).get('ok', False),
            self.results.get('compatibility', {}).get('ok', False),
            self.results.get('dependencies', {}).get('ok', False),
            self.results.get('disk', {}).get('ok', False)
        ])
        
        if all_ok:
            report.append("✅ 环境检查通过! NASTool可以正常运行")
        else:
            report.append("❌ 环境检查未通过，请解决上述问题后再运行")
        
        report.append("="*60)
        
        return '\n'.join(report)

def main():
    """命令行入口"""
    checker = EnvChecker()
    checker.run_full_check()
    print(checker.generate_report())

if __name__ == "__main__":
    main()
