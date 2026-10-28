"""
nastool — 通用 NAS 设备检测工具

不依赖任何后端、不修改被检测设备（除测速时写入并立即删除的临时文件），
一条命令给出：平台识别 / 硬件 / 存储与阵列 / 网络 / 服务 / 安全 / AI 算力，
并以「分数 + 覆盖度 + 置信度 + 证据」的形式交付结论。

架构（对外只需要记住这四个名字）：

    run(options)        → Report        执行检测
    Report.checks       → CheckResult   逐项结论（带证据与置信度）
    Report.score        → Score         分数 / 等级 / 分类得分
    JSONReporter()      → dict          稳定序列化，供上报与历史

新增检测项只需在 nastool/checks/ 下加一个 @check 函数，其余层无需改动。
"""

__version__ = "0.4.0"
__product__ = "nastool"
__description__ = "通用 NAS 设备检测工具"

from .engine import RunOptions, run  # noqa: E402
from .model import (  # noqa: E402
    REPORT_VERSION,
    CheckResult,
    Evidence,
    Report,
    Score,
    Status,
)

__all__ = [
    "__version__",
    "REPORT_VERSION",
    "RunOptions",
    "run",
    "Report",
    "CheckResult",
    "Evidence",
    "Score",
    "Status",
]
