# -*- coding: utf-8 -*-
"""GPU 显存使用检测 (declarative style)"""

from __future__ import annotations

import subprocess

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult


@check(
    id="gpu_memory",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="GPU Memory",
    description="检查 GPU 显存使用率和可用显存",
    timeout=10,
    depends_on=["gpu_detected"],
)
def gpu_memory(ctx: CheckContext) -> CheckResult:
    """检测 GPU 显存使用情况"""
    try:
        # 方法 1：使用 nvidia-smi 命令（标准 NVIDIA GPU）
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total,memory.free",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                gpus_info = []
                warnings = []
                for i, line in enumerate(lines):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 3:
                        used_mb = int(parts[0]); total_mb = int(parts[1]); free_mb = int(parts[2])
                        used_pct = (used_mb / total_mb * 100) if total_mb > 0 else 0
                        gpus_info.append(f"GPU{i}: {used_mb}MB/{total_mb}MB ({used_pct:.1f}%, free {free_mb}MB)")
                        if used_pct >= 90:
                            warnings.append(f"GPU{i} 显存使用率 {used_pct:.1f}% 过高")

                if gpus_info:
                    msg = "; ".join(gpus_info)
                    if warnings:
                        return ctx.failed(
                            current=gpus_info[0].split("(")[0].strip(),
                            expected="<90% usage",
                            message=msg,
                            fix_available=True,
                            fix_id="free_gpu_memory",
                            fix_description="清理 GPU 显存或增加显存",
                            fix_risk="low",
                            details={"gpus": gpus_info},
                        )
                    return ctx.passed(
                        current=gpus_info[0].split("(")[0].strip(),
                        expected="GPU memory available",
                        message=msg,
                        details={"gpus": gpus_info},
                    )
        except FileNotFoundError:
            # nvidia-smi 不可用，尝试使用 tegrastats（Jetson 设备）
            pass
        
        # 方法 2：使用 tegrastats 命令（Jetson 设备）
        try:
            result = subprocess.run(
                ["tegrastats", "--json", "--interval", "100", "--count", "1"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                if "RAM" in data:
                    ram = data["RAM"]
                    total_mb = ram.get("total", 0) / 1024  # 转换为 MB
                    used_mb = ram.get("used", 0) / 1024
                    free_mb = ram.get("free", 0) / 1024
                    used_pct = (used_mb / total_mb * 100) if total_mb > 0 else 0
                    gpus_info = [f"Jetson: {used_mb:.0f}MB/{total_mb:.0f}MB ({used_pct:.1f}%, free {free_mb:.0f}MB)"]
                    warnings = []
                    if used_pct >= 90:
                        warnings.append(f"Jetson 内存使用率 {used_pct:.1f}% 过高")
                    
                    msg = "; ".join(gpus_info)
                    if warnings:
                        return ctx.failed(
                            current=gpus_info[0].split("(")[0].strip(),
                            expected="<90% usage",
                            message=msg,
                            fix_available=True,
                            fix_id="free_gpu_memory",
                            fix_description="清理 GPU 显存或增加显存",
                            fix_risk="low",
                            details={"gpus": gpus_info},
                        )
                    return ctx.passed(
                        current=gpus_info[0].split("(")[0].strip(),
                        expected="GPU memory available",
                        message=msg,
                        details={"gpus": gpus_info},
                    )
        except Exception:
            # tegrastats 不可用或解析失败
            pass
        
        # 方法 3：检查 NVIDIA GPU 相关文件（备选）
        try:
            import os
            if os.path.exists("/proc/driver/nvidia/gpus/") and len(os.listdir("/proc/driver/nvidia/gpus/")) > 0:
                # 检测到 NVIDIA GPU，但无法获取详细信息
                return ctx.info(current="GPU detected", message="GPU 已检测到，但无法获取显存信息")
        except Exception:
            pass
        
        return ctx.failed(
            current="parse error",
            expected="GPU memory info",
            message="无法解析 GPU 显存信息",
        )
    except Exception as e:
        return ctx.failed(
            current="error",
            expected="GPU memory available",
            message=f"GPU 显存检测失败: {str(e)}",
            severity=CheckSeverity.CRITICAL,
        )


# Backward-compatible class alias
GPUMemoryCheck = gpu_memory
