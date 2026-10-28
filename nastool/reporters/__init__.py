"""
reporters/__init__.py — 报告输出器
支持：彩色终端 / JSON / HTML / PDF
"""
from .terminal import TerminalReporter
from .json_reporter import JSONReporter
from .html_reporter import HTMLReporter

__all__ = ["TerminalReporter", "JSONReporter", "HTMLReporter"]
