# -*- coding: utf-8 -*-
"""
nastool adapters.detector - 设备指纹识别与适配器加载

工作流程：
1. 按优先级尝试识别（昇腾 -> Jetson）
2. 匹配到设备族后加载对应适配器
3. 返回 (adapter_instance, device_family)

用法：
    from adapters.detector import detect
    adapter, family = detect()
"""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Optional

logger = logging.getLogger("nastool.detector")

# ------------------------------------------------------------------ #
# 设备识别策略
# ------------------------------------------------------------------ #

# 昇腾设备树关键词 -> 设备族
ATLAS_DEVICE_TREE_PATTERNS: dict[str, str] = {
    # Atlas 200系
    "200I A2": "Atlas 200系",
    "200DK A2": "Atlas 200系",
    "Atlas 200": "Atlas 200系",
    # Atlas 300系
    "300I Pro": "Atlas 300系",
    "300I Duo": "Atlas 300系",
    "300V": "Atlas 300系",
    "Atlas 300": "Atlas 300系",
    # Atlas 500系
    "500 A2": "Atlas 500系",
    "Atlas 500": "Atlas 500系",
    # Atlas A2 Lite系
    "A2 智能小站": "Atlas A2 Lite系",
    "A2 边缘计算": "Atlas A2 Lite系",
    "Atlas A2": "Atlas A2 Lite系",
}

# Jetson 设备树关键词 -> 设备族
JETSON_DEVICE_TREE_PATTERNS: dict[str, str] = {
    # Orin AGX
    "Orin AGX": "Orin AGX",
    "AGX Orin": "Orin AGX",
    # Orin NX
    "Orin NX": "Orin NX",
    # Orin Nano
    "Orin Nano": "Orin Nano",
    # AGX Xavier
    "AGX Xavier": "AGX Xavier",
    "Xavier AGX": "AGX Xavier",
    # Xavier NX
    "Xavier NX": "Xavier NX",
    "NX": "Xavier NX",  # 需要更精确匹配，见代码
    # Nano / TX2
    "Nano": "Nano/TX2",
    "TX2": "Nano/TX2",
    "Jetson Nano": "Nano/TX2",
    "Jetson TX2": "Nano/TX2",
}

# 昇腾 npu-smi 路径
NPU_SMI_PATHS = [
    "npu-smi",
    "/usr/local/Ascend/npu/sbin/npu-smi",
    "/usr/local/Ascend/common/bin/npu-smi",
    "/home/HwHiAiUser/npu/toolchains/npu-smi",
]

# Jetson tegrastats 路径
TEGRASTATS_PATHS = [
    "tegrastats",
    "/usr/bin/tegrastats",
    "/tegrastats",
]


def _read_device_tree() -> str:
    """读取设备树 model 文件，Windows 环境返回空字符串"""
    if sys.platform == "win32":
        return ""

    paths = [
        "/sys/firmware/devicetree/base/model",
        "/sys/firmware/devicetree/base/compatible",
    ]
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            continue
    return ""


