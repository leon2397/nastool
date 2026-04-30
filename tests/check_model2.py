#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查设备型号，识别是否为Jetson设备"""
import os


def get_device_model():
    """获取设备型号"""
    model_path = "/proc/device-tree/model"
    
    if not os.path.exists(model_path):
        print(f"错误: 设备型号文件不存在 - {model_path}")
        return None
    
    try:
        with open(model_path, "rb") as f:
            raw = f.read().strip()
        
        # 解码并清理字符串
        try:
            model = raw.decode("utf-8", errors="replace").replace("\x00", "").strip()
        except Exception as e:
            print(f"解码设备型号失败: {e}")
            model = str(raw)
        
        return model
    except Exception as e:
        print(f"读取设备型号失败: {e}")
        return None


def main():
    """主函数"""
    print("=== 设备型号检查 ===")
    
    model = get_device_model()
    
    if model:
        model_lower = model.lower()
        print(f"设备型号: {repr(model)}")
        print(f"'jetson' in model: {'jetson' in model_lower}")
        
        # 检测设备类型
        if 'jetson' in model_lower:
            print("设备类型: Jetson")
        elif 'nvidia' in model_lower:
            print("设备类型: NVIDIA")
        elif 'rockchip' in model_lower or 'rk3' in model_lower:
            print("设备类型: Rockchip")
        elif 'ascend' in model_lower:
            print("设备类型: Ascend")
        elif 'sophon' in model_lower:
            print("设备类型: Sophon")
        elif 'raspberry' in model_lower:
            print("设备类型: Raspberry Pi")
        else:
            print("设备类型: 未知")
    else:
        print("无法获取设备型号")


if __name__ == "__main__":
    main()