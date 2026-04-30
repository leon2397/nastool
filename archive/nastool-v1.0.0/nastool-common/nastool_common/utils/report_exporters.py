"""
Report Exporters - 报告导出格式增强

支持多种报告导出格式：
- PDF（可打印报告）
- CSV（表格数据）
- Markdown（文档格式）
- HTML（网页格式）
- JSON（原始数据）
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReportData:
    """报告数据结构"""

    device_id: str
    device_name: str
    timestamp: float
    health_score: int
    checks: List[Dict]
    issues: List[Dict]
    suggestions: List[str]
    summary: str

    # 性能数据
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0

    # AI 数据
    ai_score: float = 0.0
    ai_accelerator: str = ""

    def to_dict(self) -> Dict:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "timestamp": self.timestamp,
            "health_score": self.health_score,
            "checks": self.checks,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "summary": self.summary,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
            "ai_score": self.ai_score,
            "ai_accelerator": self.ai_accelerator,
        }


class ReportExporter:
    """报告导出器基类"""

    format_name: str = "base"
    file_extension: str = ".txt"

    def export(self, report: ReportData, output_path: str) -> bool:
        """
        导出报告

        Args:
            report: 报告数据
            output_path: 输出路径

        Returns:
            True 如果导出成功
        """
        raise NotImplementedError

    def _format_timestamp(self, timestamp: float) -> str:
        """格式化时间戳"""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        else:
            return f"{seconds / 3600:.1f}h"


class JSONExporter(ReportExporter):
    """JSON 格式导出器"""

    format_name = "json"
    file_extension = ".json"

    def export(self, report: ReportData, output_path: str) -> bool:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Exported JSON report: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            return False


class MarkdownExporter(ReportExporter):
    """Markdown 格式导出器"""

    format_name = "markdown"
    file_extension = ".md"

    def export(self, report: ReportData, output_path: str) -> bool:
        try:
            lines = [
                f"# NAS 诊断报告",
                "",
                f"**设备**: {report.device_name} ({report.device_id})",
                f"**时间**: {self._format_timestamp(report.timestamp)}",
                f"**健康分数**: {report.health_score}/100",
                "",
                "---",
                "",
                "## 摘要",
                "",
                report.summary,
                "",
                "## 系统状态",
                "",
                f"| 指标 | 值 |",
                f"|------|-----|",
                f"| CPU 使用率 | {report.cpu_usage:.1f}% |",
                f"| 内存使用率 | {report.memory_usage:.1f}% |",
                f"| 磁盘使用率 | {report.disk_usage:.1f}% |",
            ]

            if report.ai_accelerator:
                lines.extend(
                    [
                        f"| AI 加速器 | {report.ai_accelerator} |",
                        f"| AI 分数 | {report.ai_score:.1f} |",
                    ]
                )

            lines.extend(
                [
                    "",
                    "## 检查项",
                    "",
                ]
            )

            for check in report.checks:
                status = "[OK]" if check.get("passed") else "[X]"
                lines.append(
                    f"- {status} **{check.get('name', 'Unknown')}**: {check.get('message', '')}"
                )

            if report.issues:
                lines.extend(
                    [
                        "",
                        "## 问题列表",
                        "",
                    ]
                )

                for i, issue in enumerate(report.issues, 1):
                    lines.append(f"{i}. **{issue.get('title', 'Unknown')}**")
                    lines.append(f"   - 级别: {issue.get('level', 'info')}")
                    lines.append(f"   - 详情: {issue.get('description', '')}")
                    lines.append("")

            if report.suggestions:
                lines.extend(
                    [
                        "## 建议",
                        "",
                    ]
                )

                for suggestion in report.suggestions:
                    lines.append(f"- {suggestion}")

            lines.extend(
                [
                    "",
                    "---",
                    "",
                    f"*由 nastool v3.0.7 生成*",
                ]
            )

            content = "\n".join(lines)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Exported Markdown report: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export Markdown: {e}")
            return False


class CSVExporter(ReportExporter):
    """CSV 格式导出器"""

    format_name = "csv"
    file_extension = ".csv"

    def export(self, report: ReportData, output_path: str) -> bool:
        try:
            import csv

            with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)

                # 标题
                writer.writerow(["NAS 诊断报告"])
                writer.writerow([])

                # 基本信息
                writer.writerow(["设备ID", report.device_id])
                writer.writerow(["设备名称", report.device_name])
                writer.writerow(["诊断时间", self._format_timestamp(report.timestamp)])
                writer.writerow(["健康分数", report.health_score])
                writer.writerow([])

                # 系统状态
                writer.writerow(["系统状态"])
                writer.writerow(["指标", "值"])
                writer.writerow(["CPU使用率", f"{report.cpu_usage:.1f}%"])
                writer.writerow(["内存使用率", f"{report.memory_usage:.1f}%"])
                writer.writerow(["磁盘使用率", f"{report.disk_usage:.1f}%"])
                if report.ai_accelerator:
                    writer.writerow(["AI加速器", report.ai_accelerator])
                    writer.writerow(["AI分数", report.ai_score])
                writer.writerow([])

                # 检查项
                writer.writerow(["检查项"])
                writer.writerow(["名称", "状态", "消息"])
                for check in report.checks:
                    status = "通过" if check.get("passed") else "失败"
                    writer.writerow([check.get("name", ""), status, check.get("message", "")])
                writer.writerow([])

                # 问题
                if report.issues:
                    writer.writerow(["问题列表"])
                    writer.writerow(["标题", "级别", "描述"])
                    for issue in report.issues:
                        writer.writerow(
                            [
                                issue.get("title", ""),
                                issue.get("level", ""),
                                issue.get("description", ""),
                            ]
                        )
                    writer.writerow([])

                # 建议
                if report.suggestions:
                    writer.writerow(["建议"])
                    for suggestion in report.suggestions:
                        writer.writerow([suggestion])

            logger.info(f"Exported CSV report: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            return False


class HTMLExporter(ReportExporter):
    """HTML 格式导出器"""

    format_name = "html"
    file_extension = ".html"

    def export(self, report: ReportData, output_path: str) -> bool:
        try:
            # 健康分数颜色
            if report.health_score >= 90:
                score_color = "#28a745"
                score_class = "excellent"
            elif report.health_score >= 70:
                score_color = "#ffc107"
                score_class = "good"
            elif report.health_score >= 50:
                score_color = "#fd7e14"
                score_class = "warning"
            else:
                score_color = "#dc3545"
                score_class = "critical"

            html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NAS 诊断报告 - {report.device_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .header .meta {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .score-circle {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 20px auto;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .score-value {{
            font-size: 48px;
            font-weight: bold;
            color: {score_color};
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            margin-top: 0;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .metric {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric .value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }}
        .metric .label {{
            color: #666;
            font-size: 12px;
            margin-top: 5px;
        }}
        .check-item {{
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            align-items: center;
        }}
        .check-item.passed {{
            background: #d4edda;
        }}
        .check-item.failed {{
            background: #f8d7da;
        }}
        .check-icon {{
            margin-right: 10px;
            font-size: 20px;
        }}
        .issue-item {{
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #dc3545;
            background: #fff3cd;
            border-radius: 0 5px 5px 0;
        }}
        .suggestion-item {{
            padding: 10px;
            margin: 5px 0;
            background: #e7f3ff;
            border-radius: 5px;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🖥 NAS 诊断报告</h1>
        <div class="meta">
            <div>设备: {report.device_name} ({report.device_id})</div>
            <div>时间: {self._format_timestamp(report.timestamp)}</div>
        </div>
    </div>
    
    <div class="card">
        <div class="score-circle">
            <div class="score-value">{report.health_score}</div>
        </div>
        <p style="text-align: center; color: #666;">{report.summary}</p>
    </div>
    
    <div class="card">
        <h2>📊 系统状态</h2>
        <div class="metrics">
            <div class="metric">
                <div class="value">{report.cpu_usage:.1f}%</div>
                <div class="label">CPU 使用率</div>
            </div>
            <div class="metric">
                <div class="value">{report.memory_usage:.1f}%</div>
                <div class="label">内存使用率</div>
            </div>
            <div class="metric">
                <div class="value">{report.disk_usage:.1f}%</div>
                <div class="label">磁盘使用率</div>
            </div>
"""

            if report.ai_accelerator:
                html += f"""
            <div class="metric">
                <div class="value">{report.ai_score:.1f}</div>
                <div class="label">AI 分数 ({report.ai_accelerator})</div>
            </div>
"""

            html += """
        </div>
    </div>
    
    <div class="card">
        <h2>[OK] 检查项</h2>
"""

            for check in report.checks:
                passed = check.get("passed", False)
                icon = "[OK]" if passed else "[X]"
                css_class = "passed" if passed else "failed"
                html += f"""
        <div class="check-item {css_class}">
            <span class="check-icon">{icon}</span>
            <div>
                <strong>{check.get("name", "Unknown")}</strong>
                <div style="color: #666; font-size: 12px;">{check.get("message", "")}</div>
            </div>
        </div>
"""

            html += """
    </div>
"""

            if report.issues:
                html += """
    <div class="card">
        <h2>[!] 问题列表</h2>
"""
                for issue in report.issues:
                    html += f"""
        <div class="issue-item">
            <strong>{issue.get("title", "Unknown")}</strong>
            <div style="color: #666; font-size: 12px;">{issue.get("description", "")}</div>
        </div>
"""
                html += """
    </div>
"""

            if report.suggestions:
                html += """
    <div class="card">
        <h2>[!] 建议</h2>
"""
                for suggestion in report.suggestions:
                    html += f"""
        <div class="suggestion-item">{suggestion}</div>
"""
                html += """
    </div>
"""

            html += f"""
    <div class="footer">
        由 nastool v3.0.7 生成 | {self._format_timestamp(report.timestamp)}
    </div>
</body>
</html>
"""

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)

            logger.info(f"Exported HTML report: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export HTML: {e}")
            return False


