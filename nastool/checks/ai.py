"""
checks/ai.py — AI 算力

这是 nastool 相对通用检测工具的差异化能力，但定位保持克制：

  · **AI 不是合格线。** 纯存储 NAS 没有加速器完全正常，标 SKIP 而不是 FAIL。
  · 只有 profile=ai（AI 推理设备）时，缺加速器才算 FAIL。
  · 有硬件但推理引擎不可用才是真正需要处理的 WARN。
"""
from __future__ import annotations

import os

from ..collect.util import read_file
from ..model import Status
from ..registry import check
from ._base import R, ev


@check("ai.hardware", "AI 加速硬件", "ai", weight=3,
       platforms=["any"], tags=["ai", "verify"])
def hardware(ctx):
    ai = ctx.ai
    if ai.hardware_accelerated:
        names = "、".join(f"{d.name}" for d in ai.devices
                          if d.chip_type != "cpu")[:80]
        return R(Status.PASS, f"检测到加速硬件：{names or ai.best_chip_type}",
                 evidence=[ev("芯片探测", d.chip_type, d.name,
                              note=d.detected_by) for d in ai.devices[:6]],
                 confidence=0.95)

    # AI 推理设备场景下，没有加速器才是问题
    if ctx.profile.key == "ai":
        return R(Status.FAIL, "未检测到 AI 加速硬件",
                 detail="当前使用 ai 场景，预期这台机器应具备 NPU / GPU 加速能力",
                 suggestion="确认驱动是否加载；或改用 --profile nas 按纯存储标准评估",
                 confidence=0.9)

    return R(Status.SKIP, "未检测到 AI 加速硬件",
             detail="纯存储 / 文件服务用途无需 AI 算力，此项不计入健康评分")


@check("ai.runtime", "推理运行时", "ai", weight=2,
       platforms=["any"], tags=["ai"])
def runtime(ctx):
    ai = ctx.ai
    if not ai.hardware_accelerated:
        return R(Status.SKIP, "无加速硬件，跳过推理运行时检测")
    if not ai.inference_tested:
        return R(Status.SKIP, "已跳过推理测试（--no-ai）")

    if ai.inference_available:
        return R(Status.PASS, f"推理可用（{ai.inference_engine}）",
                 evidence=[ev("推理测试", "engine", ai.inference_engine)],
                 confidence=0.9)

    return R(Status.WARN, "有加速硬件，但没有可用的推理引擎",
             detail="常见原因：PyTorch/ONNX Runtime 未安装、安装的是 CPU 版本、"
                    "CUDA/ROCm 驱动版本不匹配",
             suggestion="按芯片厂商文档安装对应运行时；用 python -c \"import torch\" 快速验证",
             evidence=[ev("推理测试", "available", False)],
             confidence=0.85)


@check("ai.inference_perf", "推理性能", "ai", weight=2,
       platforms=["any"], tags=["ai", "slow"])
def inference_perf(ctx):
    ai = ctx.ai
    if not ai.inference_available or not ai.inference_test_ms:
        return R(Status.SKIP, "没有推理耗时数据")

    ms = ai.inference_test_ms
    evidence = [ev("推理测试", "elapsed_ms", ms, num=ms),
                ev("推理测试", "engine", ai.inference_engine)]

    if ms >= 5000:
        return R(Status.WARN, f"单次推理 {ms:.0f} ms，明显偏慢",
                 detail="可能是驱动回退到 CPU 执行，或模型过大",
                 suggestion="确认是否真的走了加速器：torch.cuda.is_available() / "
                            "rknn 日志中是否有 NPU 字样",
                 evidence=evidence)
    return R(Status.PASS, f"单次推理 {ms:.0f} ms（{ai.inference_engine}）",
             evidence=evidence, confidence=0.85)


@check("ai.vendor_env", "厂商运行环境", "ai", weight=1,
       platforms=["linux"], tags=["ai"])
def vendor_env(ctx):
    hints = []
    if read_file("/etc/nv_tegra_release"):
        hints.append(("Jetson", "/etc/nv_tegra_release",
                      read_file("/etc/nv_tegra_release").splitlines()[0][:60]))
    model = read_file("/proc/device-tree/model").replace("\x00", "").strip()
    if "rockchip" in model.lower() or os.path.exists("/dev/rknpu"):
        hints.append(("Rockchip", "/proc/device-tree/model", model or "RK 平台"))
    if read_file("/usr/local/Ascend/version.info"):
        hints.append(("Ascend", "/usr/local/Ascend/version.info", "Ascend 环境已安装"))

    if not hints:
        return R(Status.SKIP, "未检测到厂商专用运行环境",
                 detail="通用 x86 / ARM 平台无需此项")

    return R(Status.PASS, "、".join(h[0] for h in hints),
             evidence=[ev(src, f"{name}.env", val) for name, src, val in hints],
             confidence=0.9)
