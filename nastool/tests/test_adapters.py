# -*- coding: utf-8 -*-
"""
nastool adapters 单元测试 - 测试适配器核心功能

覆盖：
- BaseAdapter 基础功能
- MockAdapter 行为
- 错误处理
- 评分计算
- 报告生成
"""

import pytest
from adapters.base import BaseAdapter, AdapterResult, AdapterError, ErrorCode
from adapters.mock_adapter import MockAdapter
from adapters.reporter import Reporter
from adapters.benchmark import run_heuristic_benchmark


class TestAdapterResult:
    """AdapterResult 测试"""

    def test_default_values(self):
        """测试默认值"""
        result = AdapterResult()
        assert result.device_type == ""
        assert result.device_family == ""
        assert result.device_model == ""
        assert result.score == 0
        assert result.tools == {}
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self):
        """测试添加错误"""
        result = AdapterResult()
        result.add_error(ErrorCode.DEVICE_UNKNOWN, "测试错误", "详细信息")

        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.DEVICE_UNKNOWN
        assert result.errors[0].message == "测试错误"
        assert result.errors[0].details == "详细信息"

    def test_add_warning(self):
        """测试添加警告"""
        result = AdapterResult()
        result.add_warning("测试警告")

        assert len(result.warnings) == 1
        assert result.warnings[0] == "测试警告"

    def test_has_critical_errors(self):
        """测试关键错误检测"""
        result = AdapterResult()

        # 无错误
        assert result.has_critical_errors() is False

        # 添加非关键错误
        result.add_error(ErrorCode.TOOL_NOT_FOUND, "工具未找到")
        assert result.has_critical_errors() is False

        # 添加关键错误
        result.add_error(ErrorCode.NPU_NOT_DETECTED, "NPU 未检测到")
        assert result.has_critical_errors() is True

    def test_to_dict(self):
        """测试序列化"""
        result = AdapterResult(
            device_type="ascend",
            device_family="Atlas 200系",
            device_model="Atlas 200I A2",
            score=85,
        )
        data = result.to_dict()

        assert data["device_type"] == "ascend"
        assert data["device_family"] == "Atlas 200系"
        assert data["device_model"] == "Atlas 200I A2"
        assert data["score"] == 85


class TestAdapterError:
    """AdapterError 测试"""

    def test_error_creation(self):
        """测试错误创建"""
        error = AdapterError(
            code=ErrorCode.DEVICE_NOT_FOUND,
            message="设备未找到",
            details="无法检测到 NPU 设备",
        )

        assert error.code == ErrorCode.DEVICE_NOT_FOUND
        assert error.message == "设备未找到"
        assert error.details == "无法检测到 NPU 设备"
        assert error.timestamp is not None

    def test_error_to_dict(self):
        """测试错误序列化"""
        error = AdapterError(
            code=ErrorCode.NPU_TEMPERATURE_HIGH,
            message="NPU 温度过高",
        )
        data = error.to_dict()

        assert data["code"] == 1202
        assert data["name"] == "NPU_TEMPERATURE_HIGH"
        assert data["message"] == "NPU 温度过高"


class TestMockAdapter:
    """MockAdapter 测试"""

    def test_identify(self):
        """测试设备识别"""
        mock_data = {
            "device_family": "Atlas 200系",
            "device_model": "Atlas 200I A2",
        }
        adapter = MockAdapter(mock_data)
        family = adapter.identify()

        assert family == "Atlas 200系"
        assert adapter.result.device_model == "Atlas 200I A2"

    def test_check_tools(self):
        """测试工具检测"""
        mock_data = {
            "device_family": "Orin AGX",
            "tools": {"cuda": True, "tensorrt": True, "onnx_runtime": False},
        }
        adapter = MockAdapter(mock_data)
        tools = adapter.check_tools()

        assert tools["cuda"] is True
        assert tools["tensorrt"] is True
        assert tools["onnx_runtime"] is False

    def test_calc_score(self):
        """测试评分计算"""
        mock_data = {
            "device_family": "Atlas 300系",
            "expected": {
                "utilization": 50,
                "temperature": 60,
                "memory_used_mb": 4096,
                "memory_total_mb": 16384,
            },
        }
        adapter = MockAdapter(mock_data)
        adapter.identify()
        adapter.detect_npu()
        adapter.calc_score()

        assert adapter.result.score > 0
        assert "npu_util" in adapter.result.score_breakdown
        assert "npu_temp" in adapter.result.score_breakdown

    def test_run_benchmark(self):
        """测试基准测试"""
        mock_data = {"device_family": "Orin AGX"}
        adapter = MockAdapter(mock_data)
        adapter.run_benchmark()

        assert adapter.result.benchmark is not None
        assert "latency_ms" in adapter.result.benchmark
        assert "throughput_fps" in adapter.result.benchmark

    def test_full_run(self):
        """测试完整检测流程"""
        mock_data = {
            "device_family": "Orin AGX",
            "device_model": "NVIDIA Jetson AGX Orin 64GB",
            "expected": {
                "device_family": "Orin AGX",
                "device_model": "NVIDIA Jetson AGX Orin 64GB",
                "utilization": 35,
                "temperature": 58,
                "memory_used_mb": 2048,
                "memory_total_mb": 63488,
                "gpu_util": 42,
                "gpu_temp": 52,
            },
            "tools": {"cuda": True, "tensorrt": True},
        }
        adapter = MockAdapter(mock_data)
        result = adapter.run()

        assert result.device_family == "Orin AGX"
        assert result.device_model == "NVIDIA Jetson AGX Orin 64GB"
        assert result.score > 0
        assert len(result.errors) == 0
        assert result.elapsed_seconds >= 0


