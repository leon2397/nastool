# -*- coding: utf-8 -*-
"""
nastool adapters.hw_jet - hw-jet v6.0 入口封装

提供统一的 hw-jet 设备诊断入口，整合昇腾和 Jetson 适配器。
"""

from __future__ import annotations

import json
import sys
from typing import Optional

from nastool_adapters.detector import detect
from nastool_adapters.ascend.common import AscendAdapter
from nastool_adapters.jetson.common import JetsonAdapter
from nastool_adapters.mock_adapter import MockAdapter

# 日志
import logging
logger = logging.getLogger(__name__)


def run_hwjet_diagnosis(
    device: str = "auto",
    full: bool = False,
    benchmark: bool = False,
    output: Optional[str] = None,
    json_output: bool = False,
    mock: Optional[str] = None,
) -> int:
    """
    运行 hw-jet v6.0 诊断。

    Args:
        device: 设备类型 (auto/ascend/jetson)
        full: 完整诊断（含系统检测）
        benchmark: 运行推理基准
        output: 报告输出路径
        json_output: JSON 格式输出
        mock: Mock 设备类型 (atlas_200i_a2, orin_agx_64gb 等)

    Returns:
        退出码 (0=成功, 1=错误)
    """
    print("=" * 60)
    print("hw-jet v6.0 - Ascend + Jetson AI Edge Diagnostics")
    print("=" * 60)
    print()

    # 1. 设备识别
    print("[Step 1] Detecting device...")
    
    adapter = None
    adapter_cls = None
    
    # Mock 模式
    if mock:
        # 动态加载 mock 数据
        import importlib.util
        import os
        
        _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        _ascend_mock_path = os.path.join(_base_dir, "tests", "mock_adapters", "ascend", "mock_data.py")
        _jetson_mock_path = os.path.join(_base_dir, "tests", "mock_adapters", "jetson", "mock_data.py")
        
        def _load_module(name: str, path: str):
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        
        _ascend_mock = _load_module("ascend_mock", _ascend_mock_path)
        _jetson_mock = _load_module("jetson_mock", _jetson_mock_path)
        
        ALL_ASCEND_MOCKS = _ascend_mock.ALL_ASCEND_MOCKS
        ALL_JETSON_MOCKS = _jetson_mock.ALL_JETSON_MOCKS
        
        all_mocks = {m["device_model"].lower().replace(" ", "_"): m for m in ALL_ASCEND_MOCKS + ALL_JETSON_MOCKS}
        
        mock_key = mock.lower().replace("-", "_")
        if mock_key not in all_mocks:
            print(f"[ERROR] Unknown mock device: {mock}")
            print(f"       Available: {', '.join(all_mocks.keys())}")
            return 1
        
        mock_data = all_mocks[mock_key]
        device_family = mock_data["device_family"]
        
        # 使用 Mock 适配器
        adapter = MockAdapter(mock_data)
        print(f"[MOCK] Simulating: {mock_data['device_model']}")
    elif device == "auto":
        device_family, adapter_cls = detect()
    elif device == "ascend":
        device_family = "Atlas"
        adapter_cls = AscendAdapter
    elif device == "jetson":
        device_family = "Jetson"
        adapter_cls = JetsonAdapter
    else:
        print(f"[ERROR] Unknown device type: {device}")
        return 1

    if not adapter_cls and not mock:
        print("[INFO] No hw-jet device detected on this system.")
        print("       This tool is designed for Ascend/Jetson devices.")
        print()
        print("       For generic ARM diagnosis, use: python arm_diagnose.py")
        return 0

    # 2. 创建适配器
    if mock:
        # MockAdapter 已在前面创建
        pass
    else:
        adapter = adapter_cls()

    print(f"[OK] Detected: {device_family}")
    print()

    # 2. 创建适配器并运行检测
    print("[Step 2] Running diagnostics...")
    
    if not mock:
        adapter = adapter_cls()
    
    # 识别设备族
    family = adapter.identify()
    if not family:
        print("[ERROR] Failed to identify device family")
        return 1
    
    adapter.result.device_family = family
    print(f"[OK] Device family: {family}")

    # 检查工具链
    adapter.check_tools()
    tools = adapter.result.tools
    print(f"[OK] Tools: {', '.join(k for k, v in tools.items() if v) or 'None'}")

    # NPU/GPU 状态
    if hasattr(adapter, 'detect_npu'):
        adapter.detect_npu()
    elif hasattr(adapter, 'detect_gpu'):
        adapter.detect_gpu()
    
    # 系统状态
    if hasattr(adapter, 'detect_system'):
        adapter.detect_system()

    # 3. 健康评分
    print()
    print("[Step 3] Calculating health score...")
    adapter.calc_score()
    score = adapter.result.score
    breakdown = adapter.result.score_breakdown
    
    # 评分等级
    if score >= 90:
        grade = "A (Excellent)"
    elif score >= 80:
        grade = "B (Good)"
    elif score >= 70:
        grade = "C (Fair)"
    elif score >= 60:
        grade = "D (Poor)"
    else:
        grade = "F (Critical)"
    
    print(f"[OK] Health Score: {score}/100 ({grade})")
    print(f"     Breakdown: {json.dumps(breakdown, indent=6)}")

    # 4. 推理基准（可选）
    if benchmark:
        print()
        print("[Step 4] Running inference benchmark (MobileNetV2)...")
        adapter.run_benchmark()
        bench = adapter.result.benchmark
        if bench.get("latency_ms"):
            print(f"[OK] Latency: {bench['latency_ms']:.2f} ms")
            print(f"     Throughput: {bench.get('throughput_fps', 0):.1f} FPS")
        else:
            print(f"[WARN] Benchmark skipped: {bench.get('error', 'Unknown')}")

    # 5. 输出报告
    if output or json_output:
        print()
        print("[Step 5] Generating report...")
        
        report = adapter.result.to_dict()
        
        if output:
            # 写入文件
            with open(output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"[OK] Report saved to: {output}")
        
        if json_output:
            print()
            print(json.dumps(report, indent=2, ensure_ascii=False))

    print()
    print("=" * 60)
    print("hw-jet v6.0 diagnosis complete.")
    print("=" * 60)
    
    return 0


