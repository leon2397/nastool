#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查设备型号，识别是否为Jetson设备"""
import os
import sys


def detect_device_type():
    """检测设备类型"""
    device_info = {
        "model": None,
        "is_jetson": False,
        "device_type": "unknown"
    }
    
    # 尝试读取设备型号文件
    model_path = "/proc/device-tree/model"
    if os.path.exists(model_path):
        try:
            with open(model_path, 'rb') as f:
                model = f.read().strip()
            
            # 尝试解码
            try:
                decoded = model.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    decoded = model.decode('latin-1')
                except UnicodeDecodeError:
                    decoded = str(model)
            
            device_info["model"] = decoded
            model_lower = decoded.lower()
            
            # 检测设备类型
            if 'jetson' in model_lower:
                device_info["is_jetson"] = True
                device_info["device_type"] = "jetson"
            elif 'nvidia' in model_lower:
                device_info["device_type"] = "nvidia"
            elif 'rockchip' in model_lower or 'rk3' in model_lower:
                device_info["device_type"] = "rockchip"
            elif 'ascend' in model_lower:
                device_info["device_type"] = "ascend"
            elif 'sophon' in model_lower:
                device_info["device_type"] = "sophon"
            elif 'raspberry' in model_lower:
                device_info["device_type"] = "raspberry"
                
        except Exception as e:
            print(f"读取设备型号失败: {e}")
    else:
        print(f"设备型号文件不存在: {model_path}")
    
    return device_info


def main():
    """主函数"""
    print("=== 设备类型检测 ===")
    
    device_info = detect_device_type()
    
    if device_info["model"]:
        print(f"设备型号: {repr(device_info['model'])}")
    else:
        print("无法获取设备型号")
    
    print(f"是否为Jetson: {device_info['is_jetson']}")
    print(f"设备类型: {device_info['device_type']}")


if __name__ == "__main__":
    main()
