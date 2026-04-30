#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 SSH 检测器
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nastool-v4.0.0'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nastool-v4.0.0', 'nastool-adapters'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nastool-v4.0.0', 'nastool-core'))

try:
    from nastool_adapters.ssh_detector import RemoteSSHDetector
    print("[OK] 导入 SSH 检测器成功")
except Exception as e:
    print(f"[ERROR] 导入 SSH 检测器失败: {e}")
    sys.exit(1)

# 测试 SSH 检测器
print("\n=== 测试 SSH 检测器 ===")

# 创建检测器实例（使用默认值，实际测试时需要修改为真实的 SSH 配置）
detector = RemoteSSHDetector(
    host="192.168.1.100",
    port=22,
    username="admin",
    password=""
)

print(f"创建检测器成功: {detector.host}:{detector.port}")

# 测试连接
print("\n测试连接...")
connected = detector.connect()
print(f"连接状态: {connected}")

if connected:
    # 测试获取设备信息
    print("\n测试获取设备信息...")
    device_info = detector.get_device_info()
    if device_info:
        print(f"设备信息: {device_info.device_name} ({device_info.hostname})")
        print(f"CPU: {device_info.cpu_model}")
        print(f"内存: {device_info.memory_total} MB")
    else:
        print("获取设备信息失败")
    
    # 测试运行诊断
    print("\n测试运行诊断...")
    results = detector.run_diagnosis(full_mode=False)
    print(f"诊断结果数量: {len(results)}")
    
    # 打印前几个结果
    if results:
        print("\n前 5 个诊断结果:")
        for i, result in enumerate(results[:5]):
            print(f"{i+1}. {result.title}: {result.severity.value} - {result.current}")
    
    # 断开连接
    detector.disconnect()
    print("\n已断开连接")
else:
    print("连接失败，无法进行后续测试")

print("\n=== 测试完成 ===")
