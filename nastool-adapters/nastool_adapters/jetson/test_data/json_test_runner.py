"""
JSON Data-Driven Test Runner for Jetson Devices

This module provides a framework for running tests defined in JSON format.
It supports:
- Loading test cases from JSON files
- Multiple validation types
- Test scenarios
- Detailed reporting
"""

import json
import re
import os
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TestType(Enum):
    """测试类型枚举"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"


class ValidationType(Enum):
    """验证类型枚举"""
    REGEX_MATCH = "regex_match"
    VALUE_CHECK = "value_check"
    RANGE_CHECK = "range_check"
    ENUM_CHECK = "enum_check"
    VERSION_CHECK = "version_check"


class TestStatus(Enum):
    """测试状态枚举"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestDevice:
    """测试设备信息"""
    name: str
    model: str
    soc: str
    arch: str
    cuda_version: str
    jetpack_version: str
    expected_results: Dict[str, Any]


@dataclass
class TestCase:
    """测试用例定义"""
    id: str
    name: str
    description: str
    test_type: TestType
    data_source: str
    validation: Dict[str, Any]


@dataclass
class TestScenario:
    """测试场景定义"""
    id: str
    name: str
    description: str
    test_sequence: List[str]
    expected_status: str


@dataclass
class TestResult:
    """单个测试结果"""
    test_id: str
    test_name: str
    status: TestStatus
    message: str
    actual_value: Any = None
    expected_value: Any = None
    duration: float = 0.0


@dataclass
class ScenarioResult:
    """场景测试结果"""
    scenario_id: str
    scenario_name: str
    status: TestStatus
    results: List[TestResult]
    duration: float = 0.0


@dataclass
class TestSuiteResult:
    """测试套件结果"""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    results: List[TestResult] = field(default_factory=list)
    scenario_results: List[ScenarioResult] = field(default_factory=list)


