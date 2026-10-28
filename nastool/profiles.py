"""
nastool/profiles.py — 检测场景与判定阈值

同一台机器，用途不同，"健康"的定义就不同：

    nas     家庭/小型办公存储：存储最重要，服务次之，不看 AI
    verify  二手验机：安全与硬件损耗权重最高（买家关心"有没有被改过、盘还剩多久"）
    dev     开发机 / 软路由 / 虚拟化宿主：系统与网络权重高
    ai      AI 推理盒子：算力与内存权重高

profile 同时决定三件事：
    1. 检测哪些分类（active）。不在 active 里的分类，其检查项根本不执行。
    2. 哪些分类参与打分（weights）。权重为 0 的分类仍会检测、仍会展示，
       但不进总分——verify 场景下的 ai 就是这样：查出来给你看，不影响评分。
    3. 判定阈值（磁盘 80% 告警还是 90% 告警，取决于用途）。

这样就不会出现「纯存储 NAS 因为没装 PyTorch 被判不健康」这类错误结论。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Profile:
    key: str
    name: str
    description: str
    weights: Dict[str, float]          # 分类 → 权重（0 或缺省 = 不参与）
    active: List[str]                  # 参与检测的分类（顺序即报告顺序）
    thresholds: Dict[str, float] = field(default_factory=dict)

    def weight(self, category: str) -> float:
        return self.weights.get(category, 0.0)

    def score_weight_total(self) -> float:
        return sum(w for w in self.weights.values() if w > 0)

    def threshold(self, key: str, default: float = 0.0) -> float:
        return self.thresholds.get(key, default)


# 默认阈值集合（各 profile 覆盖其中一部分）
_BASE_THRESHOLDS = {
    "disk_use_warn": 80.0,       # 数据盘使用率告警
    "disk_use_crit": 90.0,       # 数据盘使用率严重
    "inode_use_warn": 90.0,
    "mem_use_warn": 85.0,
    "mem_use_crit": 95.0,
    "swap_use_warn": 50.0,
    "temp_warn": 75.0,           # 通用温度告警
    "temp_crit": 88.0,
    "link_speed_min": 1000.0,    # 低于此速率提示
    "load_per_core_warn": 1.5,
}


def _th(**overrides) -> Dict[str, float]:
    d = dict(_BASE_THRESHOLDS)
    d.update(overrides)
    return d


PROFILES: Dict[str, Profile] = {
    "nas": Profile(
        key="nas",
        name="存储服务器",
        description="家庭 / 小型办公 NAS：以数据安全与可用性为核心",
        weights={"storage": 34, "system": 16, "network": 18,
                 "services": 16, "security": 10, "usb": 6},
        active=["storage", "security", "system", "network", "services", "usb"],
        thresholds=_th(disk_use_warn=80, disk_use_crit=90,
                       temp_warn=75, temp_crit=88),
    ),
    "verify": Profile(
        key="verify",
        name="二手验机",
        description="买机器前验收：重点看硬件损耗、是否被改过、隐藏风险",
        weights={"storage": 32, "security": 18, "system": 14,
                 "network": 12, "services": 14, "usb": 6},
        active=["storage", "security", "system", "network", "services", "usb", "ai"],
        thresholds=_th(disk_use_warn=85, disk_use_crit=95,
                       mem_use_warn=90, mem_use_crit=97,
                       temp_warn=80, temp_crit=92),
    ),
    "dev": Profile(
        key="dev",
        name="开发机 / 虚拟化宿主",
        description="开发机、软路由、Proxmox 宿主：关注负载、网络与系统状态",
        weights={"system": 20, "storage": 20, "network": 18,
                 "services": 14, "security": 18, "ai": 10},
        active=["storage", "security", "system", "network", "services", "ai"],
        thresholds=_th(disk_use_warn=90, disk_use_crit=95,
                       mem_use_warn=90, mem_use_crit=97,
                       temp_warn=85, temp_crit=95),
    ),
    "ai": Profile(
        key="ai",
        name="AI 推理设备",
        description="Jetson / RK3588 / 昇腾等 AI 盒子：算力与内存是重点",
        weights={"storage": 24, "ai": 26, "system": 16,
                 "network": 14, "services": 10, "security": 10},
        active=["storage", "security", "system", "network", "services", "ai"],
        thresholds=_th(disk_use_warn=85, disk_use_crit=92,
                       mem_use_warn=85, mem_use_crit=95,
                       temp_warn=75, temp_crit=85),
    ),
}

DEFAULT_PROFILE = "nas"


def get_profile(key: str) -> Profile:
    return PROFILES.get(key) or PROFILES[DEFAULT_PROFILE]


def profile_names() -> List[str]:
    return list(PROFILES.keys())


def with_categories(profile: Profile, extra: List[str]) -> Profile:
    """
    在 profile 基础上追加分类（对应 CLI --enable ai）。
    追加的分类默认给一个保底权重，避免它计入总分时权重为 0。
    """
    if not extra:
        return profile
    active = list(profile.active)
    weights = dict(profile.weights)
    for cat in extra:
        if cat not in active:
            active.append(cat)
        if weights.get(cat, 0) <= 0:
            weights[cat] = 8.0
    return Profile(
        key=profile.key, name=profile.name, description=profile.description,
        weights=weights, active=active, thresholds=dict(profile.thresholds),
    )
