# -*- coding: utf-8 -*-
"""
checks/ai/version_checker.py - AI 组件版本检测

已迁移到 @check() 装饰器（Phase A 补完）。

结构：
  - AIVersionCheck：基类（复杂逻辑保留 class）
  - 8 个具体子类：已改为 @check(class_name="XxxVersionCheck") 装饰
  - _check_version_helper()：模块级版本比对，供函数式 check 调用
"""

from __future__ import annotations

import re
from typing import Optional, TYPE_CHECKING

from nastool_core.checks.base import CheckCategory, CheckResult, CheckSeverity
from nastool_core.checks.decorators import check

if TYPE_CHECKING:
    from nastool_core.checks.base import CheckContext

# ── VersionDB 单例（模块级，避免每次实例化）────────────────────────────────────
# VersionDB 已移除，版本检测使用本地比对逻辑
_version_db_instance = None


def _get_version_db():
    """懒加载 VersionDB 单例（已弃用，始终返回 None）"""
    return None


# ── 版本比对 helper（函数式 check 调用）────────────────────────────────────────

def _cmd_exists(cmd: str) -> bool:
    import subprocess
    try:
        subprocess.run(f"which {cmd}", shell=True,
                       capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def _run_cmd(cmd: str) -> str:
    import subprocess
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True,
                               text=True, timeout=10)
        return result.stdout + result.stderr
    except Exception:
        return ""


def _compare_versions(current: str, latest: str) -> int:
    """Compare versions. Returns -1/0/1 (lt/eq/gt)."""
    def parse(v: str) -> tuple:
        parts = re.sub(r"[^\d.]", "", v).split(".")
        return tuple(int(p) for p in parts if p)
    try:
        c, l = parse(current), parse(latest)
        # Pad to same length
        max_len = max(len(c), len(l))
        c = c + (0,) * (max_len - len(c))
        l = l + (0,) * (max_len - len(l))
        if c < l:
            return -1
        elif c > l:
            return 1
        return 0
    except Exception:
        return 0


def _check_version_helper(
    ctx: "CheckContext",
    check_id: str,
    title: str,
    current: str,
    component: str,
    device_model: Optional[str] = None,
) -> CheckResult:
    """
    版本比对核心逻辑（AIVersionCheck._check_version 的函数版本）。
    供所有函数式 check 调用。
    """
    vdb = _get_version_db()
    if vdb is None:
        return ctx.result(
            passed=True, current=current, expected="unknown",
            message=f"{title} {current} installed (version DB unavailable)",
            details={"component": component, "current": current},
        )

    version_info = vdb.get_version(component)
    if not version_info:
        return ctx.result(
            passed=True, current=current, expected="unknown",
            message=f"{title} {current} (version database not available)",
            details={"component": component},
        )

    latest = version_info.latest
    min_recommended = version_info.min_recommended

    # Device compatibility cap
    max_version = None
    if device_model and version_info.compatibility:
        compat = version_info.compatibility.get(device_model, {})
        max_version = compat.get("max")

    cmp_latest = _compare_versions(current, latest)
    cmp_min = _compare_versions(current, min_recommended)

    if cmp_min < 0:
        severity = CheckSeverity.CRITICAL
        passed = False
        message = f"{component} {current} below minimum recommended {min_recommended}"
    elif cmp_latest < 0:
        severity = CheckSeverity.WARNING
        passed = True
        message = f"{component} {current} -- upgrade to {latest} available"
    else:
        severity = CheckSeverity.PASSED
        passed = True
        message = f"{component} {current} is up to date"

    if max_version and _compare_versions(current, max_version) > 0:
        severity = CheckSeverity.WARNING
        message = (f"{component} {current} may not be fully compatible with "
                   f"{device_model} (max: {max_version})")

    return ctx.result(
        passed=passed, current=current,
        expected=f">= {min_recommended}",
        message=message,
        severity=severity,
        fix_available=cmp_latest < 0,
        fix_description=f"Upgrade {component} to {latest}",
        fix_risk="medium",
        details={
            "latest": latest,
            "min_recommended": min_recommended,
            "release_notes": getattr(version_info, "release_notes", ""),
            "release_date": getattr(version_info, "release_date", ""),
        },
    )


# ── Check 函数（@check 装饰）──────────────────────────────────────────────────

@check(id="nvidia_driver_version", class_name="NvidiaDriverVersionCheck",
       category="AI", title="NVIDIA Driver Version",
       description="检查 NVIDIA 驱动是否为最新版本")
