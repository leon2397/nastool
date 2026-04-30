# -*- coding: utf-8 -*-
"""系统内存检测 - 使用准确性保障方法"""
from __future__ import annotations

import subprocess
from nastool_core.checks.base import Check, CheckResult, CheckCategory, CheckSeverity
from nastool_core.checks.registry import register_check


@register_check
class MemoryCheck(Check):
    """系统内存检测 - 使用多源数据融合提高准确性"""
    
    check_id = "memory_check"
    category = CheckCategory.SYSTEM
    title = "Memory Check"
    description = "检查系统内存是否充足，使用多源数据融合提高检测准确性"
    
    def run(self) -> CheckResult:
        # 收集多源数据
        data_sources = []
        
        # 数据源1: PowerShell (Windows)
        try:
            r = subprocess.run(
                "powershell -Command \"(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize/1MB\"",
                shell=True, capture_output=True, text=True, timeout=10
            )
            total = float(r.stdout.strip()) / 1024  # MB to GB
            data_sources.append(self._create_data_source_result(total, "powershell", confidence=0.9))
        except Exception:
            pass
        
        # 数据源2: free命令 (Linux)
        try:
            r = subprocess.run("free -m", shell=True,
                               capture_output=True, text=True, errors="replace", timeout=5)
            lines = r.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                total = float(parts[1]) / 1024  # MB to GB
                data_sources.append(self._create_data_source_result(total, "free_command", confidence=0.85))
        except Exception:
            pass
        
        # 数据源3: /proc/meminfo (Linux)
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total = float(line.split()[1]) / (1024 * 1024)  # KB to GB
                        data_sources.append(self._create_data_source_result(total, "proc_meminfo", confidence=0.95))
                        break
        except Exception:
            pass
        
        # 如果没有任何数据源
        if not data_sources:
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                title=self.title,
                passed=False,
                current="unknown",
                expected="detectable",
                message="Could not determine memory - no data sources available",
                severity=CheckSeverity.INFO,
                confidence=0.0,
                data_sources=[]
            )
        
        # 使用准确性保障方法处理数据
        result, metadata = self._fuse_multiple_sources(data_sources)
        consistency_result = self._validate_consistency(data_sources)
        
        # 获取融合后的值
        if result is None:
            # 使用第一个数据源作为备选
            result = data_sources[0].value
        
        total = float(result)
        confidence = self._calculate_overall_confidence(metadata, consistency_result)
        
        min_required = 1.0  # GB
        if total < min_required:
            check_result = CheckResult(
                check_id=self.check_id,
                category=self.category,
                title=self.title,
                passed=False,
                current=f"{total:.1f}GB",
                expected=f">= {min_required:.0f}GB",
                message=f"Memory {total:.1f}GB below minimum {min_required:.0f}GB",
                severity=CheckSeverity.WARNING,
                confidence=confidence,
                data_sources=[r.source for r in data_sources]
            )
        else:
            check_result = CheckResult(
                check_id=self.check_id,
                category=self.category,
                title=self.title,
                passed=True,
                current=f"{total:.1f}GB",
                expected=f">= {min_required:.0f}GB",
                message=f"Memory {total:.1f}GB available",
                severity=CheckSeverity.PASSED,
                confidence=confidence,
                data_sources=[r.source for r in data_sources]
            )
        
        # 增强结果
        return self._enhance_result_with_accuracy(check_result, data_sources)
