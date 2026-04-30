# -*- coding: utf-8 -*-
"""
reporters/pdf_reporter.py - PDF 报告生成器

v7.0 新增功能：
- 生成专业 PDF 诊断报告
- 支持 Logo 插入
- 支持中文字体

依赖：pip install reportlab

使用方式：
    from reporters.pdf_reporter import PDFReporter
    
    reporter = PDFReporter(
        logo_path="assets/logo.png"  # 可选
    )
    reporter.generate(report, output_path="report.pdf")
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# 尝试导入 reportlab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from nastool_core.utils.health_scorer import HealthReport, score_color


# ============================================================
# PDFReporter
# ============================================================

class PDFReporter:
    """
    PDF 报告生成器
    
    生成格式：
    - 封面（带 Logo）
    - 综合评分
    - 分类详情
    - 问题列表
    - 建议
    """

    def __init__(
        self,
        logo_path: Optional[str] = None,
        title: str = "NASArm Toolkit 诊断报告",
        author: str = "NASArm Toolkit",
    ):
        """
        初始化 PDFReporter
        
        Args:
            logo_path: Logo 图片路径（可选）
            title: 报告标题
            author: 报告作者
        """
        self.logo_path = logo_path
        self.title = title
        self.author = author
        
        # 中文字体（使用系统内置）
        self._styles = None
        self._setup_styles()

    def _setup_styles(self):
        """设置样式"""
        self._styles = getSampleStyleSheet()
        
        # 标题
        self._styles.add(ParagraphStyle(
            name='PDFTitle',
            parent=self._styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#6366f1'),
            alignment=TA_CENTER,
            spaceAfter=20,
        ))
        
        # 副标题
        self._styles.add(ParagraphStyle(
            name='PDFSubtitle',
            parent=self._styles['Normal'],
            fontSize=12,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=30,
        ))
        
        # 章节标题
        self._styles.add(ParagraphStyle(
            name='PDFHeading',
            parent=self._styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#6366f1'),
            spaceBefore=20,
            spaceAfter=10,
        ))
        
        # 正文
        self._styles.add(ParagraphStyle(
            name='PDFBody',
            parent=self._styles['Normal'],
            fontSize=10,
            leading=16,
        ))
        
        # 问题项（红色）
        self._styles.add(ParagraphStyle(
            name='PDFCritical',
            parent=self._styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#ef4444'),
            leading=14,
        ))
        
        # 警告项（黄色）
        self._styles.add(ParagraphStyle(
            name='PDFWarning',
            parent=self._styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#f59e0b'),
            leading=14,
        ))

    def generate(self, report: HealthReport, output_path: str) -> bool:
        """
        生成 PDF 报告
        
        Args:
            report: HealthReport 健康评分报告
            output_path: 输出 PDF 文件路径
            
        Returns:
            是否生成成功
        """
        if not HAS_REPORTLAB:
            print("[PDFReporter] reportlab 未安装，请运行: pip install reportlab")
            return False
        
        try:
            # 创建文档
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm,
            )
            
            # 构建内容
            story = []
            
            # 封面
            self._add_cover(story, report)
            
            # 综合评分
            self._add_overview(story, report)
            
            # 分类详情
            self._add_categories(story, report)
            
            # 问题列表
            self._add_issues(story, report)
            
            # 建议
            self._add_suggestions(story, report)
            
            # 生成 PDF
            doc.build(story)
            
            print(f"[PDFReporter] 报告已生成: {output_path}")
            return True
            
        except Exception as e:
            print(f"[PDFReporter] 生成失败: {e}")
            return False

    def _add_cover(self, story, report: HealthReport):
        """添加封面"""
        # Logo
        if self.logo_path and os.path.exists(self.logo_path):
            logo = Image(self.logo_path, width=80*mm, height=30*mm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 20))
        
        # 标题
        story.append(Paragraph(self.title, self._styles['PDFTitle']))
        story.append(Spacer(1, 10))
        
        # 副标题
        timestamp = datetime.fromtimestamp(
            report.previous_score if isinstance(report.previous_score, (int, float)) else 0
        ).strftime('%Y-%m-%d %H:%M') if report.previous_score else datetime.now().strftime('%Y-%m-%d %H:%M')
        
        subtitle = f"<b>健康评分：{report.overall_score}/100</b> | 等级：{report.level_label}<br/>生成时间：{timestamp}"
        story.append(Paragraph(subtitle, self._styles['PDFSubtitle']))
        
        story.append(Spacer(1, 40))

    def _add_overview(self, story, report: HealthReport):
        """添加综合评分"""
        story.append(Paragraph("综合评分", self._styles['PDFHeading']))
        
        # 评分卡片
        data = [
            ['评分', '等级', '等级说明'],
            [
                f"{report.overall_score}/100",
                report.level_label,
                report.level_desc
            ]
        ]
        
        table = Table(data, colWidths=[80, 100, 250])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 14),
            ('TOPPADDING', (0, 1), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROUNDEDCORNERS', [5, 5, 5, 5]),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        # 统计
        stats_data = [
            ['检查项', '通过', '警告', '严重', '信息'],
            [
                str(report.total_checks),
                str(report.total_passed),
                str(report.total_warnings),
                str(report.total_critical),
                str(report.total_info)
            ]
        ]
        
        stats_table = Table(stats_data, colWidths=[60]*5)
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 30))

    def _add_categories(self, story, report: HealthReport):
        """添加分类详情"""
        story.append(Paragraph("分类评分", self._styles['PDFHeading']))
        
        data = [['类别', '评分', '检查项', '通过', '警告', '严重']]
        
        for cat in report.category_scores:
            data.append([
                cat.name,
                f"{cat.score}/100",
                str(cat.total),
                str(cat.passed),
                str(cat.warnings),
                str(cat.critical),
            ])
        
        table = Table(data, colWidths=[80, 70, 60, 50, 50, 50])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            # 斑马纹
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#f8fafc')),
            ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#f8fafc')),
            ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor('#f8fafc')),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))

    def _add_issues(self, story, report: HealthReport):
        """添加问题列表"""
        if not report.critical_items and not report.warnings_items:
            story.append(Paragraph("✓ 暂无问题", self._styles['PDFBody']))
            return
        
        story.append(Paragraph("问题详情", self._styles['PDFHeading']))
        
        # 严重问题
        if report.critical_items:
            story.append(Paragraph("🔴 严重问题", self._styles['PDFCritical']))
            for item in report.critical_items:
                msg = f"• {item.check_id}: {item.message}"
                story.append(Paragraph(msg, self._styles['PDFCritical']))
            story.append(Spacer(1, 10))
        
        # 警告问题
        if report.warnings_items:
            story.append(Paragraph("[!]  警告问题", self._styles['PDFWarning']))
            for item in report.warnings_items:
                msg = f"• {item.check_id}: {item.message}"
                story.append(Paragraph(msg, self._styles['PDFWarning']))
        
        story.append(Spacer(1, 20))

    def _add_suggestions(self, story, report: HealthReport):
        """添加建议"""
        story.append(Paragraph("修复建议", self._styles['PDFHeading']))
        
        suggestions = self._generate_suggestions(report)
        
        for i, suggestion in enumerate(suggestions, 1):
            story.append(Paragraph(f"{i}. {suggestion}", self._styles['PDFBody']))
            story.append(Spacer(1, 5))
        
        # 页脚
        story.append(Spacer(1, 30))
        footer = f"<i>由 {self.author} 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>"
        story.append(Paragraph(footer, self._styles['PDFSubtitle']))

    def _generate_suggestions(self, report: HealthReport) -> list:
        """生成修复建议"""
        suggestions = []
        
        # 根据问题生成建议
        if report.total_critical > 0:
            suggestions.append(f"存在 {report.total_critical} 项严重问题，建议立即处理")
        
        if report.total_warnings > 0:
            suggestions.append(f"存在 {report.total_warnings} 项警告，建议关注")
        
        if report.overall_score < 60:
            suggestions.append("系统健康状况较差，建议进行系统优化")
        elif report.overall_score < 80:
            suggestions.append("系统存在可优化空间，建议定期检查")
        else:
            suggestions.append("系统状态良好，继续保持")
        
        # 分类建议
        for cat in report.category_scores:
            if cat.critical > 0:
                suggestions.append(f"{cat.name} 分类存在 {cat.critical} 项严重问题，需要重点关注")
        
        return suggestions[:10]  # 最多10条建议


# ============================================================
# 便捷函数
# ============================================================

def generate_pdf_report(
    report: HealthReport,
    output_path: str,
    logo_path: Optional[str] = None
) -> bool:
    """
    一行调用生成 PDF 报告
    
    Args:
        report: HealthReport 健康评分报告
        output_path: 输出 PDF 文件路径
        logo_path: Logo 图片路径（可选）
        
    Returns:
        是否生成成功
    """
    reporter = PDFReporter(logo_path=logo_path)
    return reporter.generate(report, output_path)


# 导出
__all__ = ['PDFReporter', 'generate_pdf_report']
