# -*- coding: utf-8 -*-
"""GPU 利用率检测 (declarative style)"""

from __future__ import annotations

import subprocess

from checks.decorators import check, CheckContext
from checks.base import CheckCategory, CheckSeverity, CheckResult


@check(
    id="gpu_utilization",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="GPU Utilization",
    description="检查 GPU 计算利用率",
    timeout=10,
    depends_on=["gpu_detected"],
)
def gpu_utilization(ctx: CheckContext) -> CheckResult:
    """检测 GPU 计算利用率"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return ctx.info(current="nvidia-smi failed", message="nvidia-smi 执行失败")

        lines = result.stdout.strip().split("\n")
        gpus_info = []
        warnings = []
        for i, line in enumerate(lines):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                gpu_util = int(parts[0])
                mem_util = int(parts[1])
                temp = int(parts[2]) if len(parts) >= 3 else None
                info = f"GPU{i}: GPU {gpu_util}%, Mem {mem_util}%"
                if temp is not None:
                    info += f", {temp}C"
                gpus_info.append(info)
                if gpu_util >= 95:
                    warnings.append(f"GPU{i} 利用率 {gpu_util}% 非常高")

        if gpus_info:
            msg = "; ".join(gpus_info)
            if warnings:
                return ctx.failed(
                    current=gpus_info[0].split(":")[0].strip(),
                    expected="GPU utilization normal",
                    message=msg,
                    fix_available=True,
                    fix_id="reduce_gpu_load",
                    fix_description="GPU 负载过高，考虑优化模型或增加 GPU",
                    fix_risk="medium",
                    details={"gpus": gpus_info},
                )
            return ctx.passed(
                current=gpus_info[0].split(":")[0].strip(),
                expected="GPU utilization monitored",
                message=msg,
                details={"gpus": gpus_info},
            )

        return ctx.failed(
            current="parse error",
            expected="GPU utilization monitored",
            message="无法解析 nvidia-smi 输出",
            severity=CheckSeverity.CRITICAL,
        )
    except FileNotFoundError:
        return ctx.info(current="nvidia-smi not found", message="nvidia-smi 不可用，跳过检测")
    except Exception as e:
        return ctx.failed(
            current="error",
            expected="GPU utilization monitored",
            message=f"GPU 利用率检测失败: {str(e)}",
            severity=CheckSeverity.CRITICAL,
        )


# Backward-compatible class alias
GPUUtilizationCheck = gpu_utilization
