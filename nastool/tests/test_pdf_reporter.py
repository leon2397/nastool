# -*- coding: utf-8 -*-
"""
test_pdf_reporter.py — Unit tests for PDFReporter

v7.0 新增测试
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reporters.pdf_reporter import PDFReporter, HAS_REPORTLAB


class TestPDFReporter(unittest.TestCase):
    """Test PDFReporter"""

    def test_init(self):
        """测试初始化"""
        reporter = PDFReporter(
            title="测试报告",
            logo_path=None,
        )
        
        self.assertEqual(reporter.title, "测试报告")
        self.assertIsNone(reporter.logo_path)

    def test_init_with_logo(self):
        """测试带 Logo 初始化"""
        reporter = PDFReporter(
            logo_path="assets/logo.png",
        )
        
        self.assertEqual(reporter.logo_path, "assets/logo.png")

    @unittest.skipUnless(HAS_REPORTLAB, "reportlab 未安装")
    def test_generate_without_data(self):
        """测试生成空报告"""
        from utils.health_scorer import HealthReport
        
        reporter = PDFReporter()
        report = HealthReport()
        
        # 临时文件
        output_path = "/tmp/test_report.pdf"
        result = reporter.generate(report, output_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
        
        # 清理
        if os.path.exists(output_path):
            os.remove(output_path)

    def test_reportlab_available(self):
        """测试 reportlab 是否可用"""
        # 这个测试只是确认 skipUnless 工作正常
        self.assertIsInstance(HAS_REPORTLAB, bool)


class TestGeneratePDFReport(unittest.TestCase):
    """Test 便捷函数"""

    def test_generate_pdf_report_function_exists(self):
        """测试便捷函数是否存在"""
        from reporters import pdf_reporter
        
        self.assertTrue(hasattr(pdf_reporter, 'generate_pdf_report'))


if __name__ == "__main__":
    unittest.main()
