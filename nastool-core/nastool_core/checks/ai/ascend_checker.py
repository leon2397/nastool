#!/usr/bin/env python3
"""
昇腾芯片检测模块 - 增强版
支持检测昇腾芯片硬件、驱动、固件、CANN等
继承自Check基类，支持准确性保障
"""

import os
import subprocess
import re
from typing import Dict, List, Any, Optional

from nastool_core.checks.base import Check, CheckResult, CheckCategory, CheckSeverity


class AscendChecker(Check):
    """昇腾芯片检测工具 - 继承自Check基类"""
    
    check_id = "ascend_check"
    category = CheckCategory.AI
    title = "Ascend NPU Check"
    description = "检测昇腾芯片硬件、驱动、固件、CANN等组件"
    
    def __init__(self):
        super().__init__()  # 调用父类初始化，获取准确性保障能力
        self.results = {}
    
    def detect_ascend_hardware(self):
        """检测昇腾硬件"""
        hardware_info = {
            'detected': False,
            'devices': [],
            'device_count': 0,
            'chip_types': [],
            'total_tops': 0,
            'total_memory_mb': 0
        }
        
        # 检查是否安装了npu-smi
        npu_smi_path = self._find_npu_smi()
        if npu_smi_path:
            hardware_info['npu_smi_installed'] = True
            hardware_info['npu_smi_path'] = npu_smi_path
            
            # 获取NPU信息
            info = self._get_npu_info(npu_smi_path)
            hardware_info.update(info)
        
        # 通过其他方式检测
        if not hardware_info['detected']:
            # 检查Ascend相关目录
            if os.path.exists('/usr/local/Ascend') or os.path.exists('/usr/lib64/libascendcl.so'):
                hardware_info['detected'] = True
                
            # 检查USB设备
            try:
                result = subprocess.run(
                    ['lsusb'], capture_output=True, text=True, timeout=5
                )
                if 'Ascend' in result.stdout:
                    hardware_info['detected'] = True
                    hardware_info['device_count'] = result.stdout.count('Ascend')
            except:
                pass
            
            # 检查PCI设备
            try:
                result = subprocess.run(
                    ['lspci'], capture_output=True, text=True, timeout=5
                )
                if 'Huawei' in result.stdout and ('AI' in result.stdout or 'NPU' in result.stdout):
                    hardware_info['detected'] = True
            except:
                pass
        
        self.results['hardware'] = hardware_info
        return hardware_info
    
    def _find_npu_smi(self):
        """查找npu-smi命令路径"""
        for path in ["npu-smi", "/usr/local/bin/npu-smi", "/usr/bin/npu-smi"]:
            try:
                result = subprocess.run(
                    [path, "-h"], capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    return path
            except:
                continue
        return None
    
    def _get_npu_info(self, npu_smi_path):
        """获取NPU详细信息"""
        result = {
            'detected': True,
            'devices': [],
            'device_count': 0,
            'chip_types': [],
            'total_tops': 0,
            'total_memory_mb': 0
        }
        
        try:
            output = subprocess.run(
                [npu_smi_path, 'info'], capture_output=True, text=True, timeout=10
            )
            
            if output.returncode == 0 and output.stdout:
                devices = self._parse_npu_smi_info(output.stdout)
                result['devices'] = devices
                result['device_count'] = len(devices)
                
                for device in devices:
                    chip_type = device.get('chip_name')
                    if chip_type and chip_type not in result['chip_types']:
                        result['chip_types'].append(chip_type)
                    result['total_tops'] += device.get('tops', 0)
                    result['total_memory_mb'] += device.get('memory_total_mb', 0)
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _parse_npu_smi_info(self, output):
        """解析npu-smi info输出"""
        devices = []
        device_blocks = re.split(r"NPU\s+ID\s*:", output)[1:]
        
        chip_info_map = {
            "Ascend 310": {"series": "Atlas 200系", "tops": 22, "typical_power": 8},
            "Ascend 310P": {"series": "Atlas 200系", "tops": 44, "typical_power": 10},
            "Ascend 910": {"series": "Atlas 300系", "tops": 256, "typical_power": 310},
            "Ascend 910B": {"series": "Atlas 300系", "tops": 376, "typical_power": 350},
            "Ascend 910P": {"series": "Atlas 300系", "tops": 512, "typical_power": 400},
            "Ascend 310B": {"series": "Atlas 500系", "tops": 40, "typical_power": 12},
            "Ascend 310B1": {"series": "Atlas A2 Lite", "tops": 88, "typical_power": 20},
            "Ascend 910B1": {"series": "Atlas A2", "tops": 280, "typical_power": 300},
        }
        
        for block in device_blocks:
            device = {}
            
            # NPU ID
            m = re.search(r"(\d+)", block)
            if m:
                device["npu_id"] = int(m.group(1))
            
            # Chip Name
            m = re.search(r"Chip\s+Name\s*:\s*(.+)", block, re.IGNORECASE)
            if m:
                device["chip_name"] = m.group(1).strip()
                chip_info = chip_info_map.get(device["chip_name"], {})
                device["series"] = chip_info.get("series", "Unknown")
                device["tops"] = chip_info.get("tops", 0)
                device["typical_power"] = chip_info.get("typical_power", 0)
            
            # Memory Usage
            m = re.search(r"Memory\s+Usage\s*:\s*(\d+)\s*/\s*(\d+)\s*MB", block, re.IGNORECASE)
            if m:
                device["memory_used_mb"] = int(m.group(1))
                device["memory_total_mb"] = int(m.group(2))
            
            # HBM Usage
            m = re.search(r"HBM\s+Usage\s*:\s*(\d+)\s*/\s*(\d+)\s*MB", block, re.IGNORECASE)
            if m:
                device["hbm_used_mb"] = int(m.group(1))
                device["hbm_total_mb"] = int(m.group(2))
            
            # Power
            m = re.search(r"Power\s*:\s*([\d.]+)\s*W", block, re.IGNORECASE)
            if m:
                device["power_w"] = float(m.group(1))
            
            # Temperature
            m = re.search(r"Temp\s*:\s*([\d.]+)\s*C", block, re.IGNORECASE)
            if m:
                device["temperature_c"] = float(m.group(1))
            
            # AICore Util
            m = re.search(r"AICore\s+Util\s*:\s*(\d+)\s*%", block, re.IGNORECASE)
            if m:
                device["aicore_util_pct"] = int(m.group(1))
            
            # Health
            m = re.search(r"Health\s*:\s*(\w+)", block, re.IGNORECASE)
            if m:
                device["health"] = m.group(1).upper()
            
            devices.append(device)
        
        return devices
    
    def detect_cann_version(self):
        """检测CANN版本"""
        cann_info = {
            'installed': False,
            'version': None,
            'ascend_home': None,
            'toolkit_home': None
        }
        
        # 检查环境变量
        cann_info['ascend_home'] = os.environ.get("ASCEND_HOME")
        cann_info['toolkit_home'] = os.environ.get("ASCEND_TOOLKIT_HOME")
        
        # 从version.cfg获取版本
        for home in [cann_info['ascend_home'], cann_info['toolkit_home'], '/usr/local/Ascend']:
            if home and os.path.exists(home):
                version_file = os.path.join(home, "version.cfg")
                if os.path.isfile(version_file):
                    try:
                        with open(version_file, "r", errors="ignore") as f:
                            content = f.read()
                            m = re.search(r"Version\s*[:=]\s*([^\n]+)", content)
                            if m:
                                cann_info['version'] = m.group(1).strip()
                                cann_info['installed'] = True
                                break
                    except:
                        pass
        
        # 从npu-smi获取版本
        if not cann_info['installed']:
            try:
                result = subprocess.run(
                    ['npu-smi', 'info'], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    m = re.search(r"CANN[:\s]+([\d.]+)", result.stdout)
                    if m:
                        cann_info['version'] = m.group(1)
                        cann_info['installed'] = True
            except:
                pass
        
        self.results['cann'] = cann_info
        return cann_info
    
    def detect_driver_version(self):
        """检测驱动版本"""
        driver_info = {
            'installed': False,
            'version': None
        }
        
        try:
            result = subprocess.run(
                ['npu-smi', 'info'], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                m = re.search(r"Driver\s*[:=]\s*([\d.]+)", result.stdout)
                if m:
                    driver_info['version'] = m.group(1)
                    driver_info['installed'] = True
        except:
            pass
        
        self.results['driver'] = driver_info
        return driver_info
    
    def detect_firmware_version(self):
        """检测固件版本"""
        firmware_info = {
            'installed': False,
            'version': None
        }
        
        try:
            result = subprocess.run(
                ['npu-smi', 'info'], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                m = re.search(r"Firmware\s*[:=]\s*([\d.]+)", result.stdout)
                if m:
                    firmware_info['version'] = m.group(1)
                    firmware_info['installed'] = True
        except:
            pass
        
        self.results['firmware'] = firmware_info
        return firmware_info
    
    def check_acl_available(self):
        """检查ACL是否可用"""
        acl_info = {
            'available': False,
            'version': None,
            'error': None
        }
        
        try:
            result = subprocess.run(
                ['python3', '-c', 'import acl; print(acl.get_version())'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout:
                acl_info['available'] = True
                acl_info['version'] = result.stdout.strip()
            else:
                acl_info['error'] = result.stderr.strip() if result.stderr else "未知错误"
        except Exception as e:
            acl_info['error'] = str(e)
        
        self.results['acl'] = acl_info
        return acl_info
    
    def check_device_health(self):
        """检查设备健康状态"""
        health_info = {
            'overall_status': 'UNKNOWN',
            'devices': [],
            'issues': []
        }
        
        hardware = self.results.get('hardware', {})
        devices = hardware.get('devices', [])
        
        for device in devices:
            device_health = {
                'npu_id': device.get('npu_id'),
                'chip_name': device.get('chip_name'),
                'health': device.get('health', 'UNKNOWN'),
                'temperature_c': device.get('temperature_c'),
                'power_w': device.get('power_w'),
                'memory_usage_pct': device.get('memory_util_pct'),
                'hbm_usage_pct': device.get('hbm_util_pct'),
                'aicore_util_pct': device.get('aicore_util_pct')
            }
            
            # 检查温度
            if device.get('temperature_c', 0) > 85:
                health_info['issues'].append(
                    f"NPU {device.get('npu_id')} 温度过高: {device['temperature_c']}C"
                )
            
            # 检查健康状态
            if device.get('health') not in ['OK', 'NORMAL']:
                health_info['issues'].append(
                    f"NPU {device.get('npu_id')} 健康状态异常: {device.get('health')}"
                )
            
            health_info['devices'].append(device_health)
        
        # 确定整体状态
        if not devices:
            health_info['overall_status'] = 'NO_DEVICE'
        elif health_info['issues']:
            health_info['overall_status'] = 'ERROR'
        else:
            health_info['overall_status'] = 'OK'
        
        self.results['health'] = health_info
        return health_info
    
    def run(self) -> CheckResult:
        """运行检测 - 实现Check基类的run方法"""
        # 收集多源数据
        data_sources = []
        
        # 数据源1: 硬件检测
        hardware = self.detect_ascend_hardware()
        if hardware.get('detected'):
            data_sources.append(self._create_data_source_result(
                hardware['device_count'], 'hardware_detection', confidence=0.95
            ))
        
        # 数据源2: CANN检测
        cann = self.detect_cann_version()
        if cann.get('installed'):
            data_sources.append(self._create_data_source_result(
                cann['version'], 'cann_detection', confidence=0.9
            ))
        
        # 数据源3: 驱动检测
        driver = self.detect_driver_version()
        if driver.get('installed'):
            data_sources.append(self._create_data_source_result(
                driver['version'], 'driver_detection', confidence=0.85
            ))
        
        # 数据源4: ACL检测
        acl = self.check_acl_available()
        if acl.get('available'):
            data_sources.append(self._create_data_source_result(
                acl['version'], 'acl_detection', confidence=0.92
            ))
        
        # 数据源5: 健康检查
        health = self.check_device_health()
        data_sources.append(self._create_data_source_result(
            health['overall_status'], 'health_check', confidence=0.88
        ))
        
        # 判断检测结果
        hardware_detected = hardware.get('detected', False)
        all_components_ok = all([
            hardware_detected,
            cann.get('installed', False),
            driver.get('installed', False),
            acl.get('available', False),
            health.get('overall_status') == 'OK'
        ])
        
        if hardware_detected:
            if all_components_ok:
                result = CheckResult(
                    check_id=self.check_id,
                    category=self.category,
                    title=self.title,
                    passed=True,
                    current=f"{hardware.get('device_count', 0)} device(s) detected",
                    expected="Ascend hardware detected",
                    message=f"✅ 昇腾芯片检测通过! 检测到 {hardware.get('device_count', 0)} 个设备",
                    severity=CheckSeverity.PASSED,
                    details={
                        'hardware': hardware,
                        'cann': cann,
                        'driver': driver,
                        'firmware': self.results.get('firmware', {}),
                        'acl': acl,
                        'health': health
                    }
                )
            else:
                issues = []
                if not cann.get('installed'):
                    issues.append("CANN未安装")
                if not driver.get('installed'):
                    issues.append("驱动未安装")
                if not acl.get('available'):
                    issues.append("ACL不可用")
                if health.get('overall_status') != 'OK':
                    issues.extend(health.get('issues', []))
                
                result = CheckResult(
                    check_id=self.check_id,
                    category=self.category,
                    title=self.title,
                    passed=False,
                    current=f"{hardware.get('device_count', 0)} device(s) with issues",
                    expected="All components working",
                    message=f"❌ 昇腾芯片检测存在问题: {', '.join(issues)}",
                    severity=CheckSeverity.WARNING,
                    details={
                        'hardware': hardware,
                        'cann': cann,
                        'driver': driver,
                        'firmware': self.results.get('firmware', {}),
                        'acl': acl,
                        'health': health,
                        'issues': issues
                    }
                )
        else:
            result = CheckResult(
                check_id=self.check_id,
                category=self.category,
                title=self.title,
                passed=True,
                current="No Ascend hardware detected",
                expected="Optional component",
                message="ℹ️ 未检测到昇腾硬件，这是可选组件",
                severity=CheckSeverity.INFO,
                details={
                    'hardware': hardware,
                    'cann': cann,
                    'driver': driver,
                    'firmware': self.results.get('firmware', {}),
                    'acl': acl,
                    'health': health
                }
            )
        
        # 使用准确性保障方法增强结果
        return self._enhance_result_with_accuracy(result, data_sources)
