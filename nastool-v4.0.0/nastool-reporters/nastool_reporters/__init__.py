"""
nastool_reporters -- 报告输出模块
支持：终端 / JSON / HTML / 健康仪表盘 / 友好报告 / PDF报告
"""

from .terminal import TerminalReporter
from .json_reporter import JSONReporter
from .html_reporter import HTMLReporter
from .health_dashboard import HealthDashboard
from .friendly_reporter import FriendlyReporter
from .rk_reporter import RKReporter, generate_rk_report

# v7.0 新增 PDF 支持（可选，需要 reportlab）
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
    "RKReporter",
    "generate_rk_report",
]
if HAS_PDF:
    __all__.extend(["PDFReporter", "generate_pdf_report"])
