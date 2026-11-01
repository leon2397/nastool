"""
nastool/registry.py — 检查项注册表

每个检测项用 @check 声明一次，元信息（分类/权重/适用平台/依赖能力/标签）
就在这里，不再散落在评分器和三个报告器里。

这解决的是旧架构最致命的成本问题：
    旧：新增一项 = 改采集模块 + 改 scoring + 改 terminal + 改 html + 改 json
    新：新增一项 = 只写一个 @check 函数

同时，注册表让这些成为可能：
    nastool --list-checks     自解释的能力清单（也是路线图）
    nastool --only storage.*  只跑某类
    nastool --skip ai.*       跳过某类
    按 profile 自动裁剪范围
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from .model import CATEGORY_ORDER, FIX_RISK_DEFAULT, FIX_RISK_ORDER, PRIORITY_DEFAULT


@dataclass
class CheckMeta:
    id: str
    title: str
    category: str
    weight: float = 1.0
    function: Optional[Callable] = None
    platforms: Sequence[str] = ()      # 适用平台：linux / windows / macos / any
    requires: Sequence[str] = ()       # 依赖能力：smartctl / root / docker ...
    tags: Sequence[str] = ()           # 标签：nas / verify / slow / ai（元数据，暂不参与筛选）
    description: str = ""
    priority: int = PRIORITY_DEFAULT   # 0–3：出问题时这件事多急（DEBT-002）
    fix_risk: str = FIX_RISK_DEFAULT   # 低/中/高：修它本身的风险

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "weight": self.weight,
            "platforms": list(self.platforms),
            "requires": list(self.requires),
            "tags": list(self.tags),
            "description": self.description,
            "priority": self.priority,
            "fix_risk": self.fix_risk,
        }


_REGISTRY: Dict[str, CheckMeta] = {}


class RegistryError(RuntimeError):
    pass


def check(id: str, title: str, category: str, weight: float = 1.0,
          platforms: Sequence[str] = (), requires: Sequence[str] = (),
          tags: Sequence[str] = (), description: str = "",
          priority: int = PRIORITY_DEFAULT,
          fix_risk: str = FIX_RISK_DEFAULT) -> Callable:
    """
    注册一个检查项。

        @check("storage.smart_health", "硬盘 SMART 健康", "storage",
               weight=4, requires=["smartctl"], tags=["nas", "verify"],
               priority=3, fix_risk="中")
        def check_smart_health(ctx) -> CheckResult:
            ...

    `priority` 与 `fix_risk` 只有出问题（WARN/FAIL）时才被消费，它们决定
    行动计划里这一项排第几、以及要不要提醒"这一步有风险"。
    """
    if category not in CATEGORY_ORDER:
        raise RegistryError(f"未知分类 {category!r}（允许：{', '.join(CATEGORY_ORDER)}）")
    # 参数非法就在导入时炸掉，不留到报告里——
    # 打错成 priority=5 或 fix_risk="low" 会静默产出无法排序的清单
    if priority not in (0, 1, 2, 3):
        raise RegistryError(f"{id}: priority 必须是 0–3，收到 {priority!r}")
    if fix_risk not in FIX_RISK_ORDER:
        raise RegistryError(
            f"{id}: fix_risk 必须是 {'/'.join(FIX_RISK_ORDER)}，收到 {fix_risk!r}")

    def deco(fn: Callable) -> Callable:
        if id in _REGISTRY:
            raise RegistryError(f"检查项 id 重复：{id}")
        _REGISTRY[id] = CheckMeta(
            id=id, title=title, category=category, weight=weight,
            function=fn, platforms=tuple(platforms), requires=tuple(requires),
            tags=tuple(tags), description=description,
            priority=priority, fix_risk=fix_risk,
        )
        return fn

    return deco


def all_meta() -> List[CheckMeta]:
    """按分类顺序返回全部已注册检查项（不含执行）。"""
    def sort_key(m: CheckMeta):
        idx = CATEGORY_ORDER.index(m.category) if m.category in CATEGORY_ORDER else 99
        return (idx, m.id)
    return sorted(_REGISTRY.values(), key=sort_key)


def get(check_id: str) -> Optional[CheckMeta]:
    return _REGISTRY.get(check_id)


def _match_any(check_id: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(check_id, p) for p in patterns)


def resolve(only: Sequence[str] = (), skip: Sequence[str] = (),
            categories: Optional[Sequence[str]] = None) -> List[CheckMeta]:
    """
    按 --only / --skip / profile 分类 过滤出本次要跑的检查项。

    only/skip 支持通配：storage.* / *.smart_* / network.peer_reach
    """
    metas = all_meta()
    if only:
        metas = [m for m in metas if _match_any(m.id, only)]
    if skip:
        metas = [m for m in metas if not _match_any(m.id, skip)]
    if categories is not None:
        allowed = set(categories)
        metas = [m for m in metas if m.category in allowed]
    return metas


def count_by_category() -> Dict[str, int]:
    out: Dict[str, int] = {}
    for m in _REGISTRY.values():
        out[m.category] = out.get(m.category, 0) + 1
    return out