def nvidia_driver_version(ctx: "CheckContext"):
    """检测 NVIDIA 驱动版本"""
    if not _cmd_exists("nvidia-smi"):
        return ctx.result(
            passed=True, current="not installed", expected="installed",
            message="NVIDIA driver not detected",
            severity=CheckSeverity.INFO,
        )
    output = _run_cmd(
        "nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1"
    )
    if not output.strip():
        output = _run_cmd(
            "nvidia-smi 2>/dev/null | grep 'Driver Version' | awk '{print $6}'"
        )
    current = output.strip() if output.strip() else "unknown"
    if current == "unknown":
        return ctx.result(
            passed=True, current="unknown", expected="detectable",
            message="NVIDIA driver installed but version undetermined",
            severity=CheckSeverity.WARNING,
        )
    return _check_version_helper(
        ctx, "nvidia_driver_version", "NVIDIA Driver", current, "nvidia_driver"
    )


@check(id="cuda_version", class_name="CudaVersionCheck",
       category="AI", title="CUDA Version",
       description="检查 CUDA 是否安装且为最新版本")
def cuda_version(ctx: "CheckContext"):
    """检测 CUDA 版本"""
    if not _cmd_exists("nvcc"):
        return ctx.result(
            passed=True, current="not installed", expected="installed",
            message="CUDA toolkit not detected (nvcc not found)",
            severity=CheckSeverity.INFO,
        )
    output = _run_cmd("nvcc --version 2>/dev/null | grep 'release' | awk '{print $5}' | tr -d ','")
    current = output.strip() if output.strip() else "unknown"
    if current == "unknown":
        output = _run_cmd("cat /usr/local/cuda/version.txt 2>/dev/null | awk '{print $3}'")
        current = output.strip() if output.strip() else "unknown"
    return _check_version_helper(
        ctx, "cuda_version", "CUDA", current, "cuda"
    )


@check(id="tensorrt_version", class_name="TensorRTVersionCheck",
       category="AI", title="TensorRT Version",
       description="检查 TensorRT 是否安装且为最新版本")
def tensorrt_version(ctx: "CheckContext"):
    """检测 TensorRT 版本"""
    current = "not installed"
    try:
        import tensorrt
        current = tensorrt.__version__
    except ImportError:
        output = _run_cmd("trtexec --version 2>/dev/null | head -1")
        if output:
            match = re.search(r"(\d+\.\d+\.\d+)", output)
            if match:
                current = match.group(1)
        if current == "not installed":
            return ctx.result(
                passed=True, current="not installed", expected="installed",
                message="TensorRT not detected",
                severity=CheckSeverity.INFO,
            )
    return _check_version_helper(
        ctx, "tensorrt_version", "TensorRT", current, "tensorrt"
    )


@check(id="jetpack_version", class_name="JetPackVersionCheck",
       category="AI", title="JetPack Version",
       description="检查 NVIDIA Jetson 设备的 JetPack 版本")
def jetpack_version(ctx: "CheckContext"):
    """检测 JetPack 版本（Jetson 设备）"""
    jetson_model = ""
    try:
        with open("/proc/device-tree/model", "r") as f:
            jetson_model = f.read().strip().lower()
    except Exception:
        pass

    if "jetson" not in jetson_model:
        return ctx.result(
            passed=True, current="n/a", expected="n/a",
            message="Not a Jetson device",
            severity=CheckSeverity.INFO,
        )

    current = "unknown"

    # Method 1: jetson-release
    output = _run_cmd("jetson-release 2>/dev/null | grep 'JetPack' | awk '{print $2}'")
    if output.strip():
        current = output.strip()
    else:
        output = _run_cmd("cat /etc/nv_tegra_release 2>/dev/null | head -1")
        if output:
            l4t_to_jp = {
                "35.1": "5.0.2", "35.2": "5.1", "35.3": "5.1.1",
                "35.4": "5.1.2", "35.5": "5.1.3",
                "36.2": "6.0",   "36.3": "6.1",   "36.4": "6.2",
            }
            for l4t, jp in l4t_to_jp.items():
                if l4t in output:
                    current = jp
                    break

    # Map device model
    device_model = "jetson-unknown"
    if "nano" in jetson_model:
        device_model = "jetson-nano"
    elif "xavier-nx" in jetson_model:
        device_model = "jetson-xavier-nx"
    elif "agx-xavier" in jetson_model:
        device_model = "jetson-agx-xavier"
    elif "tx2" in jetson_model:
        device_model = "jetson-tx2"
    elif "orin-nx" in jetson_model:
        device_model = "jetson-orin-nx"
    elif "orin-nano" in jetson_model:
        device_model = "jetson-orin-nano"
    elif "agx-orin" in jetson_model:
        device_model = "jetson-agx-orin"

    return _check_version_helper(
        ctx, "jetpack_version", "JetPack", current, "jetpack", device_model
    )


