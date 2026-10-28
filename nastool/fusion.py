"""
nastool/fusion.py — 多源数据融合与一致性验证

**为什么需要这个模块**

同一个事实往往有多个来源。当多个来源给出**不同**的答案时，
「随便取一个」会产生错误结论。真实案例：某些 ARM 板子的 hwmon 只报
SoC 上某一点温度，而 thermal_zone 报的是整机热点，两者可以差 15°C——
取哪个直接决定「是否告警」。用户从报告里看不出「这个温度可能有争议」。

本模块提供两个能力：

1. **融合**（fuse）：把多个来源的同名字段合成一个值 + 置信度
2. **一致性验证**（validate）：判断多个来源是否互相矛盾

**分层约束（ADR-0002）**

本模块**只做数值运算，不做「好还是坏」的判断**——它不知道什么叫
「温度过高」，只知道「两个来源差了 12°C，超过容差」。
把结果翻译成 PASS / WARN / FAIL 是 `checks/` 的职责。

采集层保留全部来源是「事实的完整性」，不是判断，因此不违反 ADR-0002。

**四种融合方法**

| 方法 | 适用场景 |
|---|---|
| `WEIGHTED_AVERAGE` | 连续量，各来源可信度不同（默认） |
| `MEDIAN` | 有个别来源离群时更稳 |
| `MAJORITY_VOTE` | 离散量（枚举、布尔），取多数 |
| `TRUSTED_SOURCE` | 有明确权威来源时（如系统 API 优先于 sysfs） |
| `MAX` | **安全保守**场景：温度、容量、错误数——取最坏值而非平均值 |

> `MAX` 与平均值的区别不是精度问题，而是**语义问题**。
> 把 SoC 的 45°C 和热点的 60°C 平均成 52.5°C，会让"是否过热"的判断
> 偏离真实风险。温度这类"取最高才安全"的量必须用 MAX。

**与前身项目的关系**

前身 v7.1.0-beta 有一个 `DataFusionEngine` + `ConsistencyValidator`，
但**代码内核已丢失**，只剩 API 文档。这里按其规格重写，
并补上前身没有的三件事：容差可配、融合方法可插拔、纯函数可单测。
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence

__all__ = [
    "FusionMethod",
    "SourceValue",
    "FusionResult",
    "ConsistencyResult",
    "fuse",
    "validate",
    "normalize_point",
    "default_tolerance",
    "DEFAULT_TOLERANCE",
]


# ── 融合方法 ────────────────────────────────────────────────
class FusionMethod(Enum):
    """多源融合算法。"""

    WEIGHTED_AVERAGE = "weighted_average"
    MEDIAN = "median"
    MAJORITY_VOTE = "majority_vote"
    TRUSTED_SOURCE = "trusted_source"
    MAX = "max"


# ── 默认容差表 ──────────────────────────────────────────────
# 容差是「两个来源差多少算矛盾」。按被测量纲给，不同量纲不能共用一个值。
# 温度差 5°C 通常是测量点不同（SoC vs 热点），不算故障；差 15°C 才是真分歧。
DEFAULT_TOLERANCE: Dict[str, float] = {
    "temperature_c": 5.0,     # 摄氏度
    "temp_c": 5.0,
    "use_percent": 2.0,       # 百分点
    "free_gb": 1.0,
    "total_gb": 1.0,
    "power_on_hours": 24.0,   # 通电时长的读数差异不算矛盾
    "capacity_gb": 1.0,
    "rtt_ms": 50.0,
    "speed_mbps": 10.0,
}


def default_tolerance(key: str) -> float:
    """取某个字段的默认容差；未登记的字段用 0（严格相等）。"""
    return DEFAULT_TOLERANCE.get(key, 0.0)


# ── 测量点归一化 ────────────────────────────────────────────
# 不同来源对同一物理位置的叫法不同：
#   hwmon 的 label      "cpu" / "soc" / "cpuvid" / "temp1"
#   thermal_zone 的 type "cpu-thermal" / "soc-thermal" / "x86_pkg_temp"
# 只有归一化到同一个「测量点」后，两个来源的读数才可比。
# 归一化错了的代价：把「CPU 45°C + GPU 70°C」误判成「数据矛盾」。

_POINT_ALIASES = {
    "cpu": "cpu", "soc": "cpu", "cpuid": "cpu", "cpuvid": "cpu",
    "cpu_thermal": "cpu", "soc_thermal": "cpu", "x86_pkg_temp": "cpu",
    "x86_soc": "cpu", "package_id_0": "cpu", "tdie": "cpu",
    "gpu": "gpu", "gpu_thermal": "gpu",
    "acpitz": "acpi", "acpi": "acpi",
    "nvme": "disk", "disk": "disk", "composite": "disk",
    "memory": "memory", "ddr": "memory",
    "pwm": "fan", "fan": "fan",
    "wifi": "wifi", "wlan": "wifi",
    "tdie": "cpu",
}


def normalize_point(raw: str) -> str:
    """
    把测量点名称归一化。

    "cpu-thermal" / "soc_thermal" / "CPU" → "cpu"
    无法识别时返回清洗后的原名（去掉常见前后缀）。
    """
    if not raw:
        return ""
    key = raw.strip().lower().replace(" ", "_")
    # 先剥掉常见后缀再查别名
    stripped = key
    for suffix in ("_input", "_temp", "-thermal", "_thermal", "_thermal_zone"):
        if stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)]
            break
    if stripped in _POINT_ALIASES:
        return _POINT_ALIASES[stripped]
    if key in _POINT_ALIASES:
        return _POINT_ALIASES[key]
    return stripped or key


# ── 输入契约 ────────────────────────────────────────────────
@dataclass
class SourceValue:
    """单个来源的一次读数。"""

    source: str                       # 来源标识，如 "hwmon" / "thermal_zone"
    value: float                     # 数值
    weight: float = 1.0              # 该来源的相对可信度
    trusted: bool = False             # 是否为权威来源（TRUSTED_SOURCE 用）
    note: str = ""                   # 补充说明，进报告
    available: bool = True           # False 表示该来源读到了但不可用

    @property
    def usable(self) -> bool:
        return self.available and self.value is not None


@dataclass
class FusionResult:
    """融合结果。"""

    value: Optional[float] = None
    method: str = ""
    confidence: float = 0.0
    sources_used: List[str] = field(default_factory=list)
    sources_ignored: List[str] = field(default_factory=list)
    spread: Optional[float] = None      # 参与融合的值之间的极差
    note: str = ""

    @property
    def ok(self) -> bool:
        return self.value is not None


@dataclass
class ConsistencyResult:
    """一致性验证结果。"""

    consistent: bool = True
    tolerance: float = 0.0
    spread: Optional[float] = None          # 极差
    deviation: Optional[float] = None       # 偏离中位数的最大距离
    values: Dict[str, float] = field(default_factory=dict)
    outliers: List[str] = field(default_factory=list)
    note: str = ""

    def summary(self) -> str:
        if self.consistent:
            if len(self.values) < 2:
                return "单一来源，无从比较"
            return f"各来源一致（极差 {self.spread:.1f}，容差 {self.tolerance:.1f}）"
        detail = "、".join(
            f"{s}={self.values[s]:g}" for s in sorted(self.values))
        return f"来源读数不一致（{detail}），极差 {self.spread:.1f} > 容差 {self.tolerance:.1f}"


# ── 融合 ────────────────────────────────────────────────────
def fuse(values: Sequence[SourceValue],
          method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE,
          tolerance: Optional[float] = None) -> FusionResult:
    """
    把多个来源的同名字段融合成一个值。

    参数
    ----
    values        各来源读数
    method        融合方法
    tolerance     容差；None 表示按字段名查默认表（此处不适用，由调用方决定）

    返回
    ----
    FusionResult，value 为 None 表示没有可用来源。
    """
    usable = [v for v in values if v.usable]
    ignored = [v.source for v in values if not v.usable]

    if not usable:
        return FusionResult(method=method.value, sources_ignored=ignored,
                            note="没有可用来源")

    names = [v.source for v in usable]
    nums = [v.value for v in usable]

    # 极差：参与融合的值之间的最大差距
    spread = (max(nums) - min(nums)) if len(nums) > 1 else 0.0

    if len(usable) == 1:
        only = usable[0]
        return FusionResult(
            value=only.value, method=method.value, confidence=0.7,
            sources_used=names, sources_ignored=ignored, spread=0.0,
            note="单一来源")

    if method is FusionMethod.MEDIAN:
        value = statistics.median(nums)
    elif method is FusionMethod.MAJORITY_VOTE:
        value = _majority_vote(usable)
    elif method is FusionMethod.TRUSTED_SOURCE:
        value = _trusted(usable)
    elif method is FusionMethod.MAX:
        value = max(nums)
    else:  # WEIGHTED_AVERAGE
        value = _weighted_average(usable)

    confidence = _confidence(usable, spread, tolerance)

    return FusionResult(
        value=value, method=method.value, confidence=confidence,
        sources_used=names, sources_ignored=ignored, spread=spread,
    )


def _weighted_average(values: List[SourceValue]) -> float:
    total_w = sum(v.weight for v in values) or 1.0
    return sum(v.value * v.weight for v in values) / total_w


def _majority_vote(values: List[SourceValue]) -> float:
    """离散量：取出现次数最多的值；并列时取权重和最大的那个。"""
    counts: Dict[float, int] = {}
    for v in values:
        counts[v.value] = counts.get(v.value, 0) + 1
    best = max(counts.items(), key=lambda kv: (kv[1], sum(
        v.weight for v in values if v.value == kv[0])))
    return best[0]


def _trusted(values: List[SourceValue]) -> float:
    """权威优先：多个 trusted 时按权重平均；没有 trusted 时退回加权平均。"""
    trusted = [v for v in values if v.trusted]
    pool = trusted if trusted else values
    return _weighted_average(pool)


def _confidence(values: List[SourceValue], spread: float,
                tolerance: Optional[float]) -> float:
    """
    置信度：来源越多、彼此越接近，越可信。

    这是**相对**置信度（相对于本次融合自身），不是绝对可信度——
    「两个来源一致」不等于「两个来源都准」。
    """
    base = min(0.98, 0.55 + 0.15 * len(values))
    if tolerance is not None and tolerance > 0:
        if spread > tolerance:
            # 超出容差：按超出比例线性衰减，最低 0.2
            excess = (spread - tolerance) / tolerance
            base *= max(0.2, 1.0 - min(1.0, excess) * 0.6)
    return round(max(0.0, min(1.0, base)), 3)


# ── 一致性验证 ──────────────────────────────────────────────
def validate(values: Sequence[SourceValue],
             tolerance: Optional[float] = None,
             key: str = "") -> ConsistencyResult:
    """
    验证多个来源是否互相矛盾。

    判定规则：极差（max - min）超过容差即视为不一致。

    参数
    ----
    values      各来源读数
    tolerance   容差；None 时按 key 查默认表
    key         字段名，用于查默认容差
    """
    usable = [v for v in values if v.usable]
    if tolerance is None:
        tolerance = default_tolerance(key)

    if not usable:
        return ConsistencyResult(consistent=True, tolerance=tolerance,
                                 note="没有可用来源")

    if len(usable) == 1:
        return ConsistencyResult(consistent=True, tolerance=tolerance,
                                 spread=0.0, deviation=0.0,
                                 values={usable[0].source: usable[0].value},
                                 note="单一来源，无从比较")

    nums = [v.value for v in usable]
    spread = max(nums) - min(nums)
    med = statistics.median(nums)
    deviation = max(abs(v - med) for v in nums)

    mapping = {v.source: v.value for v in usable}
    consistent = spread <= tolerance

    outliers = []
    if not consistent and len(usable) >= 3:
        # 偏离中位数超过一半容差的来源视为离群。
        # 少于 3 个来源时**不判离群**——两个来源各执一词时，
        # 没有第三个参照，无法认定谁是错的，只能说「两者不一致」。
        for v in usable:
            if abs(v.value - med) > tolerance / 2:
                outliers.append(v.source)

    note = ""
    if not consistent:
        note = "各来源读数分歧，可能测量点不同或其中一路数据不可靠"

    return ConsistencyResult(
        consistent=consistent, tolerance=tolerance, spread=round(spread, 3),
        deviation=round(deviation, 3), values=mapping, outliers=outliers,
        note=note,
    )
