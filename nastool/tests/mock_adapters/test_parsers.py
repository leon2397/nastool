# -*- coding: utf-8 -*-
"""
nastool tests.mock_adapters.test_parsers - 测试 npu-smi 和 tegrastats 解析器

运行方式：
    cd D:\armtool415\nastool
    python -m pytest tests/mock_adapters/test_parsers.py -v
    # 或直接运行：
    python tests/mock_adapters/test_parsers.py
"""

from __future__ import annotations

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from adapters.ascend.common import _parse_npu_smi_list, _parse_npu_smi_query, _parse_memory
from adapters.jetson.common import _parse_tegrastats

# 直接导入 mock_data（使用相对路径）
import importlib.util

def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_current_dir = os.path.dirname(os.path.abspath(__file__))
_ascend_mock = _load_module("ascend_mock", os.path.join(_current_dir, "ascend", "mock_data.py"))
_jetson_mock = _load_module("jetson_mock", os.path.join(_current_dir, "jetson", "mock_data.py"))

ALL_ASCEND_MOCKS = _ascend_mock.ALL_ASCEND_MOCKS
ALL_JETSON_MOCKS = _jetson_mock.ALL_JETSON_MOCKS


def test_ascend_npu_smi_list():
    """Test npu-smi -i all -L parsing"""
    print("\n[Ascend] Testing npu-smi list parsing...")
    
    passed = 0
    failed = 0
    
    for mock in ALL_ASCEND_MOCKS:
        model = mock["device_model"]
        list_output = mock["npu_smi_list"]
        expected = mock["expected"]
        
        devices = _parse_npu_smi_list_from_output(list_output)
        
        if len(devices) == expected["device_count"]:
            print(f"  [OK] {model}: {len(devices)} cards")
            passed += 1
        else:
            print(f"  [FAIL] {model}: expected {expected['device_count']}, got {len(devices)}")
            failed += 1
    
    print(f"\n[Ascend] npu-smi list: {passed}/{len(ALL_ASCEND_MOCKS)} passed")
    return failed == 0


def _parse_npu_smi_list_from_output(output: str) -> list:
    """从给定输出解析设备列表（不调用实际命令）"""
    import re
    devices = []
    pattern = re.compile(r"Card\s+(\d+)\s+\[([^\]]+)\]")
    for line in output.splitlines():
        m = pattern.search(line)
        if m:
            devices.append({"id": m.group(1), "chip": m.group(2)})
    return devices


def test_ascend_npu_smi_query():
    """Test npu-smi -i 0 -q parsing"""
    print("\n[Ascend] Testing npu-smi query parsing...")
    
    passed = 0
    failed = 0
    
    for mock in ALL_ASCEND_MOCKS:
        model = mock["device_model"]
        query_output = mock["npu_smi_query"]
        expected = mock["expected"]
        
        info = _parse_npu_smi_query_from_output(query_output)
        
        # 检查温度
        temp_ok = True
        if "temperature" in expected:
            actual_temp = info.get("temperature")
            # 从解析结果中提取温度
            for key, val in info.items():
                if "temperature" in key.lower():
                    try:
                        import re
                        actual_temp = int(re.search(r"\d+", str(val)).group())
                    except Exception:
                        pass
                    break
            temp_ok = actual_temp == expected["temperature"]
        
        # 检查利用率
        util_ok = True
        if "utilization" in expected:
            actual_util = None
            for key, val in info.items():
                if "util" in key.lower():
                    try:
                        import re
                        actual_util = int(re.search(r"\d+", str(val)).group())
                    except Exception:
                        pass
                    break
            util_ok = actual_util == expected["utilization"]
        
        if temp_ok and util_ok:
            print(f"  [OK] {model}")
            passed += 1
        else:
            print(f"  [FAIL] {model}: temp={temp_ok}, util={util_ok}")
            failed += 1
    
    print(f"\n[Ascend] npu-smi query: {passed}/{len(ALL_ASCEND_MOCKS)} passed")
    return failed == 0


def _parse_npu_smi_query_from_output(output: str) -> dict:
    """从给定输出解析设备详情（不调用实际命令）"""
    info = {}
    for line in output.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        parts = line.rsplit(":", 1)
        if len(parts) == 2:
            key = parts[0].strip().strip("*|")
            val = parts[1].strip()
            info[key] = val
    return info


def test_jetson_tegrastats():
    """Test tegrastats parsing"""
    print("\n[Jetson] Testing tegrastats parsing...")
    
    passed = 0
    failed = 0
    
    for mock in ALL_JETSON_MOCKS:
        model = mock["device_model"]
        tegrastats_output = mock["tegrastats"]
        expected = mock["expected"]
        
        result = _parse_tegrastats(tegrastats_output)
        
        # 检查 RAM 总量
        ram_ok = True
        if "ram_total_mb" in expected:
            actual = result.get("ram_total_mb", 0)
            expected_ram = expected["ram_total_mb"]
            # 允许 ±10% 误差（不同版本输出格式略有差异）
            ram_ok = abs(actual - expected_ram) / expected_ram < 0.1 if expected_ram > 0 else False
        
        # 检查 GPU 利用率
        gpu_ok = True
        if "gpu_util_pct" in expected:
            actual = result.get("gpu_util_pct", -1)
            expected_gpu = expected["gpu_util_pct"]
            gpu_ok = actual == expected_gpu
        
        if ram_ok and gpu_ok:
            print(f"  [OK] {model}: RAM={result.get('ram_total_mb', 'N/A')}MB, GPU={result.get('gpu_util_pct', 'N/A')}%")
            passed += 1
        else:
            print(f"  [FAIL] {model}: RAM={ram_ok}, GPU={gpu_ok}")
            print(f"       parsed: {result}")
            failed += 1
    
    print(f"\n[Jetson] tegrastats: {passed}/{len(ALL_JETSON_MOCKS)} passed")
    return failed == 0


def test_all():
    """Run all tests"""
    print("=" * 60)
    print("hw-jet v6.0 Parser Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("Ascend npu-smi list", test_ascend_npu_smi_list()))
    results.append(("Ascend npu-smi query", test_ascend_npu_smi_query()))
    results.append(("Jetson tegrastats", test_jetson_tegrastats()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    
    return all_passed


if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
