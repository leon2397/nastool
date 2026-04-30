# -*- coding: utf-8 -*-
"""PDF Reporter 功能测试"""
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_pdf_reporter_import():
    """测试PDFReporter模块导入"""
    from nastool_reporters.pdf_reporter import PDFReporter, generate_pdf_report, HAS_REPORTLAB

    print(f"[INFO] HAS_REPORTLAB = {HAS_REPORTLAB}")
    assert HAS_REPORTLAB, "reportlab 未安装"
    assert PDFReporter is not None
    print("[PASS] PDFReporter 模块导入成功")


def test_pdf_reporter_instantiate():
    """测试PDFReporter实例化"""
    from nastool_reporters.pdf_reporter import PDFReporter

    reporter = PDFReporter(
        title="测试报告",
        author="测试作者"
    )
    assert reporter is not None
    assert reporter.title == "测试报告"
    assert reporter.author == "测试作者"
    print("[PASS] PDFReporter 实例化成功")


def create_mock_health_report():
    """创建模拟的HealthReport对象"""
    from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
    from nastool_core.utils.health_scorer import HealthReport, CategoryScore, HealthScorer

    # 创建模拟检查结果
    results = [
        CheckResult(
            check_id="test_passed",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.PASSED,
            passed=True,
            title="通过测试",
            current="OK",
            expected="OK",
            message="测试通过"
        ),
        CheckResult(
            check_id="test_warning",
            category=CheckCategory.STORAGE,
            severity=CheckSeverity.WARNING,
            passed=False,
            title="警告测试",
            current="Warning",
            expected="OK",
            message="这是一个警告"
        ),
        CheckResult(
            check_id="test_critical",
            category=CheckCategory.NETWORK,
            severity=CheckSeverity.CRITICAL,
            passed=False,
            title="严重问题",
            current="Error",
            expected="OK",
            message="这是一个严重问题"
        ),
    ]

    # 使用HealthScorer计算报告
    scorer = HealthScorer()
    scorer.add_results(results)
    report = scorer.calculate(previous_score=85)

    return report


def test_pdf_reporter_generate():
    """测试PDF报告生成"""
    from nastool_reporters.pdf_reporter import PDFReporter

    # 创建模拟健康报告
    report = create_mock_health_report()

    # 生成PDF
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_report.pdf"

        reporter = PDFReporter(title="测试报告")
        try:
            success = reporter.generate(report, str(output_path))
            print(f"[DEBUG] generate() returned: {success}")
            if not success:
                print(f"[DEBUG] PDF file exists: {output_path.exists()}")
                if output_path.exists():
                    print(f"[DEBUG] PDF file size: {output_path.stat().st_size}")
        except Exception as gen_err:
            print(f"[ERROR] generate() raised: {gen_err}")
            import traceback
            traceback.print_exc()
            success = False

        assert success, "PDF生成失败"
        assert output_path.exists(), "PDF文件不存在"
        assert output_path.stat().st_size > 0, "PDF文件为空"

        print(f"[PASS] PDF生成成功: {output_path}")
        print(f"       文件大小: {output_path.stat().st_size} bytes")


