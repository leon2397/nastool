# -*- coding: utf-8 -*-
"""GPU 利用率检测 (declarative style)"""

from __future__ import annotations

import subprocess

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult


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
        # 方法 1：使用 nvidia-smi 命令（标准 NVIDIA GPU）
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
            )
            if result.returncode == 0:
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
                gpus_info = []
                warnings = []
                
                # 提取 GPU 相关信息
                if "GR3D_FREQ" in data:
                    gpu_freq = data["GR3D_FREQ"]
                    # 假设频率不为 0 表示有 GPU 活动
                    gpu_util = 0
                    if isinstance(gpu_freq, list) and len(gpu_freq) > 0:
                        # 简单计算 GPU 利用率（基于频率）
                        max_freq = 1000  # 假设最大频率为 1000 MHz
                        current_freq = gpu_freq[0]
                        gpu_util = int((current_freq / max_freq) * 100)
                else:
                    gpu_util = 0
                
                # 提取内存使用率
                mem_util = 0
                if "RAM" in data:
                    ram = data["RAM"]
                    total = ram.get("total", 1)
                    used = ram.get("used", 0)
                    mem_util = int((used / total) * 100)
                
                # 提取温度
                temp = None
                if "TEMPERATURE" in data:
                    temp_data = data["TEMPERATURE"]
                    if isinstance(temp_data, dict) and "CPU" in temp_data:
                        temp = temp_data["CPU"]
                
                info = f"Jetson: GPU {gpu_util}%, Mem {mem_util}%"
                if temp is not None:
                    info += f", {temp}C"
                gpus_info.append(info)
                
                if gpu_util >= 95:
                    warnings.append(f"Jetson GPU 利用率 {gpu_util}% 非常高")
                
                if gpus_info:
                    msg = "; ".join(gpus_info)
                    if warnings:
                        return ctx.failed(
                            current="Jetson",
                            expected="GPU utilization normal",
                            message=msg,
                            fix_available=True,
                            fix_id="reduce_gpu_load",
                            fix_description="GPU 负载过高，考虑优化模型或增加 GPU",
                            fix_risk="medium",
                            details={"gpus": gpus_info},
                        )
                    return ctx.passed(
                        current="Jetson",
                        expected="GPU utilization monitored",
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
                return ctx.info(current="GPU detected", message="GPU 已检测到，但无法获取利用率信息")
        except Exception:
            pass
        
        return ctx.failed(
            current="parse error",
            expected="GPU utilization monitored",
            message="无法解析 GPU 利用率信息",
            severity=CheckSeverity.CRITICAL,
        )
    except Exception as e:
        return ctx.failed(
            current="error",
            expected="GPU utilization monitored",
            message=f"GPU 利用率检测失败: {str(e)}",
            severity=CheckSeverity.CRITICAL,
        )


# Backward-compatible class alias
GPUUtilizationCheck = gpu_utilization
