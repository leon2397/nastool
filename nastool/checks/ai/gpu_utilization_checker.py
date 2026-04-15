# -*- coding: utf-8 -*-
"""GPU 利用率检测"""

import subprocess

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class GPUUtilizationCheck(Check):
    """检测 GPU 计算利用率"""

    check_id = "gpu_utilization"
    category = CheckCategory.AI
    title = "GPU Utilization"
    description = "检查 GPU 计算利用率"

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.INFO, passed=True,
                    title=self.title, current="nvidia-smi failed",
                    expected="GPU utilization monitored",
                    message="nvidia-smi 执行失败",
                    fix_available=False,
                )

            lines = result.stdout.strip().split("\n")
            gpus_info = []
            warnings = []
            for i, line in enumerate(lines):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    gpu_util = int(parts[0])
                    mem_util = int(parts[1])
                    temp = int(parts[2]) if len(parts) >= 3 else None
                    gpus_info.append(f"GPU{i}: GPU {gpu_util}%, Mem {mem_util}%" + (f", {temp}C" if temp is not None else ""))
                    if gpu_util >= 95:
                        warnings.append(f"GPU{i} 利用率 {gpu_util}% 非常高")

            if gpus_info:
                msg = "; ".join(gpus_info)
                if warnings:
                    return CheckResult(
                        check_id=self.check_id, category=self.category,
                        severity=CheckSeverity.WARNING, passed=False,
                        title=self.title, current=gpus_info[0].split(":")[0].strip(),
                        expected="GPU utilization normal",
                        message=msg,
                        fix_available=True,
                        fix_id="reduce_gpu_load",
                        fix_description="GPU 负载过高，考虑优化模型或增加 GPU",
                        fix_risk="medium",
                        details={"gpus": gpus_info},
                    )
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current=gpus_info[0].split(":")[0].strip(),
                    expected="GPU utilization monitored",
                    message=msg,
                    fix_available=False,
                    details={"gpus": gpus_info},
                )
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.CRITICAL, passed=False,
                title=self.title, current="parse error",
                expected="GPU utilization monitored",
                message="无法解析 nvidia-smi 输出",
                fix_available=False,
            )
        except FileNotFoundError:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.INFO, passed=True,
                title=self.title, current="nvidia-smi not found",
                expected="GPU utilization monitored",
                message="nvidia-smi 不可用，跳过检测",
                fix_available=False,
            )
        except Exception as e:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.CRITICAL, passed=False,
                title=self.title, current="error",
                expected="GPU utilization monitored",
                message=f"GPU 利用率检测失败: {str(e)}",
                fix_available=False,
            )