def test_pdf_reporter_different_scenarios():
    """测试不同场景的PDF生成"""
    from nastool_reporters.pdf_reporter import PDFReporter
    from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
    from nastool_core.utils.health_scorer import HealthScorer

    scenarios = [
        {
            "name": "全部通过",
            "results": [
                CheckResult(
                    check_id="all_pass",
                    category=CheckCategory.SYSTEM,
                    severity=CheckSeverity.PASSED,
                    passed=True,
                    title="全部通过",
                    current="OK",
                    expected="OK",
                    message="所有检查通过"
                ),
            ]
        },
        {
            "name": "有警告",
            "results": [
                CheckResult(
                    check_id="warning_test",
                    category=CheckCategory.STORAGE,
                    severity=CheckSeverity.WARNING,
                    passed=False,
                    title="警告测试",
                    current="High",
                    expected="Normal",
                    message="存储使用率较高"
                ),
            ]
        },
        {
            "name": "有严重问题",
            "results": [
                CheckResult(
                    check_id="critical_test",
                    category=CheckCategory.NETWORK,
                    severity=CheckSeverity.CRITICAL,
                    passed=False,
                    title="网络不可达",
                    current="Unreachable",
                    expected="Reachable",
                    message="网络连接失败"
                ),
            ]
        },
        {
            "name": "混合场景",
            "results": [
                CheckResult(
                    check_id="pass_1",
                    category=CheckCategory.SYSTEM,
                    severity=CheckSeverity.PASSED,
                    passed=True,
                    title="系统正常",
                    current="OK",
                    expected="OK",
                    message="系统运行正常"
                ),
                CheckResult(
                    check_id="warning_1",
                    category=CheckCategory.STORAGE,
                    severity=CheckSeverity.WARNING,
                    passed=False,
                    title="存储警告",
                    current="85%",
                    expected="<70%",
                    message="存储使用率超过70%"
                ),
                CheckResult(
                    check_id="critical_1",
                    category=CheckCategory.SECURITY,
                    severity=CheckSeverity.CRITICAL,
                    passed=False,
                    title="安全风险",
                    current="Vulnerable",
                    expected="Secure",
                    message="发现安全漏洞"
                ),
            ]
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        for scenario in scenarios:
            print(f"\n[TEST] 测试场景: {scenario['name']}")

            # 计算报告
            scorer = HealthScorer()
            scorer.add_results(scenario["results"])
            report = scorer.calculate(previous_score=80)

            # 生成PDF
            output_path = Path(tmpdir) / f"report_{scenario['name']}.pdf"
            reporter = PDFReporter(title=f"{scenario['name']}测试报告")
            success = reporter.generate(report, str(output_path))

            if success and output_path.exists():
                print(f"  [PASS] {scenario['name']}: {output_path.stat().st_size} bytes")
            else:
                print(f"  [FAIL] {scenario['name']}: 生成失败")


def test_pdf_reporter_edge_cases():
    """测试PDFReporter边界情况"""
    from nastool_reporters.pdf_reporter import PDFReporter
    from nastool_core.utils.health_scorer import HealthReport, HealthScorer

    # 空报告
    print("\n[TEST] 测试边界情况: 空报告")
    scorer = HealthScorer()
    empty_report = scorer.calculate()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "empty_report.pdf"
        reporter = PDFReporter()

        success = reporter.generate(empty_report, str(output_path))
        if success:
            print(f"  [PASS] 空报告PDF生成成功: {output_path.stat().st_size} bytes")
        else:
            print(f"  [FAIL] 空报告PDF生成失败")

    # 无logo路径
    print("\n[TEST] 测试边界情况: 无效logo路径")
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "no_logo_report.pdf"
        reporter = PDFReporter(logo_path="/nonexistent/logo.png")

        success = reporter.generate(empty_report, str(output_path))
        if success:
            print(f"  [PASS] 无效logo路径处理正确: {output_path.stat().st_size} bytes")
        else:
            print(f"  [FAIL] 无效logo路径处理失败")


def test_generate_pdf_report_function():
    """测试便捷函数generate_pdf_report"""
    from nastool_reporters.pdf_reporter import generate_pdf_report
    from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
    from nastool_core.utils.health_scorer import HealthScorer

    results = [
        CheckResult(
            check_id="quick_test",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.PASSED,
            passed=True,
            title="快速测试",
            current="OK",
            expected="OK",
            message="快速测试通过"
        ),
    ]

    scorer = HealthScorer()
    scorer.add_results(results)
    report = scorer.calculate()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "quick_report.pdf"
        success = generate_pdf_report(report, str(output_path))

        if success:
            print(f"[PASS] 便捷函数测试成功: {output_path.stat().st_size} bytes")
        else:
            print(f"[FAIL] 便捷函数测试失败")


if __name__ == "__main__":
    tests = [
        test_pdf_reporter_import,
        test_pdf_reporter_instantiate,
        test_pdf_reporter_generate,
        test_pdf_reporter_different_scenarios,
        test_pdf_reporter_edge_cases,
        test_generate_pdf_report_function,
    ]

    passed = 0
    failed = 0

    print("=" * 60)
    print("PDF Reporter 功能测试")
    print("=" * 60)

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)