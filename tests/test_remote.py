#!/usr/bin/env python3
# 远程检测测试脚本

import sys
import os

# 添加模块路径
base_path = os.path.dirname(os.path.dirname(__file__))  # 项目根目录
adapters_path = os.path.join(base_path, 'nastool-adapters')
core_path = os.path.join(base_path, 'nastool-core')
common_path = os.path.join(base_path, 'nastool-common')
sys.path.insert(0, adapters_path)
sys.path.insert(0, core_path)
sys.path.insert(0, common_path)
print(f"添加模块路径: {adapters_path}")
print(f"添加核心模块路径: {core_path}")
print(f"添加公共模块路径: {common_path}")
print(f"当前Python路径: {sys.path}")

try:
    from nastool_adapters.http_detector import RemoteHTTPDetector
    print("导入模块成功")
except Exception as e:
    print(f"导入模块失败: {e}")
    # 检查模块文件是否存在
    module_file = os.path.join(adapters_path, 'nastool_adapters', 'http_detector.py')
    print(f"模块文件是否存在: {os.path.exists(module_file)}")
    # 检查核心模块是否存在
    core_file = os.path.join(core_path, 'nastool_core', '__init__.py')
    print(f"核心模块文件是否存在: {os.path.exists(core_file)}")
    # 检查公共模块是否存在
    common_file = os.path.join(common_path, 'nastool_common', '__init__.py')
    print(f"公共模块文件是否存在: {os.path.exists(common_file)}")
    sys.exit(1)

def test_remote_detection():
    print("=== 远程检测测试 ===")
    
    # 测试本地设备的HTTP API
    target = "http://192.168.1.123:8000"
    print(f"测试目标: {target}")
    
    try:
        detector = RemoteHTTPDetector(target)
        print("创建检测器成功")
        
        # 尝试连接
        connected = detector.connect()
        print(f"连接状态: {connected}")
        
        if connected:
            # 获取设备信息
            device_info = detector.get_device_info()
            print(f"设备信息: {device_info}")
            
            # 运行诊断
            print("\n运行远程诊断...")
            results = detector.run_diagnosis(full_mode=False)
            print(f"诊断结果数量: {len(results)}")
            
            if results:
                print("\n诊断结果:")
                for result in results[:5]:  # 只显示前5个结果
                    print(f"- {result.title}: {result.status}")
        else:
            print("无法连接到目标设备")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    test_remote_detection()