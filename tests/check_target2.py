#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接测试 jetpack_version 检测逻辑"""
import sys
import os


def detect_device_type():
    """检测设备类型"""
    device_info = {
        "model": None,
        "is_jetson": False,
        "is_nvidia": False
    }
    
    model_path = "/proc/device-tree/model"
    if os.path.exists(model_path):
        try:
            with open(model_path, "rb") as f:
                raw = f.read().strip()
            
            try:
                model = raw.decode("utf-8", errors="replace").replace("\x00", "").strip()
            except Exception as e:
                print(f"解码设备型号失败: {e}")
                model = str(raw)
            
            device_info["model"] = model
            model_lower = model.lower()
            
            device_info["is_jetson"] = 'jetson' in model_lower
            device_info["is_nvidia"] = 'nvidia' in model_lower
            
        except Exception as e:
            print(f"读取设备型号失败: {e}")
    else:
        print(f"设备型号文件不存在: {model_path}")
    
    return device_info

def setup_python_path():
    """设置Python路径"""
    # 尝试不同的路径
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "nastool-v4.0.0"),
        "/home/nvidia/nastool-v4.0.0",
        "/opt/nastool-v4.0.0",
        os.path.join(os.path.expanduser("~"), "nastool-v4.0.0")
    ]
    
    for path in possible_paths:
        if os.path.exists(os.path.join(path, "nastool_core")):
            sys.path.insert(0, path)
            print(f"设置 Python 路径: {path}")
            return True
    
    print("警告: 未找到 nastool-v4.0.0 目录")
    return False


def test_jetpack_version():
    """测试 jetpack_version 检测"""
    print("\n--- 运行 jetpack_version 检查 ---")
    
    try:
        from nastool_core.checks.ai.version_checker import jetpack_version
        from nastool_core.checks.base import CheckContext
        
        class DummyCtx:
            def result(self, **kwargs):
                r = kwargs
                print(f"RESULT: passed={r.get('passed')}, severity={r.get('severity')}, message={r.get('message')}")
                print(f"  current={r.get('current')}")
                return r
        
        ctx = DummyCtx()
        jetpack_version(ctx)
        return True
    except ImportError as e:
        print(f"导入模块失败: {e}")
        return False
    except Exception as e:
        print(f"执行检测时出错: {e}")
        return False


def main():
    """主函数"""
    print("=== 设备型号和 JetPack 版本检测 ===")
    
    # 检测设备类型
    device_info = detect_device_type()
    
    if device_info["model"]:
        print(f"设备型号: {repr(device_info['model'])}")
        print(f"是否为 Jetson: {device_info['is_jetson']}")
        print(f"是否为 NVIDIA 设备: {device_info['is_nvidia']}")
    else:
        print("无法获取设备型号")
    
    # 设置 Python 路径
    if setup_python_path():
        # 测试 JetPack 版本
        if device_info["is_jetson"]:
            test_jetpack_version()
        else:
            print("\n跳过 JetPack 版本检测 (非 Jetson 设备)")
    else:
        print("\n跳过 JetPack 版本检测 (无法找到模块)")


if __name__ == "__main__":
    main()