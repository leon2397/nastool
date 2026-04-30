# -*- coding: utf-8 -*-
"""
reporters/rk_reporter.py - RK3588/RK3568 专用诊断报告器

特性:
- RK 芯片专用评分（NPU 权重更高）
- 趋势分析（对比历史数据）
- 调优建议集成
- JSON/Markdown/纯文本输出

Usage:
    reporter = RKReporter(chip_model="RK3588")
    reporter.generate(results, output_format="text")
    reporter.generate(results, output_format="markdown", output_path="report.md")
    reporter.generate(results, output_format="json", output_path="report.json")
"""

import json
import time
import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from nastool_core.checks.base import CheckResult, CheckSeverity
from nastool_core.utils.health_scorer import calculate_health_score


@dataclass
class TrendPoint:
    """趋势数据点"""
    timestamp: float
    overall_score: float
    npu_score: float
    cpu_score: float
    thermal_score: float


class RKReporter:
    """
    RK3588/RK3568 专用报告器
    
    相比通用 TerminalReporter，增加了:
    1. RK 芯片加权评分（NPU 权重 30%）
    2. 历史趋势对比
    3. 调优建议摘要
    4. 多格式输出（text/markdown/json）
    """
    
    # 不同芯片型号的权重配置
    CHIP_WEIGHTS = {
        # 高性能芯片（重视 AI 能力）
        "RK3588": {
            "ai": 0.30,       # NPU/AI 权重最高
            "system": 0.20,   # 系统基础
            "nas": 0.15,      # 存储
            "network": 0.10,  # 网络
            "security": 0.10, # 安全
            "storage": 0.15,  # 存储
        },
        # 中端芯片（平衡配置）
        "RK3568": {
            "ai": 0.25,       # NPU 权重较高
            "system": 0.20,   # 系统基础
            "nas": 0.15,      # 存储
            "network": 0.15,  # 网络
            "security": 0.10, # 安全
            "storage": 0.15,  # 存储
        },
        # 入门级芯片（重视系统稳定性）
        "RK3566": {
            "ai": 0.20,       # NPU 权重适中
            "system": 0.25,   # 系统基础权重更高
            "nas": 0.15,      # 存储
            "network": 0.15,  # 网络
            "security": 0.10, # 安全
            "storage": 0.15,  # 存储
        },
        # 其他 RK 芯片（默认配置）
        "RK3399": {
            "ai": 0.15,       # 无 NPU，AI 权重较低
            "system": 0.30,   # 系统基础权重最高
            "nas": 0.15,      # 存储
            "network": 0.15,  # 网络
            "security": 0.10, # 安全
            "storage": 0.15,  # 存储
        },
        "RK3288": {
            "ai": 0.10,       # 无 NPU，AI 权重最低
            "system": 0.35,   # 系统基础权重最高
            "nas": 0.15,      # 存储
            "network": 0.15,  # 网络
            "security": 0.10, # 安全
            "storage": 0.15,  # 存储
        },
    }
    
    # 默认权重（当芯片型号未匹配时使用）
    DEFAULT_WEIGHTS = {
        "ai": 0.20,       # AI 权重适中
        "system": 0.25,   # 系统基础
        "nas": 0.15,      # 存储
        "network": 0.15,  # 网络
        "security": 0.10, # 安全
        "storage": 0.15,  # 存储
    }
    
    # 温度评级
    THERMAL_RATINGS = {
        "excellent": {"max": 45, "label": "Excellent", "icon": "[OK]"},
        "good": {"max": 60, "label": "Good", "icon": "[OK]"},
        "warm": {"max": 75, "label": "Warm", "icon": "[!]"},
        "hot": {"max": 85, "label": "Hot", "icon": "[!!]"},
        "critical": {"max": 999, "label": "Critical", "icon": "[!!!]"},
    }
    
    def __init__(
        self,
        chip_model: str = "RK3588",
        history_dir: Optional[str] = None,
    ):
        """
        初始化 RK 报告器
        
        Args:
            chip_model: 芯片型号
            history_dir: 历史报告目录（用于趋势分析）
        """
        self.chip_model = chip_model.upper()
        self.history_dir = history_dir or os.path.join(
            os.path.expanduser("~"), ".nastool", "history"
        )
    
    def generate(
        self,
        results: List[CheckResult],
        output_format: str = "text",
        output_path: Optional[str] = None,
        tune_profile: Optional[str] = None,
    ) -> str:
        """
        生成 RK 专用报告
        
        Args:
            results: 检测结果列表
            output_format: 输出格式 (text/markdown/json)
            output_path: 输出文件路径（None 则打印到终端）
            tune_profile: 调优配置文件
            
        Returns:
            报告内容字符串
        """
        # 计算评分
        report = calculate_health_score(results)
        rk_score = self._calculate_rk_score(results)
        thermal_rating = self._assess_thermal(results)
        
        # 趋势分析
        trend = self._analyze_trend(rk_score)
        
        # 生成报告内容
        if output_format == "json":
            content = self._generate_json(results, report, rk_score, thermal_rating, trend, tune_profile)
        elif output_format == "markdown":
            content = self._generate_markdown(results, report, rk_score, thermal_rating, trend, tune_profile)
        else:
            content = self._generate_text(results, report, rk_score, thermal_rating, trend, tune_profile)
        
        # 保存历史
        self._save_history(rk_score, results)
        
        # 输出
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Report saved to: {output_path}")
        else:
            print(content)
        
        return content
    
    def _calculate_rk_score(self, results: List[CheckResult]) -> Dict[str, Any]:
        """计算 RK 专用加权评分"""
        # 按分类统计
        cat_scores = {}
        for r in results:
            cat = getattr(r, 'category', 'system')
            if cat not in cat_scores:
                cat_scores[cat] = {"total": 0, "passed": 0, "critical": 0, "warning": 0}
            cat_scores[cat]["total"] += 1
            if r.passed:
                cat_scores[cat]["passed"] += 1
            if r.severity == CheckSeverity.CRITICAL and not r.passed:
                cat_scores[cat]["critical"] += 1
            elif r.severity == CheckSeverity.WARNING and not r.passed:
                cat_scores[cat]["warning"] += 1
        
        # 计算各分类评分
        for cat in cat_scores:
            s = cat_scores[cat]
            if s["total"] > 0:
                base = (s["passed"] / s["total"]) * 100
                # 严重问题扣分
                penalty = s["critical"] * 15 + s["warning"] * 5
                s["score"] = max(0, base - penalty)
            else:
                s["score"] = 100
        
        # 获取当前芯片型号的权重配置
        weights = self.CHIP_WEIGHTS.get(self.chip_model, self.DEFAULT_WEIGHTS)
        
        # 加权汇总
        overall = 0
        total_weight = 0
        for cat, weight in weights.items():
            if cat in cat_scores:
                overall += cat_scores[cat]["score"] * weight
                total_weight += weight
        
        if total_weight > 0:
            overall = round(overall / total_weight)
        else:
            overall = 0
        
        # 确定等级
        if overall >= 90:
            grade, level = "A", "Excellent"
        elif overall >= 80:
            grade, level = "B", "Good"
        elif overall >= 70:
            grade, level = "C", "Fair"
        elif overall >= 60:
            grade, level = "D", "Poor"
        else:
            grade, level = "F", "Critical"
        
        return {
            "overall_score": overall,
            "grade": grade,
            "level": level,
            "category_scores": {str(cat): s["score"] for cat, s in cat_scores.items()},
        }
    
    def _assess_thermal(self, results: List[CheckResult]) -> Dict[str, Any]:
        """评估散热状态"""
        temps = {}
        for r in results:
            cid = getattr(r, 'check_id', '')
            val = getattr(r, 'value', getattr(r, 'current', None))
            if val is None:
                continue
            
            # 检测温度相关的检测项
            if 'temp' in cid.lower() or 'thermal' in cid.lower():
                try:
                    temp_c = float(str(val).replace('C', '').replace('c', '').strip())
                    temps[cid] = temp_c
                except (ValueError, TypeError):
                    pass
        
        if not temps:
            return {"status": "unknown", "max_temp": None, "rating": "N/A"}
        
        max_temp = max(temps.values())
        rating = "critical"
        for level, spec in self.THERMAL_RATINGS.items():
            if max_temp <= spec["max"]:
                rating = level
                break
        
        return {
            "status": rating,
            "max_temp": max_temp,
            "rating": self.THERMAL_RATINGS.get(rating, {}).get("label", "Unknown"),
            "icon": self.THERMAL_RATINGS.get(rating, {}).get("icon", "[?]"),
            "sensors": temps,
        }
    
    def _analyze_trend(self, rk_score: Dict) -> Dict[str, Any]:
        """分析历史趋势"""
        history = self._load_history()
        
        if len(history) < 2:
            return {"available": False, "direction": "N/A", "change": 0}
        
        # 最近 2 次对比
        latest = history[-1]
        previous = history[-2]
        change = latest["overall_score"] - previous["overall_score"]
        
        if change > 5:
            direction = "improving"
        elif change < -5:
            direction = "declining"
        else:
            direction = "stable"
        
        return {
            "available": True,
            "direction": direction,
            "change": change,
            "history_count": len(history),
            "latest_score": latest["overall_score"],
        }
    
    def _generate_text(
        self,
        results: List[CheckResult],
        report,
        rk_score: Dict,
        thermal: Dict,
        trend: Dict,
        tune_profile: Optional[str],
    ) -> str:
        """生成文本格式报告"""
        lines = []
        w = 60
        
        lines.append("=" * w)
        lines.append(f"  NASTool RK Diagnostic Report")
        lines.append(f"  Chip: {self.chip_model}")
        lines.append(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * w)
        
        # 1. RK Score
        lines.append("")
        lines.append(f"  RK Score: {rk_score['overall_score']}/100  Grade: {rk_score['grade']} ({rk_score['level']})")
        
        # 2. Category scores
        lines.append("")
        lines.append("  Category Scores (RK-weighted):")
        for cat, score in rk_score.get("category_scores", {}).items():
            bar_len = int(score / 100 * 30)
            bar = "#" * bar_len + "-" * (30 - bar_len)
            lines.append(f"    {cat:12s} [{bar}] {score:.0f}")
        
        # 3. Thermal
        if thermal.get("max_temp") is not None:
            lines.append("")
            lines.append(f"  Thermal: {thermal['icon']} {thermal['rating']} (max: {thermal['max_temp']}C)")
            for sensor, temp in thermal.get("sensors", {}).items():
                lines.append(f"    {sensor}: {temp}C")
        
        # 4. Trend
        if trend.get("available"):
            arrow = {"improving": "^", "declining": "v", "stable": "="}.get(trend["direction"], "?")
            lines.append("")
            lines.append(f"  Trend: {arrow} {trend['direction']} ({trend['change']:+.0f} pts, {trend['history_count']} reports)")
        
        # 5. Failed checks
        failed = [r for r in results if not r.passed and r.severity != CheckSeverity.INFO]
        if failed:
            lines.append("")
            lines.append(f"  Issues ({len(failed)}):")
            for r in failed:
                icon = "[X]" if r.severity == CheckSeverity.CRITICAL else "[!]"
                lines.append(f"    {icon} {getattr(r, 'title', getattr(r, 'name', r.check_id))}")
                msg = getattr(r, 'message', getattr(r, 'summary', ''))
                if msg:
                    lines.append(f"       {msg}")
        
        # 6. Tuning suggestions
        if tune_profile:
            lines.append("")
            lines.append(f"  Tune Profile: {tune_profile}")
        
        lines.append("")
        lines.append("=" * w)
        
        return "\n".join(lines)
    
    def _generate_markdown(
        self,
        results: List[CheckResult],
        report,
        rk_score: Dict,
        thermal: Dict,
        trend: Dict,
        tune_profile: Optional[str],
    ) -> str:
        """生成 Markdown 格式报告"""
        lines = []
        
        lines.append(f"# NASTool RK Diagnostic Report")
        lines.append("")
        lines.append(f"**Chip:** {self.chip_model}  ")
        lines.append(f"**Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ")
        lines.append(f"**RK Score:** {rk_score['overall_score']}/100 (Grade {rk_score['grade']}: {rk_score['level']})  ")
        lines.append("")
        
        # Category scores table
        lines.append("## Category Scores (RK-weighted)")
        lines.append("")
        lines.append("| Category | Score | Bar |")
        lines.append("|----------|-------|-----|")
        for cat, score in rk_score.get("category_scores", {}).items():
            bar_len = int(score / 100 * 20)
            bar = "#" * bar_len + "-" * (20 - bar_len)
            lines.append(f"| {cat} | {score:.0f} | `{bar}` |")
        lines.append("")
        
        # Thermal
        if thermal.get("max_temp") is not None:
            lines.append("## Thermal Status")
            lines.append("")
            lines.append(f"**Rating:** {thermal['rating']} (max: {thermal['max_temp']}C)")
            lines.append("")
            lines.append("| Sensor | Temperature |")
            lines.append("|--------|-------------|")
            for sensor, temp in thermal.get("sensors", {}).items():
                lines.append(f"| {sensor} | {temp}C |")
            lines.append("")
        
        # Trend
        if trend.get("available"):
            lines.append("## Trend Analysis")
            lines.append("")
            lines.append(f"- Direction: **{trend['direction']}**")
            lines.append(f"- Change: {trend['change']:+.0f} pts")
            lines.append(f"- Reports: {trend['history_count']}")
            lines.append("")
        
        # Issues
        failed = [r for r in results if not r.passed and r.severity != CheckSeverity.INFO]
        if failed:
            lines.append("## Issues")
            lines.append("")
            for r in failed:
                icon = "X" if r.severity == CheckSeverity.CRITICAL else "!"
                title = getattr(r, 'title', getattr(r, 'name', r.check_id))
                msg = getattr(r, 'message', getattr(r, 'summary', ''))
                lines.append(f"- [{icon}] **{title}**: {msg}")
            lines.append("")
        
        # All checks
        lines.append("## All Checks")
        lines.append("")
        lines.append("| Check | Severity | Passed | Value |")
        lines.append("|-------|----------|--------|-------|")
        for r in results:
            title = getattr(r, 'title', getattr(r, 'name', r.check_id))
            val = getattr(r, 'value', getattr(r, 'current', ''))
            lines.append(f"| {title} | {r.severity.value} | {'Y' if r.passed else 'N'} | {val} |")
        lines.append("")
        
        return "\n".join(lines)
    
    def _generate_json(
        self,
        results: List[CheckResult],
        report,
        rk_score: Dict,
        thermal: Dict,
        trend: Dict,
        tune_profile: Optional[str],
    ) -> str:
        """生成 JSON 格式报告"""
        data = {
            "version": "2.0.0",
            "chip_model": self.chip_model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "rk_score": rk_score,
            "thermal": thermal,
            "trend": trend,
            "tune_profile": tune_profile,
            "results": [
                {
                    "check_id": r.check_id,
                    "title": getattr(r, 'title', getattr(r, 'name', '')),
                    "severity": r.severity.value if hasattr(r.severity, 'value') else str(r.severity),
                    "passed": r.passed,
                    "message": getattr(r, 'message', getattr(r, 'summary', '')),
                    "value": str(getattr(r, 'value', getattr(r, 'current', ''))),
                    "category": str(getattr(r, 'category', 'system')),
                }
                for r in results
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    # ===== 历史数据管理 =====
    
    def _save_history(self, rk_score: Dict, results: List[CheckResult]):
        """保存本次评分到历史"""
        os.makedirs(self.history_dir, exist_ok=True)
        
        # 提取分类评分
        cat_scores = rk_score.get("category_scores", {})
        
        point = {
            "timestamp": time.time(),
            "overall_score": rk_score["overall_score"],
            "npu_score": cat_scores.get("ai", 0),
            "cpu_score": cat_scores.get("system", 0),
            "thermal_score": cat_scores.get("thermal", 100),
        }
        
        # 追加到历史文件
        history_file = os.path.join(self.history_dir, f"{self.chip_model.lower()}_history.json")
        
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []
        
        history.append(point)
        
        # 只保留最近 100 次
        if len(history) > 100:
            history = history[-100:]
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    
    def _load_history(self) -> List[Dict]:
        """加载历史评分数据"""
        history_file = os.path.join(self.history_dir, f"{self.chip_model.lower()}_history.json")
        
        if not os.path.exists(history_file):
            return []
        
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []


def generate_rk_report(
    results: List[CheckResult],
    chip_model: str = "RK3588",
    output_format: str = "text",
    output_path: Optional[str] = None,
    tune_profile: Optional[str] = None,
) -> str:
    """便捷函数：生成 RK 专用报告"""
    reporter = RKReporter(chip_model=chip_model)
    return reporter.generate(results, output_format, output_path, tune_profile)
