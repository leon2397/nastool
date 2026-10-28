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

from .model import CATEGORY_ORDER


@dataclass
class CheckMeta:
    id: str
    title: str
    category: str
    weight: float = 1.0
    function: Optional[Callable] = None
    platforms: Sequence[str] = ()      # 适用平台：linux / windows / macos / any
    requires: Sequence[str] = ()       # 依赖能力：smartctl / root / docker ...
    tags: Sequence[str] = ()           # 标签：nas / verify / slow / ai
    description: str = ""

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
        }


_REGISTRY: Dict[str, CheckMeta] = {}


class RegistryError(RuntimeError):
    pass


def check(id: str, title: str, category: str, weight: float = 1.0,
          platforms: Sequence[str] = (), requires: Sequence[str] = (),
          tags: Sequence[str] = (), description: str = "") -> Callable:
    """
    注册一个检查项。

        @check("storage.smart_health", "硬盘 SMART 健康", "storage",
               weight=4, requires=["smartctl"], tags=["nas", "verify"])
        def check_smart_health(ctx) -> CheckResult:
            ...
    """
    if category not in CATEGORY_ORDER:
        raise RegistryError(f"未知分类 {category!r}（允许：{', '.join(CATEGORY_ORDER)}）")

    def deco(fn: Callable) -> Callable:
        if id in _REGISTRY:
            raise RegistryError(f"检查项 id 重复：{id}")
        _REGISTRY[id] = CheckMeta(
            id=id, title=title, category=category, weight=weight,
            function=fn, platforms=tuple(platforms), requires=tuple(requires),
            tags=tuple(tags), description=description,
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