class JSONTestRunner:
    """
    JSON 数据驱动测试运行器
    
    功能：
    - 从 JSON 文件加载测试用例
    - 支持多种验证类型
    - 执行测试场景
    - 生成详细报告
    """
    
    def __init__(self, test_data_path: Optional[str] = None):
        """
        初始化测试运行器
        
        Args:
            test_data_path: JSON 测试数据文件路径
        """
        self.test_data_path = test_data_path
        self.devices: List[TestDevice] = []
        self.test_cases: Dict[str, TestCase] = {}
        self.scenarios: Dict[str, TestScenario] = {}
        self._data_providers: Dict[str, Callable] = {}
        
        if test_data_path:
            self.load_test_data(test_data_path)
    
    def load_test_data(self, file_path: str) -> bool:
        """
        从 JSON 文件加载测试数据
        
        Args:
            file_path: JSON 文件路径
        
        Returns:
            bool: 是否加载成功
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 加载设备列表
            for device_data in data.get("devices", []):
                self.devices.append(TestDevice(
                    name=device_data["name"],
                    model=device_data["model"],
                    soc=device_data["soc"],
                    arch=device_data["arch"],
                    cuda_version=device_data["cuda_version"],
                    jetpack_version=device_data["jetpack_version"],
                    expected_results=device_data["expected_results"]
                ))
            
            # 加载测试用例
            for case_data in data.get("test_cases", []):
                self.test_cases[case_data["id"]] = TestCase(
                    id=case_data["id"],
                    name=case_data["name"],
                    description=case_data["description"],
                    test_type=TestType(case_data["test_type"]),
                    data_source=case_data["data_source"],
                    validation=case_data["validation"]
                )
            
            # 加载测试场景
            for scenario_data in data.get("test_scenarios", []):
                self.scenarios[scenario_data["id"]] = TestScenario(
                    id=scenario_data["id"],
                    name=scenario_data["name"],
                    description=scenario_data["description"],
                    test_sequence=scenario_data["test_sequence"],
                    expected_status=scenario_data["expected_status"]
                )
            
            print(f"Loaded {len(self.devices)} devices, {len(self.test_cases)} test cases, {len(self.scenarios)} scenarios")
            return True
        except Exception as e:
            print(f"Failed to load test data: {e}")
            return False
    
    def register_data_provider(self, source_name: str, provider: Callable):
        """
        注册数据提供者
        
        Args:
            source_name: 数据源名称
            provider: 数据提供函数
        """
        self._data_providers[source_name] = provider
    
    def _get_data(self, source_name: str) -> Any:
        """
        获取数据源数据
        
        Args:
            source_name: 数据源名称
        
        Returns:
            Any: 数据源返回的数据
        """
        if source_name in self._data_providers:
            try:
                return self._data_providers[source_name]()
            except Exception as e:
                print(f"Error getting data from {source_name}: {e}")
                return None
        return None
    
    def _validate(self, actual: Any, validation: Dict[str, Any]) -> bool:
        """
        执行验证
        
        Args:
            actual: 实际值
            validation: 验证配置
        
        Returns:
            bool: 是否通过验证
        """
        validation_type = validation.get("type")
        
        if validation_type == "regex_match":
            pattern = validation.get("pattern")
            return self._validate_regex(actual, pattern)
        
        elif validation_type == "value_check":
            expected = validation.get("expected")
            field_name = validation.get("field")
            return self._validate_value(actual, expected, field_name)
        
        elif validation_type == "range_check":
            min_val = validation.get("min")
            max_val = validation.get("max")
            field_name = validation.get("field")
            return self._validate_range(actual, min_val, max_val, field_name)
        
        elif validation_type == "enum_check":
            allowed = validation.get("allowed_values")
            return self._validate_enum(actual, allowed)
        
        elif validation_type == "version_check":
            min_version = validation.get("min_version")
            max_version = validation.get("max_version")
            return self._validate_version(actual, min_version, max_version)
        
        return False
    
    def _validate_regex(self, actual: Any, pattern: str) -> bool:
        """正则匹配验证"""
        if actual is None:
            return False
        try:
            return re.match(pattern, str(actual)) is not None
        except Exception:
            return False
    
    def _validate_value(self, actual: Any, expected: Any, field_name: str = None) -> bool:
        """值相等验证"""
        if field_name and isinstance(actual, dict):
            actual = actual.get(field_name)
        return actual == expected
    
    def _validate_range(self, actual: Any, min_val: float, max_val: float, field_name: str = None) -> bool:
        """范围验证"""
        if field_name and isinstance(actual, dict):
            actual = actual.get(field_name)
        
        try:
            actual_num = float(actual)
            return min_val <= actual_num <= max_val
        except (ValueError, TypeError):
            return False
    
    def _validate_enum(self, actual: Any, allowed_values: List) -> bool:
        """枚举值验证"""
        return actual in allowed_values
    
    def _validate_version(self, actual: str, min_version: str, max_version: str) -> bool:
        """版本号验证"""
        if actual is None:
            return False
        
        def parse_version(v: str) -> List[int]:
            parts = v.split(".")
            return [int(p) for p in parts if p.isdigit()]
        
        try:
            actual_parts = parse_version(actual)
            min_parts = parse_version(min_version) if min_version else []
            max_parts = parse_version(max_version) if max_version else []
            
            if min_parts and actual_parts < min_parts:
                return False
            if max_parts and actual_parts > max_parts:
                return False
            return True
        except Exception:
            return False
    
    def run_test(self, test_case: TestCase) -> TestResult:
        """
        执行单个测试用例
        
        Args:
            test_case: 测试用例
        
        Returns:
            TestResult: 测试结果
        """
        import time
        
        start_time = time.time()
        
        try:
            # 获取数据
            actual_data = self._get_data(test_case.data_source)
            
            # 提取实际值
            field_name = test_case.validation.get("field")
            actual_value = actual_data
            if field_name and isinstance(actual_data, dict):
                actual_value = actual_data.get(field_name)
            
            # 执行验证
            passed = self._validate(actual_data, test_case.validation)
            
            duration = time.time() - start_time
            
            if passed:
                return TestResult(
                    test_id=test_case.id,
                    test_name=test_case.name,
                    status=TestStatus.PASSED,
                    message=f"Test passed",
                    actual_value=actual_value,
                    duration=duration
                )
            else:
                expected_info = test_case.validation.get("expected", test_case.validation.get("pattern", "N/A"))
                return TestResult(
                    test_id=test_case.id,
                    test_name=test_case.name,
                    status=TestStatus.FAILED,
                    message=f"Validation failed",
                    actual_value=actual_value,
                    expected_value=expected_info,
                    duration=duration
                )
        
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_id=test_case.id,
                test_name=test_case.name,
                status=TestStatus.ERROR,
                message=f"Test error: {str(e)}",
                duration=duration
            )
    
    def run_scenario(self, scenario: TestScenario) -> ScenarioResult:
        """
        执行测试场景
        
        Args:
            scenario: 测试场景
        
        Returns:
            ScenarioResult: 场景测试结果
        """
        import time
        
        start_time = time.time()
        results: List[TestResult] = []
        
        for test_id in scenario.test_sequence:
            if test_id in self.test_cases:
                result = self.run_test(self.test_cases[test_id])
                results.append(result)
            else:
                results.append(TestResult(
                    test_id=test_id,
                    test_name=f"Unknown test: {test_id}",
                    status=TestStatus.SKIPPED,
                    message="Test case not found"
                ))
        
        duration = time.time() - start_time
        
        # 确定场景状态
        if all(r.status == TestStatus.PASSED for r in results):
            status = TestStatus.PASSED
        elif any(r.status == TestStatus.ERROR for r in results):
            status = TestStatus.ERROR
        else:
            status = TestStatus.FAILED
        
        return ScenarioResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            status=status,
            results=results,
            duration=duration
        )
    
    def run_all(self) -> TestSuiteResult:
        """
        运行所有测试用例和场景
        
        Returns:
            TestSuiteResult: 测试套件结果
        """
        import time
        
        start_time = time.time()
        results: List[TestResult] = []
        scenario_results: List[ScenarioResult] = []
        
        # 运行所有测试用例
        for test_case in self.test_cases.values():
            result = self.run_test(test_case)
            results.append(result)
        
        # 运行所有场景
        for scenario in self.scenarios.values():
            scenario_result = self.run_scenario(scenario)
            scenario_results.append(scenario_result)
        
        duration = time.time() - start_time
        
        # 统计结果
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        return TestSuiteResult(
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            results=results,
            scenario_results=scenario_results
        )
    
    def run_by_device(self, device_model: str) -> TestSuiteResult:
        """
        针对特定设备型号运行测试
        
        Args:
            device_model: 设备型号
        
        Returns:
            TestSuiteResult: 测试套件结果
        """
        device = next((d for d in self.devices if d.model == device_model), None)
        if not device:
            print(f"Device not found: {device_model}")
            return TestSuiteResult()
        
        print(f"Running tests for device: {device.name}")
        return self.run_all()
    
    def print_report(self, result: TestSuiteResult):
        """
        打印测试报告
        
        Args:
            result: 测试套件结果
        """
        print(f"\n{'='*70}")
        print(f"Jetson Test Suite Report")
        print(f"{'='*70}")
        print(f"\nTest Summary:")
        print(f"  Total:    {result.total_tests}")
        print(f"  Passed:   {result.passed}")
        print(f"  Failed:   {result.failed}")
        print(f"  Skipped:  {result.skipped}")
        print(f"  Errors:   {result.errors}")
        print(f"  Duration: {result.duration:.2f}s")
        
        if result.results:
            print(f"\n{'='*70}")
            print("Test Results:")
            print(f"{'='*70}")
            
            for r in result.results:
                status_icon = "✅" if r.status == TestStatus.PASSED else \
                             "❌" if r.status == TestStatus.FAILED else \
                             "⚠️" if r.status == TestStatus.SKIPPED else "🔴"
                print(f"\n{status_icon} {r.test_name} ({r.test_id})")
                print(f"   Status: {r.status.value}")
                print(f"   Message: {r.message}")
                if r.actual_value is not None:
                    print(f"   Actual: {r.actual_value}")
                if r.expected_value is not None:
                    print(f"   Expected: {r.expected_value}")
        
        if result.scenario_results:
            print(f"\n{'='*70}")
            print("Scenario Results:")
            print(f"{'='*70}")
            
            for scenario in result.scenario_results:
                status_icon = "✅" if scenario.status == TestStatus.PASSED else "❌"
                print(f"\n{status_icon} {scenario.scenario_name} ({scenario.scenario_id})")
                print(f"   Status: {scenario.status.value}")
                print(f"   Duration: {scenario.duration:.2f}s")
                
                for r in scenario.results:
                    sub_icon = "✅" if r.status == TestStatus.PASSED else "❌"
                    print(f"     {sub_icon} {r.test_name}")
        
        print(f"\n{'='*70}")
    
    def export_report(self, result: TestSuiteResult, output_path: str):
        """
        导出测试报告到文件
        
        Args:
            result: 测试套件结果
            output_path: 输出文件路径
        """
        report_data = {
            "summary": {
                "total_tests": result.total_tests,
                "passed": result.passed,
                "failed": result.failed,
                "skipped": result.skipped,
                "errors": result.errors,
                "duration": result.duration
            },
            "test_results": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "status": r.status.value,
                    "message": r.message,
                    "actual_value": r.actual_value,
                    "expected_value": r.expected_value,
                    "duration": r.duration
                } for r in result.results
            ],
            "scenario_results": [
                {
                    "scenario_id": s.scenario_id,
                    "scenario_name": s.scenario_name,
                    "status": s.status.value,
                    "duration": s.duration,
                    "test_results": [
                        {
                            "test_id": r.test_id,
                            "test_name": r.test_name,
                            "status": r.status.value
                        } for r in s.results
                    ]
                } for s in result.scenario_results
            ]
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"Report exported to: {output_path}")


# 示例用法
def main():
    # 创建测试运行器
    runner = JSONTestRunner()
    
    # 加载测试数据
    test_data_path = Path(__file__).parent / "jetson_test_cases.json"
    runner.load_test_data(str(test_data_path))
    
    # 注册模拟数据提供者
    def mock_jetson_info():
        return "AGX Orin"
    
    def mock_cuda_info():
        return {"available": True, "version": "11.4"}
    
    def mock_tensorrt_info():
        return {"available": True, "version": "8.4"}
    
    def mock_gpu_memory():
        return 32
    
    def mock_power_mode():
        return "MAXN"
    
    def mock_jetpack_version():
        return "5.0.2"
    
    def mock_thermal():
        return {"temperature": 45.5, "status": "normal"}
    
    def mock_fan():
        return {"controllable": True, "speed": 50}
    
    def mock_multiprocess_service():
        return {"status": "running", "pid": 1234}
    
    runner.register_data_provider("jetson_info", mock_jetson_info)
    runner.register_data_provider("cuda_info", mock_cuda_info)
    runner.register_data_provider("tensorrt_info", mock_tensorrt_info)
    runner.register_data_provider("gpu_memory", mock_gpu_memory)
    runner.register_data_provider("power_mode", mock_power_mode)
    runner.register_data_provider("jetpack_version", mock_jetpack_version)
    runner.register_data_provider("cuda_version", lambda: "11.4")
    runner.register_data_provider("thermal", mock_thermal)
    runner.register_data_provider("fan", mock_fan)
    runner.register_data_provider("multiprocess_service", mock_multiprocess_service)
    
    # 运行所有测试
    result = runner.run_all()
    
    # 打印报告
    runner.print_report(result)
    
    # 导出报告
    runner.export_report(result, "jetson_test_report.json")


if __name__ == "__main__":
    main()