"""
reporters/__init__.py — 报告输出器

三个报告器读取同一份 Report，只有呈现方式不同：
  TerminalReporter  终端（人看，先结论后细节）
  JSONReporter      JSON（机器读，格式向后兼容，上报与历史都用它）
  HTMLReporter      单文件 HTML（可发出去，零外部资源、可打印）
"""
from .html_reporter import HTMLReporter
from .json_reporter import JSONReporter
from .terminal import TerminalReporter, render_diff

__all__ = ["TerminalReporter", "JSONReporter", "HTMLReporter", "render_diff"]