def generate_report(adapter, format: str = "terminal") -> str:
    """生成报告（使用 Reporter 类）"""
    from adapters.reporter import Reporter
    reporter = Reporter(adapter.result)
    
    if format == "terminal":
        return reporter.generate_terminal()
    elif format == "json":
        return json.dumps(reporter.generate_json(), indent=2, ensure_ascii=False)
    elif format == "html":
        return reporter.generate_html()
    elif format == "md":
        return reporter.generate_markdown()
    else:
        raise ValueError(f"Unsupported format: {format}")


def save_report(adapter, path: str, format: str = "json") -> None:
    """保存报告到文件"""
    from adapters.reporter import Reporter
    reporter = Reporter(adapter.result)
    reporter.save(path, format)


def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="hw-jet v6.0 - Ascend + Jetson AI Edge Diagnostics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--device", "-d",
        choices=["auto", "ascend", "jetson"],
        default="auto",
        help="Device type to diagnose (default: auto-detect)"
    )
    parser.add_argument(
        "--full", "-f",
        action="store_true",
        help="Run full diagnosis including system checks"
    )
    parser.add_argument(
        "--benchmark", "-b",
        action="store_true",
        help="Run inference benchmark (MobileNetV2)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Save report to file (format auto-detected from extension: .json/.html/.md)"
    )
    parser.add_argument(
        "--format",
        choices=["terminal", "json", "html", "md"],
        default="terminal",
        help="Report format (default: terminal)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report in JSON format to stdout"
    )
    parser.add_argument(
        "--mock", "-m",
        help="Mock device for testing (e.g., atlas_200i_a2, orin_agx_64gb)"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="hw-jet v6.0"
    )
    
    args = parser.parse_args()
    
    return run_hwjet_diagnosis(
        device=args.device,
        full=args.full,
        benchmark=args.benchmark,
        output=args.output,
        json_output=args.json,
        mock=args.mock,
    )


if __name__ == "__main__":
    sys.exit(main())
