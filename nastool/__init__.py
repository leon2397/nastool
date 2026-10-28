"""
nastool — 通用 NAS 设备检测工具

不依赖任何后端、不写入被检测设备（除速度测试的临时文件），
一条命令给出：平台识别 / 硬件 / 存储与阵列 / 网络 / 服务 / AI 算力 / 健康评分。
"""

__version__ = "0.2.0"
__product__ = "nastool"
__description__ = "通用 NAS 设备检测工具"

from .core.runner import DiagnosticResult, RunOptions, run_diagnostics  # noqa: E402

__all__ = [
    "__version__",
    "DiagnosticResult",
    "RunOptions",
    "run_diagnostics",
]
