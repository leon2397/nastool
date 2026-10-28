"""
nastool/context.py — 检查上下文

所有检查项通过同一个 CheckContext 访问事实：

    def my_check(ctx):
        ctx.storage      # 第一次访问时采集，之后复用
        ctx.has("smartctl")
        ctx.threshold("disk_use_warn")

三个作用：
  1. **不重复采集**：13 个存储检查项只跑一次 df / lsblk / smartctl
  2. **失败不致命**：某个采集器崩了只返回空事实 + 记录错误，
     对应检查项会自然落到「不可判定」，而不是让整次检测失败
  3. **能力查询**：检查项用 ctx.has("smartctl") 声明依赖，
     缺依赖时引擎直接标 SKIP，不会写出「SMART 正常」这种假结论
"""
from __future__ import annotations

import shutil
from typing import Any, Callable, Dict, List, Optional

from .collect import (
    AIFacts,
    DeviceFacts,
    Facts,
    NetworkFacts,
    PlatformFacts,
    SecurityFacts,
    ServicesFacts,
    StorageFacts,
    collect_network,
    collect_security,
    collect_services,
    collect_storage,
    detect_ai_accelerator,
    detect_platform,
    get_device_info,
)
from .collect.util import IS_DARWIN, IS_LINUX, IS_WINDOWS, have, pick_default_storage_path
from .profiles import Profile


class CheckContext:
    def __init__(self, options: Any, profile: Profile):
        self.options = options
        self.profile = profile
        self._cache: Dict[str, Any] = {}
        self.collector_errors: Dict[str, str] = {}
        self.storage_path: Optional[str] = None

    # ── 惰性采集 ────────────────────────────────────────────
    def _get(self, key: str, factory: Callable, default: Callable) -> Any:
        if key not in self._cache:
            try:
                self._cache[key] = factory()
            except Exception as e:  # noqa: BLE001 - 采集失败降级为空事实
                self.collector_errors[key] = f"{type(e).__name__}: {e}"
                self._cache[key] = default()
        return self._cache[key]

    @property
    def platform(self) -> PlatformFacts:
        return self._get("platform", detect_platform, PlatformFacts)

    @property
    def device(self) -> DeviceFacts:
        return self._get("device", get_device_info, DeviceFacts)

    @property
    def resolve_storage_path(self) -> str:
        if self.storage_path is None:
            self.storage_path = (getattr(self.options, "storage_path", "") or
                                 pick_default_storage_path())
        return self.storage_path

    @property
    def storage(self) -> StorageFacts:
        return self._get(
            "storage",
            lambda: collect_storage(
                self.resolve_storage_path,
                do_speed_test=getattr(self.options, "do_speed_test", True),
                do_smart=getattr(self.options, "do_smart", True),
            ),
            StorageFacts,
        )

    @property
    def network(self) -> NetworkFacts:
        return self._get(
            "network",
            lambda: collect_network(
                peers=getattr(self.options, "peers", []),
                do_internet_check=getattr(self.options, "do_internet_check", True),
            ),
            NetworkFacts,
        )

    @property
    def services(self) -> ServicesFacts:
        return self._get("services", collect_services, ServicesFacts)

    @property
    def security(self) -> SecurityFacts:
        return self._get("security", collect_security, SecurityFacts)

    @property
    def ai(self) -> AIFacts:
        return self._get(
            "ai",
            lambda: detect_ai_accelerator(
                do_inference_test=getattr(self.options, "do_ai", True)),
            AIFacts,
        )

    # ── 能力查询 ────────────────────────────────────────────
    def has(self, capability: str) -> bool:
        """
        检查项声明的依赖能力是否满足。

        platforms  : linux / windows / macos
        privileges : root
        data       : smart_data / physical_disks / raid / docker / ssh_config / certs
        tools      : 任意命令名（smartctl / zpool / openssl ...）
        """
        cap = (capability or "").lower()
        if not cap:
            return True

        if cap == "linux":
            return IS_LINUX
        if cap == "windows":
            return IS_WINDOWS
        if cap == "macos":
            return IS_DARWIN
        if cap == "any":
            return True

        if cap == "root":
            return bool(self.platform.is_root)
        if cap == "not_container":
            return not self.platform.in_container

        if cap == "smart_data":
            return bool(self.storage.smart)
        if cap == "physical_disks":
            return bool(self.storage.physical_disks)
        if cap == "raid":
            return bool(self.storage.raids)
        if cap == "docker":
            return bool(self.services.docker_available)
        if cap == "ssh_config":
            return bool(self.security.ssh.found)
        if cap == "certs":
            return bool(self.security.certs)
        if cap == "smb_config":
            return self.security.smb_guest is not None or bool(self.security.smb_signing)
        if cap == "nfs_config":
            return self.security.nfs_no_root_squash is not None

        return have(capability)

    # ── 阈值 ────────────────────────────────────────────────
    def threshold(self, key: str, default: float = 0.0) -> float:
        return self.profile.threshold(key, default)

    # ── 平台相关的自适应阈值 ────────────────────────────────
    def chip_hint(self) -> str:
        """
        芯片类型提示，用于温度阈值自适应。

        不同 SoC 的"正常温度"差别很大：RK3588 70°C 才开始算热，
        Jetson 75°C 才需要关注，而普通 x86 CPU 65°C 就该看散热了。
        """
        chip = (self.ai.best_chip_type or "").lower()
        if chip and chip not in ("cpu", "none"):
            return chip
        model = " ".join([
            str(self.platform.facts.get("model", "")),
            str(self.device.board.model),
            str(self.device.cpu.model),
        ]).lower()
        for key in ("rk3588", "rk3568", "rk3566", "jetson", "orin", "raspberry",
                    "bcm2711", "bcm2712", "ascend", "intel-npu"):
            if key in model:
                return key
        return "generic"

    def thermal_limits(self) -> tuple:
        """返回 (告警温度, 严重温度)，按芯片类型自适应。"""
        chip = self.chip_hint()
        if chip in ("rk3588", "rk3568", "rk3566"):
            return 70.0, 82.0
        if chip in ("jetson", "orin"):
            return 75.0, 88.0
        if chip in ("raspberry", "bcm2711", "bcm2712"):
            return 70.0, 82.0
        if chip == "ascend":
            return 78.0, 90.0
        return self.threshold("temp_warn", 75.0), self.threshold("temp_crit", 88.0)

    # ── 便捷出口 ────────────────────────────────────────────
    def facts(self) -> Facts:
        """一次性把所有采集结果打包（报告展示用）。"""
        return Facts(
            platform=self.platform,
            device=self.device,
            storage=self.storage,
            network=self.network,
            services=self.services,
            security=self.security,
            ai=self.ai,
        )