class TestReporter:
    """Reporter 测试"""

    def test_generate_terminal(self):
        """测试终端报告生成"""
        mock_data = {
            "device_family": "Atlas 200系",
            "device_model": "Atlas 200I A2",
            "expected": {"utilization": 45, "temperature": 62},
        }
        adapter = MockAdapter(mock_data)
        result = adapter.run()

        reporter = Reporter(result)
        terminal = reporter.generate_terminal()

        assert "hw-jet v6.0" in terminal
        assert "Atlas 200I A2" in terminal

    def test_generate_json(self):
        """测试 JSON 报告生成"""
        mock_data = {
            "device_family": "Orin AGX",
            "device_model": "Orin AGX 64GB",
        }
        adapter = MockAdapter(mock_data)
        result = adapter.run()

        reporter = Reporter(result)
        json_report = reporter.generate_json()

        assert json_report["device_family"] == "Orin AGX"
        assert json_report["device_model"] == "Orin AGX 64GB"
        assert "score" in json_report
        assert "grade" in json_report

    def test_generate_html(self):
        """测试 HTML 报告生成"""
        mock_data = {
            "device_family": "Atlas 300系",
            "device_model": "Atlas 300I Pro",
        }
        adapter = MockAdapter(mock_data)
        result = adapter.run()

        reporter = Reporter(result)
        html = reporter.generate_html()

        assert "<!DOCTYPE html>" in html
        assert "Atlas 300I Pro" in html
        assert "score-circle" in html

    def test_generate_markdown(self):
        """测试 Markdown 报告生成"""
        mock_data = {
            "device_family": "Orin NX",
            "device_model": "Jetson Orin NX 16GB",
        }
        adapter = MockAdapter(mock_data)
        result = adapter.run()

        reporter = Reporter(result)
        md = reporter.generate_markdown()

        assert "# hw-jet v6.0" in md
        assert "Jetson Orin NX 16GB" in md

    def test_grade_calculation(self):
        """测试等级计算"""
        reporter = Reporter(AdapterResult())

        assert reporter._get_grade(95) == "A"
        assert reporter._get_grade(85) == "B"
        assert reporter._get_grade(75) == "C"
        assert reporter._get_grade(65) == "D"
        assert reporter._get_grade(55) == "F"


class TestBenchmark:
    """基准测试模块测试"""

    def test_heuristic_benchmark(self):
        """测试启发式基准"""
        result = run_heuristic_benchmark()

        assert result["status"] == "success"
        assert result["latency_ms"] > 0
        assert result["throughput_fps"] > 0
        assert result["framework"] == "heuristic"

    def test_heuristic_benchmark_with_cpu_info(self):
        """测试启发式基准包含 CPU 信息"""
        result = run_heuristic_benchmark()

        assert "cpu_count" in result
        assert result["cpu_count"] > 0


class TestErrorCode:
    """错误码测试"""

    def test_error_code_values(self):
        """测试错误码值范围"""
        # 设备识别错误
        assert 1000 <= ErrorCode.DEVICE_NOT_FOUND.value <= 1099
        assert 1000 <= ErrorCode.DEVICE_UNKNOWN.value <= 1099

        # 工具链错误
        assert 1100 <= ErrorCode.TOOL_NOT_FOUND.value <= 1199

        # NPU 错误
        assert 1200 <= ErrorCode.NPU_NOT_DETECTED.value <= 1299
        assert 1200 <= ErrorCode.NPU_TEMPERATURE_HIGH.value <= 1299

        # 系统错误
        assert 1300 <= ErrorCode.SYSTEM_MEMORY_LOW.value <= 1399

        # 通用错误
        assert 1900 <= ErrorCode.UNKNOWN_ERROR.value <= 1999

    def test_all_error_codes_unique(self):
        """测试所有错误码唯一"""
        values = [e.value for e in ErrorCode]
        assert len(values) == len(set(values))


# ------------------------------------------------------------------ #
# 运行测试
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