@check(id="rknn_version", class_name="RKNNVersionCheck",
       category="AI", title="RKNN SDK Version",
       description="检查 Rockchip 设备的 RKNN SDK 版本")
def rknn_version(ctx: "CheckContext"):
    """检测 RKNN SDK 版本（Rockchip 设备）"""
    is_rockchip = False
    try:
        with open("/proc/device-tree/compatible", "r") as f:
            compat = f.read().lower()
            is_rockchip = "rockchip" in compat or "rk35" in compat
    except Exception:
        pass

    if not is_rockchip:
        try:
            with open("/dev/rknpu", "r"):
                is_rockchip = True
        except Exception:
            pass

    if not is_rockchip:
        return ctx.result(
            passed=True, current="n/a", expected="n/a",
            message="Not a Rockchip NPU device",
            severity=CheckSeverity.INFO,
        )

    current = "unknown"
    try:
        from rknn.api import RKNN
        rknn = RKNN()
        current = rknn.get_sdk_version().decode("utf-8").split(" ")[-1]
    except ImportError:
        output = _run_cmd("cat /usr/local/rknpu2/version.txt 2>/dev/null || echo ''")
        if output.strip():
            current = output.strip()
        else:
            return ctx.result(
                passed=True, current="installed", expected="version detectable",
                message="RKNN SDK installed but version undetermined",
                severity=CheckSeverity.WARNING,
            )

    return _check_version_helper(
        ctx, "rknn_version", "RKNN SDK", current, "rknn_sdk"
    )


@check(id="pytorch_version", class_name="PyTorchVersionCheck",
       category="AI", title="PyTorch Version",
       description="检查 PyTorch 是否安装且为最新版本")
def pytorch_version(ctx: "CheckContext"):
    """检测 PyTorch 版本"""
    try:
        import torch
        current = torch.__version__
    except ImportError:
        return ctx.result(
            passed=True, current="not installed", expected="installed",
            message="PyTorch not installed",
            severity=CheckSeverity.WARNING,
            fix_available=True,
            fix_command="pip install torch",
            fix_description="Install PyTorch",
            fix_risk="low",
        )
    return _check_version_helper(
        ctx, "pytorch_version", "PyTorch", current, "pytorch"
    )


@check(id="onnxruntime_version", class_name="ONNXRuntimeVersionCheck",
       category="AI", title="ONNX Runtime Version",
       description="检查 ONNX Runtime 是否安装且为最新版本")
def onnxruntime_version(ctx: "CheckContext"):
    """检测 ONNX Runtime 版本"""
    try:
        import onnxruntime as ort
        current = ort.__version__
    except ImportError:
        return ctx.result(
            passed=True, current="not installed", expected="installed",
            message="ONNX Runtime not installed",
            severity=CheckSeverity.INFO,
            fix_available=True,
            fix_command="pip install onnxruntime",
            fix_description="Install ONNX Runtime",
            fix_risk="low",
        )
    return _check_version_helper(
        ctx, "onnxruntime_version", "ONNX Runtime", current, "onnxruntime"
    )


# ── Backward compatibility aliases ────────────────────────────────────────────

# 类名兼容：模块导出原类名
NvidiaDriverVersionCheck = nvidia_driver_version
CudaVersionCheck = cuda_version
TensorRTVersionCheck = tensorrt_version
JetPackVersionCheck = jetpack_version
RKNNVersionCheck = rknn_version
PyTorchVersionCheck = pytorch_version
ONNXRuntimeVersionCheck = onnxruntime_version

# __getattr__ 兜底（旧的 VersionCheckerCheck 名称）
def __getattr__(name):
    if name == "VersionCheckerCheck":
        return nvidia_driver_version
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ── AIVersionCheck 保留（复杂场景备用）────────────────────────────────────────
# 如需自定义 run() 逻辑，可继承此类：
#
# class MyVersionCheck(AIVersionCheck):
#     check_id = "my_version"
#     def run(self):
#         current = self._get_my_version()
#         return self._check_version("my_tool", current)
