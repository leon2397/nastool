# -*- coding: utf-8 -*-
"""
nastool adapters - 设备适配层基类

每个设备族（昇腾/Jetson）继承 BaseAdapter，实现自己的检测逻辑。
适配器由 detector.py 根据设备指纹自动加载。
"""

from __future__ import annotations

import logging
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("nastool.adapter")


class ErrorCode(Enum):
    """错误码枚举"""
    # 设备识别错误 (1000-1099)
    DEVICE_NOT_FOUND = 1000
    DEVICE_UNKNOWN = 1001
    DEVICE_UNSUPPORTED = 1002

    # 工具链错误 (1100-1199)
    TOOL_NOT_FOUND = 1100
    TOOL_VERSION_MISMATCH = 1101
    TOOL_EXECUTION_FAILED = 1102

    # NPU/GPU 错误 (1200-1299)
    NPU_NOT_DETECTED = 1200
    NPU_UTILIZATION_HIGH = 1201
    NPU_TEMPERATURE_HIGH = 1202
    NPU_MEMORY_LOW = 1203
    GPU_NOT_DETECTED = 1250
    GPU_DRIVER_ERROR = 1251

    # 系统错误 (1300-1399)
    SYSTEM_MEMORY_LOW = 1300
    SYSTEM_CPU_HIGH = 1301
    SYSTEM_DISK_LOW = 1302
    SYSTEM_NETWORK_ERROR = 1303

    # 基准测试错误 (1400-1499)
    BENCHMARK_MODEL_NOT_FOUND = 1400
    BENCHMARK_FRAMEWORK_ERROR = 1401
    BENCHMARK_TIMEOUT = 1402

    # 通用错误 (1900-1999)
    UNKNOWN_ERROR = 1900
    PERMISSION_DENIED = 1901
    TIMEOUT = 1902


@dataclass
class AdapterError:
    """适配器错误"""
    code: ErrorCode
    message: str
    details: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "code": self.code.value,
            "name": self.code.name,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class AdapterResult:
    """适配器检测结果"""

    # 设备身份
    device_type: str = ""          # "ascend" / "jetson"
    device_family: str = ""         # "Atlas 200系" / "Orin AGX" 等
    device_model: str = ""         # 具体型号："Atlas 200I A2" / "Orin AGX 64GB"
    device_id: str = ""            # 唯一标识符（通常为序列号或 MAC）

    # 工具链状态
    tools: dict[str, bool] = field(default_factory=dict)  # {"npu-smi": True, "tegrastats": False}

    # NPU / GPU 状态
    npu_status: dict[str, Any] = field(default_factory=dict)
    gpu_status: dict[str, Any] = field(default_factory=dict)

    # 系统状态（通用）
    system: dict[str, Any] = field(default_factory=dict)

    # 推理基准
    benchmark: dict[str, Any] = field(default_factory=dict)

    # 健康评分
    score: int = 0                 # 0-100
    score_breakdown: dict[str, int] = field(default_factory=dict)

    # 原始输出（用于调试）
    raw_outputs: dict[str, str] = field(default_factory=dict)

    # 错误信息（结构化）
    errors: list[AdapterError] = field(default_factory=list)

    # 警告信息
    warnings: list[str] = field(default_factory=list)

    # 执行时间
    elapsed_seconds: float = 0.0

    def add_error(self, code: ErrorCode, message: str, details: Optional[str] = None) -> None:
        """添加结构化错误"""
        error = AdapterError(code=code, message=message, details=details)
        self.errors.append(error)
        logger.error(f"[{code.name}] {message}" + (f" - {details}" if details else ""))

    def add_warning(self, message: str) -> None:
        """添加警告"""
        self.warnings.append(message)
        logger.warning(message)

    def has_critical_errors(self) -> bool:
        """是否有关键错误"""
        critical_codes = {
            ErrorCode.DEVICE_NOT_FOUND,
            ErrorCode.NPU_NOT_DETECTED,
            ErrorCode.GPU_NOT_DETECTED,
        }
        return any(e.code in critical_codes for e in self.errors)

    def to_dict(self) -> dict:
        return {
            "device_type": self.device_type,
            "device_family": self.device_family,
            "device_model": self.device_model,
            "device_id": self.device_id,
            "tools": self.tools,
            "npu_status": self.npu_status,
            "gpu_status": self.gpu_status,
            "system": self.system,
            "benchmark": self.benchmark,
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "elapsed_seconds": self.elapsed_seconds,
        }


