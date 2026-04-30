# -*- coding: utf-8 -*-
"""
nastool adapters.jetson.power - Jetson 功耗模式管理

Jetson 支持 nvpmodel 切换功耗模式：
- 0: MAX N（最高性能，最大功耗）
- 1: 15W
- 2: 10W
- ...

不同设备型号有不同的功耗模式配置。
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nastool.jetson.power")

# ------------------------------------------------------------------ #
# 设备默认功耗模式
# ------------------------------------------------------------------ #

DEFAULT_POWER_MODES = {
    "Orin AGX": {
        "modes": {
            0: {"name": "MAX N", "power": "60W", "cpu": "全部核心", "gpu": "最大频率"},
            1: {"name": "50W", "power": "50W", "cpu": "全部核心", "gpu": "高频率"},
            2: {"name": "30W", "power": "30W", "cpu": "部分核心", "gpu": "中频率"},
            3: {"name": "15W", "power": "15W", "cpu": "少核心", "gpu": "低频率"},
        },
        "default": 0,
    },
    "Orin NX": {
        "modes": {
            0: {"name": "MAX N", "power": "25W", "cpu": "全部核心", "gpu": "最大频率"},
            1: {"name": "15W", "power": "15W", "cpu": "部分核心", "gpu": "中频率"},
            2: {"name": "10W", "power": "10W", "cpu": "少核心", "gpu": "低频率"},
        },
        "default": 0,
    },
    "Orin Nano": {
        "modes": {
            0: {"name": "MAX N", "power": "15W", "cpu": "全部核心", "gpu": "最大频率"},
            1: {"name": "10W", "power": "10W", "cpu": "部分核心", "gpu": "中频率"},
            2: {"name": "7W", "power": "7W", "cpu": "少核心", "gpu": "低频率"},
        },
        "default": 0,
    },
    "AGX Xavier": {
        "modes": {
            0: {"name": "MAX N", "power": "30W", "cpu": "全部核心", "gpu": "最大频率"},
            1: {"name": "15W", "power": "15W", "cpu": "部分核心", "gpu": "中频率"},
            2: {"name": "10W", "power": "10W", "cpu": "少核心", "gpu": "低频率"},
        },
        "default": 0,
    },
    "Xavier NX": {
        "modes": {
            0: {"name": "MAX N", "power": "15W", "cpu": "全部核心", "gpu": "最大频率"},
            1: {"name": "10W", "power": "10W", "cpu": "部分核心", "gpu": "中频率"},
            2: {"name": "7.5W", "power": "7.5W", "cpu": "少核心", "gpu": "低频率"},
        },
        "default": 0,
    },
    "Nano/TX2": {
        "modes": {
            0: {"name": "MAX N", "power": "10W", "cpu": "全部核心", "gpu": "最大频率"},
            1: {"name": "5W", "power": "5W", "cpu": "部分核心", "gpu": "低频率"},
        },
        "default": 1,
    },
}


def _run(cmd: str, timeout: int = 10) -> tuple[str, str, int]:
    """执行命令并返回结果"""
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except subprocess.TimeoutExpired:
        return "", "命令执行超时", -1
    except Exception as e:
        return "", str(e), -1


def detect_power_mode() -> Dict[str, Any]:
    """
    检测当前功耗模式。

    Returns:
        {
            "mode": int,           # 当前模式编号
            "name": str,           # 模式名称
            "power": str,          # 功耗
            "available_modes": [], # 可用模式列表
            "nvpmodel_installed": bool,
        }
    """
    result: Dict[str, Any] = {
        "mode": None,
        "name": "Unknown",
        "power": "Unknown",
        "available_modes": [],
        "nvpmodel_installed": False,
    }

    # 检查 nvpmodel 是否安装
    stdout, stderr, code = _run("which nvpmodel 2>&1 || echo ''")
    if not stdout or code != 0:
        logger.warning("[Power] nvpmodel 未安装")
        return result

    result["nvpmodel_installed"] = True

    # 获取当前模式
    stdout, stderr, code = _run("sudo nvpmodel -q 2>&1 || echo ''")
    if code == 0 and stdout:
        # 解析输出：
        # NV Power Mode: 15W
        # 或
        # NV Power Mode[0]: MAX N
        m = re.search(r"NV Power Mode(?:\[(\d+)\])?:\s*(.+)", stdout)
        if m:
            mode_num = m.group(1)
            mode_name = m.group(2).strip()
            result["mode"] = int(mode_num) if mode_num else 0
            result["name"] = mode_name

    # 获取可用模式列表
    stdout, stderr, code = _run("cat /etc/nvpmodel.conf 2>&1 | grep -E '^[0-9]+' || echo ''")
    if stdout:
        modes = []
        for line in stdout.splitlines():
            # 格式：0: MAX N
            m = re.match(r"(\d+):\s*(.+)", line.strip())
            if m:
                modes.append({"id": int(m.group(1)), "name": m.group(2).strip()})
        result["available_modes"] = modes

    logger.info(f"[Power] 功耗模式: {result}")
    return result


def set_power_mode(mode: int) -> Dict[str, Any]:
    """
    设置功耗模式（需要 sudo 权限）。

    Args:
        mode: 模式编号（0 = 最高性能）

    Returns:
        {"success": bool, "message": str}
    """
    result = {"success": False, "message": ""}

    stdout, stderr, code = _run(f"sudo nvpmodel -m {mode} 2>&1")
    if code == 0:
        result["success"] = True
        result["message"] = f"功耗模式已设置为 {mode}"
        logger.info(f"[Power] {result['message']}")
    else:
        result["message"] = f"设置失败: {stderr}"
        logger.error(f"[Power] 设置功耗模式失败: {stderr}")

    return result


def get_power_info(device_family: str) -> Dict[str, Any]:
    """
    获取设备功耗配置信息。

    Args:
        device_family: 设备族名称

    Returns:
        {
            "modes": {...},
            "default": int,
            "current": {...},
        }
    """
    config = DEFAULT_POWER_MODES.get(device_family, {})
    current = detect_power_mode()

    return {
        "modes": config.get("modes", {}),
        "default_mode": config.get("default", 0),
        "current": current,
    }
