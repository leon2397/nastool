"""
core/runner.py — 诊断编排

把各采集模块串起来，产出唯一的 DiagnosticResult。
报告器（terminal / json / html）只依赖这个对象，不再各自拼装数据。
"""
import datetime
import platform
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .. import __version__
from .ai_accel import AIReport, detect_ai_accelerator
from .device import DeviceReport, get_device_info
from .network import NetworkReport, check_network
from .platform_detect import PlatformReport, detect_platform
from .scoring import ScoreReport, compute_score
from .services import ServicesReport, detect_services
from .storage import StorageReport, check_storage
from .util import pick_default_storage_path


@dataclass
class RunOptions:
    storage_path: str = ""
    peers: List[str] = field(default_factory=list)
    do_speed_test: bool = True
    do_smart: bool = True
    do_ai: bool = True
    do_internet_check: bool = True
    verbose: bool = False


@dataclass
class ReportMeta:
    tool: str = "nastool"
    version: str = __version__
    generated_at: str = ""
    duration_s: float = 0.0
    hostname: str = ""
    python: str = ""
    platform_summary: str = ""
    options: dict = field(default_factory=dict)


@dataclass
class DiagnosticResult:
    meta: ReportMeta = field(default_factory=ReportMeta)
    platform: PlatformReport = field(default_factory=PlatformReport)
    device: DeviceReport = field(default_factory=DeviceReport)
    storage: StorageReport = field(default_factory=StorageReport)
    network: NetworkReport = field(default_factory=NetworkReport)
    services: ServicesReport = field(default_factory=ServicesReport)
    ai: AIReport = field(default_factory=AIReport)
    adapter: object = None
    score: ScoreReport = field(default_factory=ScoreReport)
    overall_ok: bool = False

    def critical_findings(self) -> list:
        return [f for f in self.score.findings if f.level == "critical"]

    def summary_line(self) -> str:
        return (f"{self.score.total} 分 / {self.score.grade} 级 · "
                f"严重 {len(self.critical_findings())} 项 · "
                f"告警 {len([f for f in self.score.findings if f.level == 'warning'])} 项")


def _noop(_msg: str) -> None:
    pass


def run_diagnostics(options: Optional[RunOptions] = None,
                    progress: Optional[Callable[[str], None]] = None) -> DiagnosticResult:
    """
    执行一次完整诊断。
    progress: 进度回调（CLI 用来打印步骤），默认静默。
    """
    opts = options or RunOptions()
    step = progress or _noop

    t0 = time.time()
    result = DiagnosticResult()
    result.meta = ReportMeta(
        generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        hostname=platform.node(),
        python=platform.python_version(),
        platform_summary=platform.platform(terse=True),
        options={
            "storage_path": opts.storage_path,
            "peers": opts.peers,
            "speed_test": opts.do_speed_test,
            "smart": opts.do_smart,
            "ai": opts.do_ai,
        },
    )

    # 1. 平台
    step("识别系统平台...")
    try:
        result.platform = detect_platform()
    except Exception as e:  # noqa: BLE001
        result.platform.warnings.append(f"平台识别失败: {e}")

    # 2. 设备
    step("采集设备信息...")
    try:
        result.device = get_device_info()
    except Exception as e:  # noqa: BLE001
        result.device.errors.append(str(e))

    # 3. 存储
    storage_path = opts.storage_path or pick_default_storage_path()
    result.meta.options["storage_path"] = storage_path
    step(f"检测存储（{storage_path}）...")
    try:
        result.storage = check_storage(
            storage_path,
            do_speed_test=opts.do_speed_test,
            do_smart=opts.do_smart,
        )
    except Exception as e:  # noqa: BLE001
        result.storage.errors.append(str(e))

    # 4. 网络
    step("检查网络...")
    try:
        result.network = check_network(
            peers=opts.peers, do_internet_check=opts.do_internet_check)
    except Exception as e:  # noqa: BLE001
        result.network.errors.append(str(e))

    # 5. 服务
    step("探测运行中的服务...")
    try:
        result.services = detect_services()
    except Exception as e:  # noqa: BLE001
        result.services.warnings.append(f"服务探测失败: {e}")

    # 6. AI 算力（可选）
    step("检测 AI 算力...")
    try:
        result.ai = detect_ai_accelerator(do_inference_test=opts.do_ai)
    except Exception as e:  # noqa: BLE001
        result.ai.errors.append(str(e))

    # 7. 厂商适配检查
    try:
        from ..adapters import get_adapter
        adapter = get_adapter(result.ai.best_chip_type)
        result.adapter = adapter.health_check()
    except Exception:  # noqa: BLE001
        result.adapter = None

    # 8. 评分
    result.score = compute_score(
        result.device, result.storage, result.network,
        result.services, result.platform, result.ai,
    )

    result.meta.duration_s = round(time.time() - t0, 1)
    result.overall_ok = (
        result.device.ok
        and result.storage.ok
        and result.network.ok
        and not result.critical_findings()
    )
    return result