class BaseAdapter(ABC):
    """
    设备适配器基类。

    子类需要实现：
    - identify()      : 识别设备型号，返回 device_family
    - check_tools()   : 检测本族设备所需工具是否可用
    - detect_npu()    : 检测 NPU/GPU 状态（昇腾用 npu-smi，Jetson 用 tegrastats）
    - detect_system() : 通用系统检测（CPU/内存/存储/网络）
    - run_benchmark() : 推理基准测试
    - score()         : 计算健康评分
    """

    NAME: str = "base"           # 适配器名称，如 "ascend", "jetson"
    DEVICE_FAMILIES: list[str] = []  # 支持的设备族列表

    def __init__(self):
        self.result = AdapterResult()
        self.result.device_type = self.NAME

    # ------------------------------------------------------------------ #
    # 公共入口
    # ------------------------------------------------------------------ #

    def run(self) -> AdapterResult:
        """
        执行完整检测流程。
        顺序：识别型号 -> 检测工具 -> NPU/GPU -> 系统 -> 基准 -> 评分
        """
        import time
        start_time = time.perf_counter()

        try:
            self.result.device_family = self.identify()
            if not self.result.device_family:
                self.result.add_error(
                    ErrorCode.DEVICE_UNKNOWN,
                    "无法识别设备型号",
                    "设备可能是非支持的设备族，或检测工具不可用"
                )
                return self.result

            self.result.device_model = self.get_model_name()

            self.check_tools()
            self.detect_npu()
            self.detect_system()
            self.run_benchmark()
            self.calc_score()

        except PermissionError as e:
            self.result.add_error(
                ErrorCode.PERMISSION_DENIED,
                "权限不足",
                str(e)
            )
        except subprocess.TimeoutExpired as e:
            self.result.add_error(
                ErrorCode.TIMEOUT,
                "检测超时",
                str(e)
            )
        except Exception as e:
            self.result.add_error(
                ErrorCode.UNKNOWN_ERROR,
                f"适配器执行异常: {e}",
                type(e).__name__
            )
            logger.exception(f"[{self.NAME}] Unexpected error")

        finally:
            self.result.elapsed_seconds = round(time.perf_counter() - start_time, 2)

        return self.result

    # ------------------------------------------------------------------ #
    # 抽象方法（子类必须实现）
    # ------------------------------------------------------------------ #

    @abstractmethod
    def identify(self) -> str:
        """
        识别设备族。
        返回设备族名称（如 "Atlas 200系"），识别失败返回空字符串。
        """
        ...

    @abstractmethod
    def check_tools(self) -> None:
        """检测本族设备所需工具是否可用，结果写入 self.result.tools"""
        ...

    @abstractmethod
    def detect_npu(self) -> None:
        """检测 NPU/GPU 状态，结果写入 self.result.npu_status / gpu_status"""
        ...

    @abstractmethod
    def detect_system(self) -> None:
        """检测通用系统状态，结果写入 self.result.system"""
        ...

    def run_benchmark(self) -> None:
        """
        推理基准测试（可选，子类可重写）。
        默认实现为空。
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """返回具体型号名称"""
        ...

    @abstractmethod
    def calc_score(self) -> None:
        """计算健康评分，结果写入 self.result.score"""
        ...

    # ------------------------------------------------------------------ #
    # 公共工具方法
    # ------------------------------------------------------------------ #

    def _run(self, cmd: str, timeout: int = 10) -> tuple[str, str, int]:
        """
        执行 shell 命令，返回 (stdout, stderr, returncode)。
        超时或异常返回 ("", str(e), -1)。
        """
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
        except subprocess.TimeoutExpired:
            return "", "命令执行超时", -1
        except Exception as e:
            return "", str(e), -1

    def _check_command(self, cmd: str) -> bool:
        """检查命令是否存在且可执行"""
        stdout, stderr, code = self._run(f"{cmd} --version 2>&1 || {cmd} -h 2>&1 || which {cmd}", timeout=5)
        return code == 0 and stdout != ""

    @staticmethod
    def score_percent(used: float, total: float, reverse: bool = False) -> int:
        """
        将使用率转换为 0-100 分。
        reverse=True 表示使用率越低越健康（如温度）。
        """
        if total <= 0:
            return 0
        pct = used / total
        if reverse:
            pct = 1.0 - pct
        return max(0, min(100, int(pct * 100)))