def _run_cmd(cmd: str, timeout: int = 5) -> str:
    """执行命令并返回 stdout"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ------------------------------------------------------------------ #
# 昇腾识别
# ------------------------------------------------------------------ #

def _detect_ascend() -> Optional[str]:
    """
    识别昇腾设备族。
    策略：
    1. npu-smi 命令存在且可执行
    2. 读取设备树或 npu-smi 输出中的型号关键词
    返回设备族名称，识别失败返回 None。
    """
    # 1. 检查 npu-smi
    npu_smi_cmd = None
    for path in NPU_SMI_PATHS:
        result = _run_cmd(f"{path} -i 0 -q 2>&1 || echo __FAIL__", timeout=5)
        if result and "__FAIL__" not in result and "not found" not in result.lower():
            npu_smi_cmd = path
            break

    if not npu_smi_cmd:
        return None

    # 2. 获取设备型号信息（从 npu-smi 输出或设备树）
    device_info = ""

    # 尝试 npu-smi -L（列出设备）
    output = _run_cmd(f"{npu_smi_cmd} -i all -L 2>&1", timeout=5)
    if output and "__FAIL__" not in output:
        device_info += " " + output

    # 尝试 npu-smi -i 0 -q（详细查询）
    output = _run_cmd(f"{npu_smi_cmd} -i 0 -q 2>&1", timeout=5)
    if output and "__FAIL__" not in output:
        device_info += " " + output

    # 3. 补充设备树
    dt = _read_device_tree()
    device_info += " " + dt

    # 4. 关键词匹配
    for keyword, family in ATLAS_DEVICE_TREE_PATTERNS.items():
        if keyword in device_info:
            logger.info(f"[Ascend] 识别到设备族: {family} (关键词: {keyword})")
            return family

    # 5. 兜底：npu-smi 存在但无法匹配 -> 通用昇腾
    if "npu" in device_info.lower() or "ascend" in device_info.lower():
        logger.warning("[Ascend] npu-smi 存在但无法识别具体型号，使用通用昇腾")
        return "Atlas 200系"  # 最基础的默认

    return None


# ------------------------------------------------------------------ #
# Jetson 识别
# ------------------------------------------------------------------ #

def _detect_jetson() -> Optional[str]:
    """
    识别 Jetson 设备族。
    策略：
    1. 检查 tegrastats 是否存在
    2. 读取设备树 model
    3. 关键词匹配
    返回设备族名称，识别失败返回 None。
    """
    # 1. 检查 tegrastats
    tegrastats_ok = False
    for path in TEGRASTATS_PATHS:
        result = _run_cmd(f"{path} --help 2>&1 || echo __FAIL__", timeout=5)
        if result and "__FAIL__" not in result:
            tegrastats_ok = True
            break

    if not tegrastats_ok:
        return None

    # 2. 读取设备树
    dt = _read_device_tree()
    if not dt:
        # 尝试从 /proc/device-tree/model（部分系统路径）
        dt = _run_cmd("cat /proc/device-tree/model 2>/dev/null || echo ''")

    # 3. 关键词匹配（注意优先级）
    # Orin 系列必须在 Nano/NX 之前匹配（因为 "Orin" 不含 "NX" 但 "Orin NX" 应该匹配 Orin NX）
    for keyword in ["Orin AGX", "AGX Orin"]:
        if keyword in dt:
            logger.info(f"[Jetson] 识别到设备族: Orin AGX")
            return "Orin AGX"

    for keyword in ["Orin NX", "Orin-NX"]:
        if keyword in dt:
            logger.info(f"[Jetson] 识别到设备族: Orin NX")
            return "Orin NX"

    for keyword in ["Orin Nano", "Orin-Nano", "Jetson Orin Nano"]:
        if keyword in dt:
            logger.info(f"[Jetson] 识别到设备族: Orin Nano")
            return "Orin Nano"

    for keyword in ["AGX Xavier", "Xavier AGX", "Jetson AGX"]:
        if keyword in dt:
            logger.info(f"[Jetson] 识别到设备族: AGX Xavier")
            return "AGX Xavier"

    for keyword in ["Xavier NX", "NX", "Jetson NX"]:
        if "Xavier" in dt and "NX" in dt:
            logger.info(f"[Jetson] 识别到设备族: Xavier NX")
            return "Xavier NX"

    for keyword in ["TX2", "Jetson TX2"]:
        if keyword in dt:
            logger.info(f"[Jetson] 识别到设备族: Nano/TX2")
            return "Nano/TX2"

    for keyword in ["Nano", "Jetson Nano"]:
        if keyword in dt:
            logger.info(f"[Jetson] 识别到设备族: Nano/TX2")
            return "Nano/TX2"

    # 4. 兜底：tegrastats 存在但无法匹配
    if tegrastats_ok:
        logger.warning("[Jetson] tegrastats 存在但无法识别具体型号，使用 Nano/TX2 默认")
        return "Nano/TX2"

    return None


# ------------------------------------------------------------------ #
# 主入口
# ------------------------------------------------------------------ #

def detect() -> tuple[Optional["BaseAdapter"], Optional[str]]:
    """
    自动检测设备类型并返回 (适配器实例, 设备族名称)。

    检测顺序：昇腾 -> Jetson -> None

    Windows 环境：
        返回 (None, None)，Windows 不运行 ARM 设备诊断。
        调用方应处理此情况并退出。
    """
    if sys.platform == "win32":
        logger.warning("[Detector] Windows 环境，跳过 ARM 设备检测")
        return None, None

    # 1. 尝试昇腾
    family = _detect_ascend()
    if family:
        from adapters.ascend.common import AscendAdapter

        adapter = AscendAdapter()
        return adapter, family

    # 2. 尝试 Jetson
    family = _detect_jetson()
    if family:
        from adapters.jetson.common import JetsonAdapter

        adapter = JetsonAdapter()
        return adapter, family

    # 3. 无法识别
    logger.warning("[Detector] 无法识别设备类型，返回 None")
    return None, None


def detect_with_manual(model: str) -> tuple[Optional["BaseAdapter"], str]:
    """
    手动指定设备型号进行适配器加载。

    model: 设备族名称（如 "Atlas 200系"、"Orin AGX"）
    返回 (适配器实例, 设备族名称)。
    """
    from adapters.ascend.common import AscendAdapter
    from adapters.jetson.common import JetsonAdapter

    ascend_families = [
        "Atlas 200系", "Atlas 300系", "Atlas 500系", "Atlas A2 Lite系"
    ]
    jetson_families = [
        "Orin AGX", "Orin NX", "Orin Nano", "AGX Xavier", "Xavier NX", "Nano/TX2"
    ]

    if model in ascend_families:
        adapter = AscendAdapter()
        adapter.result.device_family = model
        adapter.result.device_model = model
        logger.info(f"[Detector] 手动指定昇腾设备族: {model}")
        return adapter, model

    if model in jetson_families:
        adapter = JetsonAdapter()
        adapter.result.device_family = model
        adapter.result.device_model = model
        logger.info(f"[Detector] 手动指定 Jetson 设备族: {model}")
        return adapter, model

    raise ValueError(f"未知设备族: {model}，有效值：{ascend_families + jetson_families}")
