"""
reporters/__init__.py — 报告输出器
支持：彩色终端 / JSON / HTML / 健康仪表盘 / 普通人友好报告 / PDF报告
"""

from .terminal import TerminalReporter
from .json_reporter import JSONReporter
from .html_reporter import HTMLReporter
from .health_dashboard import HealthDashboard
from .friendly_reporter import FriendlyReporter

# v7.0 新增 PDF 报告（可选，需要 reportlab）
try:
    from .pdf_reporter import PDFReporter, generate_pdf_report
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

__all__ = [
    "TerminalReporter",
    "JSONReporter",
    "HTMLReporter",
    "HealthDashboard",
    "FriendlyReporter",
]
if HAS_PDF:
    __all__.extend(["PDFReporter", "generate_pdf_report"])
