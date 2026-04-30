#!/usr/bin/env python3
# Relay Server 远程检测测试脚本

import sys
import os

# 添加模块路径
base_path = os.path.join(os.path.expanduser('~'), 'nastool-v4.0.0')
adapters_path = os.path.join(base_path, 'nastool-adapters')
core_path = os.path.join(base_path, 'nastool-core')
common_path = os.path.join(base_path, 'nastool-common')
sys.path.insert(0, adapters_path)
sys.path.insert(0, core_path)
sys.path.insert(0, common_path)
print(f"添加模块路径: {adapters_path}")
print(f"添加核心模块路径: {core_path}")
print(f"添加公共模块路径: {common_path}")

try:
    from nastool_adapters.relay_detector import RelayDetector
    print("导入模块成功")
except Exception as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)

def test_relay_detection():
    print("=== Relay Server 远程检测测试 ===")
    
    # 测试Relay Server连接
    relay_url = "http://120.77.249.3:18888"
    print(f"Relay Server URL: {relay_url}")
    
    try:
        detector = RelayDetector(relay_url)
        print("创建Relay检测器成功")
        
        # 尝试连接
        connected = detector.connect()
        print(f"连接Relay Server状态: {connected}")
        
        if connected:
            # 列出设备
            print("\n列出所有设备...")
            devices = detector.list_devices()
            print(f"设备数量: {len(devices)}")
            
            if devices:
                print("\n设备列表:")
                for device in devices:
                    print(f"- ID: {device.device_id}")
                    print(f"  名称: {device.device_name or device.device_id}")
                    print(f"  状态: {device.status}")
                    print(f"  主机名: {device.hostname}")
                    print(f"  本地IP: {device.ip_local}")
                    print(f"  类型: {device.device_type}")
                    print()
            else:
                print("无设备注册到Relay Server")
                
            # 快速扫描
            print("\n执行快速扫描...")
            scan_result = detector.quick_scan()
            print(f"扫描结果: {scan_result}")
        else:
            print("无法连接到Relay Server")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    test_relay_detection()