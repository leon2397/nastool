# -*- coding: utf-8 -*-
"""
nastool adapters.ascend.npu - 昇腾 NPU 详细信息解析

解析 npu-smi info 输出，获取：
- 设备型号/芯片类型
- NPU 利用率/温度/功率
- 内存使用情况
- 健康状态
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nastool.ascend.npu")

# ------------------------------------------------------------------ #
# 昇腾芯片型号映射
# ------------------------------------------------------------------ #

ASCEND_CHIP_MAP = {
    # Atlas 200 系列
    "Ascend 310": {"series": "Atlas 200系", "tops": 22, "typical_power": 8},
    "Ascend 310P": {"series": "Atlas 200系", "tops": 44, "typical_power": 10},
    
    # Atlas 300 系列
    "Ascend 910": {"series": "Atlas 300系", "tops": 256, "typical_power": 310},
    "Ascend 910B": {"series": "Atlas 300系", "tops": 376, "typical_power": 350},
    "Ascend 910P": {"series": "Atlas 300系", "tops": 512, "typical_power": 400},
    
    # Atlas 500 系列
    "Ascend 310B": {"series": "Atlas 500系", "tops": 40, "typical_power": 12},
    
    # Atlas A2 系列
    "Ascend 310B1": {"series": "Atlas A2 Lite", "tops": 88, "typical_power": 20},
    "Ascend 910B1": {"series": "Atlas A2", "tops": 280, "typical_power": 300},
}


def _run(cmd: str, timeout: int = 10) -> tuple[str, str, int]:
    """执行命令"""
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except subprocess.TimeoutExpired:
        return "", "命令执行超时", -1
    except Exception as e:
        return "", str(e), -1


def find_npu_smi() -> Optional[str]:
    """查找 npu-smi 命令路径"""
    for path in ["npu-smi", "/usr/local/bin/npu-smi", "/usr/bin/npu-smi"]:
        stdout, _, code = _run(f"{path} -h 2>&1 | head -1 || echo ''", timeout=5)
        if stdout and "NPU" in stdout or "usage" in stdout.lower():
            return path
    return None


def parse_npu_smi_info(output: str) -> Dict[str, Any]:
    """
    解析 npu-smi info 输出。

    输出格式示例：
    ```
    NPU ID                         : 0
    Chip Name                      : Ascend 910B
    Chip Type                      : Ascend910B
    Processors                     : AICORE
    AI Core                        : 0 (OK)
    AI CPU                         : 0 (OK)
    Ctrl CPU                       : 0 (OK)
    Memory Usage                   : 1536 / 32768 MB
    HBM Usage                      : 8192 / 65536 MB
    Power                          : 310.0 W
    Temp                           : 62 C
    AICore Freq                    : 1800 MHz
    AICore Util                    : 45 %
    Bandwidth                      : 1024 GB/s
    Health                         : OK
    ```
    """
    result: Dict[str, Any] = {
        "devices": [],
        "total_memory_mb": 0,
        "used_memory_mb": 0,
        "total_hbm_mb": 0,
        "used_hbm_mb": 0,
        "max_temperature": 0,
        "max_power": 0,
        "errors": [],
    }

    # 按 NPU 分割
    device_blocks = re.split(r"NPU\s+ID\s*:", output)[1:]  # 跳过第一个空块

    for block in device_blocks:
        device: Dict[str, Any] = {}
        
        # NPU ID
        m = re.search(r"(\d+)", block)
        if m:
            device["npu_id"] = int(m.group(1))

        # Chip Name
        m = re.search(r"Chip\s+Name\s*:\s*(.+)", block, re.IGNORECASE)
        if m:
            device["chip_name"] = m.group(1).strip()
            # 获取芯片信息
            chip_info = ASCEND_CHIP_MAP.get(device["chip_name"], {})
            device["series"] = chip_info.get("series", "Unknown")
            device["tops"] = chip_info.get("tops", 0)
            device["typical_power"] = chip_info.get("typical_power", 0)

        # Memory Usage
        m = re.search(r"Memory\s+Usage\s*:\s*(\d+)\s*/\s*(\d+)\s*MB", block, re.IGNORECASE)
        if m:
            device["memory_used_mb"] = int(m.group(1))
            device["memory_total_mb"] = int(m.group(2))
            device["memory_util_pct"] = round(int(m.group(1)) / int(m.group(2)) * 100, 1)

        # HBM Usage
        m = re.search(r"HBM\s+Usage\s*:\s*(\d+)\s*/\s*(\d+)\s*MB", block, re.IGNORECASE)
        if m:
            device["hbm_used_mb"] = int(m.group(1))
            device["hbm_total_mb"] = int(m.group(2))
            device["hbm_util_pct"] = round(int(m.group(1)) / int(m.group(2)) * 100, 1)

        # Power
        m = re.search(r"Power\s*:\s*([\d.]+)\s*W", block, re.IGNORECASE)
        if m:
            device["power_w"] = float(m.group(1))

        # Temperature
        m = re.search(r"Temp\s*:\s*([\d.]+)\s*C", block, re.IGNORECASE)
        if m:
            device["temperature_c"] = float(m.group(1))

        # AICore Util
        m = re.search(r"AICore\s+Util\s*:\s*(\d+)\s*%", block, re.IGNORECASE)
        if m:
            device["aicore_util_pct"] = int(m.group(1))

        # AICore Freq
        m = re.search(r"AICore\s+Freq\s*:\s*(\d+)\s*MHz", block, re.IGNORECASE)
        if m:
            device["aicore_freq_mhz"] = int(m.group(1))

        # Health
        m = re.search(r"Health\s*:\s*(\w+)", block, re.IGNORECASE)
        if m:
            device["health"] = m.group(1).upper()

        result["devices"].append(device)

        # 汇总统计
        if device.get("memory_total_mb"):
            result["total_memory_mb"] += device["memory_total_mb"]
            result["used_memory_mb"] += device.get("memory_used_mb", 0)
        if device.get("hbm_total_mb"):
            result["total_hbm_mb"] += device["hbm_total_mb"]
            result["used_hbm_mb"] += device.get("hbm_used_mb", 0)
        if device.get("temperature_c", 0) > result["max_temperature"]:
            result["max_temperature"] = device["temperature_c"]
        if device.get("power_w", 0) > result["max_power"]:
            result["max_power"] = device["power_w"]

        # 健康状态错误
        if device.get("health") not in ["OK", "NORMAL"]:
            result["errors"].append(f"NPU {device.get('npu_id', '?')} health: {device.get('health')}")

    return result


def parse_npu_smi_query(output: str) -> Dict[str, Any]:
    """
    解析 npu-smi query 输出（XML 格式）。

    更详细的信息，包括：
    - 固件版本
    - 驱动版本
    - 详细的健康指标
    """
    result: Dict[str, Any] = {}

    # 简化处理，提取关键字段
    m = re.search(r"<version>([^<]+)</version>", output)
    if m:
        result["firmware_version"] = m.group(1)

    m = re.search(r"<driver>([^<]+)</driver>", output)
    if m:
        result["driver_version"] = m.group(1)

    return result


def get_npu_info() -> Dict[str, Any]:
    """
    获取 NPU 完整信息。

    Returns:
        {
            "npu_smi_installed": bool,
            "npu_smi_path": str,
            "device_count": int,
            "devices": [...],
            "summary": {...},
            "errors": [...],
        }
    """
    result: Dict[str, Any] = {
        "npu_smi_installed": False,
        "npu_smi_path": None,
        "device_count": 0,
        "devices": [],
        "summary": {},
        "errors": [],
    }

    # 查找 npu-smi
    npu_smi_path = find_npu_smi()
    if not npu_smi_path:
        logger.warning("[NPU] npu-smi 未安装")
        return result

    result["npu_smi_installed"] = True
    result["npu_smi_path"] = npu_smi_path

    # 执行 npu-smi info
    stdout, stderr, code = _run(f"{npu_smi_path} info 2>&1")
    if code == 0 and stdout:
        parsed = parse_npu_smi_info(stdout)
        result["devices"] = parsed["devices"]
        result["device_count"] = len(parsed["devices"])
        result["summary"] = {
            "total_memory_mb": parsed["total_memory_mb"],
            "used_memory_mb": parsed["used_memory_mb"],
            "total_hbm_mb": parsed["total_hbm_mb"],
            "used_hbm_mb": parsed["used_hbm_mb"],
            "max_temperature": parsed["max_temperature"],
            "max_power": parsed["max_power"],
        }
        result["errors"] = parsed["errors"]
        result["raw_output"] = stdout[:2000]  # 保留原始输出（截断）

    logger.info(f"[NPU] 检测到 {result['device_count']} 个 NPU 设备")
    return result


def detect_cann_version() -> Optional[str]:
    """检测 CANN 版本"""
    # 从环境变量
    cann_root = os.environ.get("ASCEND_HOME") or os.environ.get("ASCEND_TOOLKIT_HOME")
    if cann_root:
        version_file = os.path.join(cann_root, "version.cfg")
        if os.path.isfile(version_file):
            try:
                with open(version_file, "r", errors="ignore") as f:
                    content = f.read()
                    m = re.search(r"Version\s*[:=]\s*([^\n]+)", content)
                    if m:
                        return m.group(1).strip()
            except Exception:
                pass

    # 从 npu-smi
    stdout, _, _ = _run("npu-smi info 2>&1 | grep -i 'cann' || echo ''")
    if stdout:
        m = re.search(r"CANN[:\s]+([\d.]+)", stdout)
        if m:
            return m.group(1)

    return None


def detect_acl_available() -> bool:
    """检测 ACL (Ascend Computing Language) 是否可用"""
    stdout, _, code = _run(
        "python3 -c 'import acl; print(acl.get_version())' 2>&1 || echo ''"
    )
    return code == 0 and stdout and "Error" not in stdout