class PDFExporter(ReportExporter):
    """PDF 格式导出器"""

    format_name = "pdf"
    file_extension = ".pdf"

    def export(self, report: ReportData, output_path: str) -> bool:
        """
        导出 PDF 报告

        注意：需要 reportlab 库
        pip install reportlab
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # 注册中文字体（如果可用）
            try:
                pdfmetrics.registerFont(TTFont("SimHei", "/usr/share/fonts/truetype/simhei.ttf"))
                chinese_font = "SimHei"
            except Exception as e:
                chinese_font = "Helvetica"

            # 创建文档
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()

            # 自定义样式
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontName=chinese_font,
                fontSize=24,
                spaceAfter=30,
            )

            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading2"],
                fontName=chinese_font,
                fontSize=16,
                spaceAfter=12,
            )

            body_style = ParagraphStyle(
                "CustomBody",
                parent=styles["Normal"],
                fontName=chinese_font,
                fontSize=12,
            )

            elements = []

            # 标题
            elements.append(Paragraph("NAS 诊断报告", title_style))
            elements.append(Spacer(1, 0.5 * cm))

            # 基本信息
            info_data = [
                ["设备名称", report.device_name],
                ["设备ID", report.device_id],
                ["诊断时间", self._format_timestamp(report.timestamp)],
                ["健康分数", f"{report.health_score}/100"],
            ]

            info_table = Table(info_data, colWidths=[4 * cm, 10 * cm])
            info_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), chinese_font),
                        ("FONTSIZE", (0, 0), (-1, -1), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            elements.append(info_table)
            elements.append(Spacer(1, 0.5 * cm))

            # 摘要
            elements.append(Paragraph("摘要", heading_style))
            elements.append(Paragraph(report.summary, body_style))
            elements.append(Spacer(1, 0.5 * cm))

            # 系统状态
            elements.append(Paragraph("系统状态", heading_style))
            metrics_data = [
                ["指标", "值"],
                ["CPU 使用率", f"{report.cpu_usage:.1f}%"],
                ["内存使用率", f"{report.memory_usage:.1f}%"],
                ["磁盘使用率", f"{report.disk_usage:.1f}%"],
            ]

            metrics_table = Table(metrics_data, colWidths=[6 * cm, 6 * cm])
            metrics_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), chinese_font),
                        ("FONTSIZE", (0, 0), (-1, -1), 12),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            elements.append(metrics_table)
            elements.append(Spacer(1, 0.5 * cm))

            # 检查项
            elements.append(Paragraph("检查项", heading_style))
            checks_data = [["名称", "状态", "消息"]]
            for check in report.checks:
                status = "通过" if check.get("passed") else "失败"
                checks_data.append(
                    [
                        check.get("name", ""),
                        status,
                        check.get("message", "")[:50],  # 截断长消息
                    ]
                )

            checks_table = Table(checks_data, colWidths=[4 * cm, 2 * cm, 8 * cm])
            checks_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), chinese_font),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            elements.append(checks_table)

            # 构建 PDF
            doc.build(elements)

            logger.info(f"Exported PDF report: {output_path}")
            return True

        except ImportError:
            logger.warning("reportlab not installed, skipping PDF export")
            return False
        except Exception as e:
            logger.error(f"Failed to export PDF: {e}")
            return False


# 导出器注册表
EXPORTERS = {
    "json": JSONExporter(),
    "markdown": MarkdownExporter(),
    "csv": CSVExporter(),
    "html": HTMLExporter(),
    "pdf": PDFExporter(),
}


def export_report(report: ReportData, output_path: str, format: str = "json") -> bool:
    """
    导出报告到指定格式

    Args:
        report: 报告数据
        output_path: 输出路径
        format: 格式（json, markdown, csv, html, pdf）

    Returns:
        True 如果导出成功
    """
    if format not in EXPORTERS:
        logger.error(f"Unknown format: {format}")
        return False

    exporter = EXPORTERS[format]

    # 确保输出路径有正确的扩展名
    if not output_path.endswith(exporter.file_extension):
        output_path += exporter.file_extension

    return exporter.export(report, output_path)


def export_all_formats(report: ReportData, output_dir: str) -> Dict[str, str]:
    """
    导出所有格式

    Args:
        report: 报告数据
        output_dir: 输出目录

    Returns:
        生成的文件路径字典 {format: path}
    """
    results = {}

    for format_name, exporter in EXPORTERS.items():
        output_path = os.path.join(output_dir, f"report_{report.device_id}.{format_name}")

        if exporter.export(report, output_path):
            results[format_name] = output_path

    return results


if __name__ == "__main__":
    # 测试
    print("=== Report Exporter Test ===\n")

    # 创建测试报告
    test_report = ReportData(
        device_id="test-001",
        device_name="Test NAS",
        timestamp=time.time(),
        health_score=85,
        summary="系统状态良好，CPU 使用率偏高，建议检查后台任务。",
        checks=[
            {"name": "CPU 检查", "passed": True, "message": "CPU 温度正常"},
            {"name": "内存检查", "passed": True, "message": "内存使用率 60%"},
            {"name": "磁盘检查", "passed": False, "message": "磁盘空间不足 20%"},
        ],
        issues=[
            {"title": "磁盘空间警告", "level": "warning", "description": "可用空间不足 20%"},
        ],
        suggestions=[
            "清理临时文件",
            "检查大文件并迁移",
        ],
        cpu_usage=75.5,
        memory_usage=60.2,
        disk_usage=82.3,
    )

    # 导出各种格式
    output_dir = "/tmp/nastool_reports"
    os.makedirs(output_dir, exist_ok=True)

    for format_name in ["json", "markdown", "csv", "html"]:
        output_path = os.path.join(output_dir, f"test_report.{format_name}")
        success = export_report(test_report, output_path, format_name)
        print(f"  {format_name}: {'OK' if success else 'FAIL'}")

    print(f"\nReports saved to: {output_dir}")
    print("\n=== Test Complete ===")
