"""
Universal Test Runner for nastool

Dynamic test discovery and execution framework that:
- Discovers tests without relying on module names
- Supports multiple test patterns (class-based, function-based)
- Provides flexible test filtering
- Generates structured test reports
"""

import inspect
import importlib
import pkgutil
import traceback
from typing import List, Dict, Any, Callable, Type
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Result of a single test execution"""
    test_id: str
    test_name: str
    status: TestStatus
    message: str
    duration: float = 0.0
    traceback: str = ""


@dataclass
class TestSuiteResult:
    """Result of a test suite execution"""
    suite_name: str
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    results: List[TestResult]


class TestRunner:
    """
    Universal test runner with dynamic discovery.
    
    Features:
    - Auto-discovers test functions/classes in specified modules
    - Supports pytest-style test discovery
    - Runs tests in isolation
    - Generates detailed reports
    """
    
    def __init__(self):
        self.discovered_tests = []
        self._registry = {}
    
    def discover(self, module_path: str, pattern: str = "test_*.py") -> List[str]:
        """
        Discover tests dynamically without relying on module names.
        
        Args:
            module_path: Path to search for tests
            pattern: File pattern to match (default: test_*.py)
        
        Returns:
            List of discovered test identifiers
        """
        discovered = []
        
        # Convert path to module if needed
        if isinstance(module_path, str) and module_path.endswith(".py"):
            module_path = Path(module_path).parent
        
        if isinstance(module_path, Path):
            # Search directory for test files
            for test_file in module_path.rglob(pattern):
                discovered.extend(self._discover_in_file(test_file))
        elif isinstance(module_path, str):
            # Import as module
            try:
                module = importlib.import_module(module_path)
                discovered.extend(self._discover_in_module(module))
            except ImportError:
                # Try as path
                path = Path(module_path)
                if path.exists():
                    discovered.extend(self.discover(path, pattern))
        
        self.discovered_tests = discovered
        return discovered
    
    def _discover_in_file(self, file_path: Path) -> List[str]:
        """Discover tests in a single file"""
        tests = []
        
        # Get module name from path
        module_name = ".".join(file_path.parts[:-1]) + "." + file_path.stem
        module_name = module_name.replace("/", ".").replace("\\", ".")
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            tests.extend(self._discover_in_module(module))
        except Exception:
            pass
        
        return tests
    
    def _discover_in_module(self, module) -> List[str]:
        """Discover tests in an imported module"""
        tests = []
        
        for name, obj in inspect.getmembers(module):
            # Test classes (Test* pattern)
            if inspect.isclass(obj) and name.startswith("Test"):
                for method_name, method in inspect.getmembers(obj):
                    if inspect.isfunction(method) and method_name.startswith("test_"):
                        tests.append(f"{module.__name__}.{name}.{method_name}")
            
            # Test functions (test_* pattern)
            elif inspect.isfunction(obj) and name.startswith("test_"):
                tests.append(f"{module.__name__}.{name}")
        
        return tests
    
    def run(self, test_ids: List[str] = None, filter_pattern: str = None) -> TestSuiteResult:
        """
        Run tests with optional filtering.
        
        Args:
            test_ids: List of test identifiers to run (if None, run all discovered)
            filter_pattern: Optional regex pattern to filter test names
        
        Returns:
            TestSuiteResult with aggregated results
        """
        import time
        
        tests_to_run = test_ids or self.discovered_tests
        
        if filter_pattern:
            import re
            pattern = re.compile(filter_pattern)
            tests_to_run = [t for t in tests_to_run if pattern.search(t)]
        
        results = []
        start_time = time.time()
        
        for test_id in tests_to_run:
            result = self._run_test(test_id)
            results.append(result)
        
        duration = time.time() - start_time
        
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        return TestSuiteResult(
            suite_name="Test Suite",
            total=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            results=results
        )
    
    def _run_test(self, test_id: str) -> TestResult:
        """Run a single test by its identifier"""
        import time
        
        start_time = time.time()
        
        try:
            # Parse test_id: module.class.method or module.function
            parts = test_id.split(".")
            
            # Import module
            module_name = ".".join(parts[:-1])
            obj_name = parts[-1]
            
            # Handle nested classes
            module = importlib.import_module(module_name)
            obj = getattr(module, obj_name, None)
            
            if obj is None:
                # Try class.method pattern
                class_name = parts[-2]
                method_name = parts[-1]
                module_name = ".".join(parts[:-2])
                module = importlib.import_module(module_name)
                cls = getattr(module, class_name)
                obj = getattr(cls(), method_name)
            
            if obj is None:
                return TestResult(
                    test_id=test_id,
                    test_name=test_id,
                    status=TestStatus.ERROR,
                    message=f"Test not found: {test_id}"
                )
            
            # Execute test
            obj()
            
            duration = time.time() - start_time
            
            return TestResult(
                test_id=test_id,
                test_name=test_id,
                status=TestStatus.PASSED,
                message="Test passed",
                duration=duration
            )
        
        except AssertionError as e:
            duration = time.time() - start_time
            return TestResult(
                test_id=test_id,
                test_name=test_id,
                status=TestStatus.FAILED,
                message=str(e),
                duration=duration,
                traceback=traceback.format_exc()
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_id=test_id,
                test_name=test_id,
                status=TestStatus.ERROR,
                message=str(e),
                duration=duration,
                traceback=traceback.format_exc()
            )
    
    def register_test(self, test_id: str, test_func: Callable):
        """Register a test function manually"""
        self._registry[test_id] = test_func
    
    def print_report(self, result: TestSuiteResult):
        """Print human-readable test report"""
        print(f"\n{'='*60}")
        print(f"Test Suite Report: {result.suite_name}")
        print(f"{'='*60}")
        print(f"\nTotal: {result.total} | Passed: {result.passed} | Failed: {result.failed}")
        print(f"Skipped: {result.skipped} | Errors: {result.errors}")
        print(f"Duration: {result.duration:.2f}s")
        
        if result.failed > 0 or result.errors > 0:
            print("\nFailed Tests:")
            print("-" * 60)
            for r in result.results:
                if r.status in (TestStatus.FAILED, TestStatus.ERROR):
                    print(f"\n{r.test_id}")
                    print(f"  Status: {r.status.value}")
                    print(f"  Message: {r.message}")
                    if r.traceback:
                        print(f"  Traceback:\n{r.traceback}")
        
        print(f"\n{'='*60}")


class RegistryBasedTestRunner(TestRunner):
    """
    Test runner that uses the check registry for dynamic test discovery.
    
    This runner integrates with the existing check registry to:
    - Discover tests based on registered checks
    - Run checks in test mode
    - Validate check behavior
    """
    
    def __init__(self):
        super().__init__()
        self._check_registry = None
    
    def set_registry(self, registry):
        """Set the check registry for test discovery"""
        self._check_registry = registry
    
    def discover_from_registry(self) -> List[str]:
        """Discover tests from the check registry"""
        if not self._check_registry:
            raise RuntimeError("Check registry not set")
        
        tests = []
        
        # Discover all registered checks as potential tests
        for check_id, check_info in self._check_registry.list_checks().items():
            tests.append(f"check.{check_id}")
        
        self.discovered_tests = tests
        return tests
    
    def _run_test(self, test_id: str) -> TestResult:
        """Run a test that corresponds to a registered check"""
        import time
        
        start_time = time.time()
        
        if test_id.startswith("check."):
            check_id = test_id[6:]  # Remove "check." prefix
            
            try:
                if self._check_registry:
                    # Run check in test mode
                    check_cls = self._check_registry.get_check(check_id)
                    if check_cls:
                        check = check_cls()
                        result = check.run(mock=True)
                        
                        duration = time.time() - start_time
                        
                        if result.passed:
                            return TestResult(
                                test_id=test_id,
                                test_name=check_id,
                                status=TestStatus.PASSED,
                                message=f"Check passed: {result.message}",
                                duration=duration
                            )
                        else:
                            return TestResult(
                                test_id=test_id,
                                test_name=check_id,
                                status=TestStatus.FAILED,
                                message=f"Check failed: {result.message}",
                                duration=duration
                            )
                    else:
                        return TestResult(
                            test_id=test_id,
                            test_name=check_id,
                            status=TestStatus.ERROR,
                            message=f"Check not found in registry: {check_id}",
                            duration=time.time() - start_time
                        )
                else:
                    return super()._run_test(test_id)
            
            except Exception as e:
                duration = time.time() - start_time
                return TestResult(
                    test_id=test_id,
                    test_name=check_id,
                    status=TestStatus.ERROR,
                    message=str(e),
                    duration=duration,
                    traceback=traceback.format_exc()
                )
        
        return super()._run_test(test_id)


# Convenience functions
def run_all_tests(module_path: str = None) -> TestSuiteResult:
    """Run all tests in the specified module path"""
    runner = TestRunner()
    if module_path:
        runner.discover(module_path)
    return runner.run()


def run_tests_by_pattern(pattern: str, module_path: str = None) -> TestSuiteResult:
    """Run tests matching a specific pattern"""
    runner = TestRunner()
    if module_path:
        runner.discover(module_path)
    return runner.run(filter_pattern=pattern)


def run_registry_tests() -> TestSuiteResult:
    """Run all tests from the check registry"""
    from nastool_core.checks import get_registry
    
    runner = RegistryBasedTestRunner()
    runner.set_registry(get_registry())
    runner.discover_from_registry()
    return runner.run()


if __name__ == "__main__":
    # Example usage
    runner = TestRunner()
    
    # Discover tests in nastool-core
    print("Discovering tests...")
    tests = runner.discover("nastool-core/tests")
    print(f"Found {len(tests)} tests")
    
    # Run tests
    print("\nRunning tests...")
    result = runner.run()
    runner.print_report(result)