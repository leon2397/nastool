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
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, errors="replace", timeout=10,
        )
        if result.returncode != 0:
            return ctx.info(current="nvidia-smi failed", message="nvidia-smi 执行失败")

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

        return ctx.failed(
            current="parse error",
            expected="GPU memory info",
            message="无法解析 nvidia-smi 输出",
        )
    except FileNotFoundError:
        return ctx.info(current="nvidia-smi not found", message="nvidia-smi 不可用，跳过检测")
    except Exception as e:
        return ctx.failed(
            current="error",
            expected="GPU memory available",
            message=f"GPU 显存检测失败: {str(e)}",
            severity=CheckSeverity.CRITICAL,
        )


# Backward-compatible class alias
GPUMemoryCheck = gpu_memory
