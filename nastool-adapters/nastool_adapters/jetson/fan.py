# -*- coding: utf-8 -*-
"""
nastool adapters.jetson.fan - Jetson 风扇控制

Jetson 风扇控制方式：
- 手动模式：echo PWM 值到 /sys/devices/pwm-fan/target_pwm
- 自动模式：jetson_clocks 或 fan_control 服务
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger("nastool.jetson.fan")

# PWM 值范围
PWM_MIN = 0
PWM_MAX = 255


def _run(cmd: str, timeout: int = 10) -> tuple[str, str, int]:
    """执行命令"""
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except Exception as e:
        return "", str(e), -1


def detect_fan_status() -> Dict[str, Any]:
    """
    检测风扇状态。

    Returns:
        {
            "present": bool,
            "pwm": int,           # 当前 PWM 值 (0-255)
            "speed_pct": float,   # 转速百分比
            "mode": str,          # manual/auto
            "rpm": int,           # 转速（如果可读）
        }
    """
    result: Dict[str, Any] = {
        "present": False,
        "pwm": None,
        "speed_pct": None,
        "mode": "unknown",
        "rpm": None,
    }

    # PWM 文件路径（不同 Jetpack 版本路径不同）
    pwm_paths = [
        "/sys/devices/pwm-fan/target_pwm",
        "/sys/class/hwmon/hwmon0/pwm1",
        "/sys/class/hwmon/hwmon1/pwm1",
        "/sys/kernel/debug/tegra_fan/target_pwm",
    ]

    pwm_file = None
    for path in pwm_paths:
        if os.path.isfile(path):
            pwm_file = path
            break

    if not pwm_file:
        logger.warning("[Fan] 未找到风扇 PWM 文件")
        return result

    result["present"] = True
    result["pwm_path"] = pwm_file

    # 读取 PWM 值
    try:
        with open(pwm_file, "r") as f:
            pwm = int(f.read().strip())
            result["pwm"] = pwm
            result["speed_pct"] = round(pwm / PWM_MAX * 100, 1)
    except Exception as e:
        logger.warning(f"[Fan] 读取 PWM 失败: {e}")

    # 检测风扇控制服务
    stdout, _, code = _run("systemctl is-active fan_control 2>&1 || echo ''")
    if stdout == "active":
        result["mode"] = "auto"
    else:
        # 检查 jetson_clocks 是否在运行
        stdout, _, _ = _run("pgrep -f jetson_clocks 2>&1 || echo ''")
        if stdout:
            result["mode"] = "auto"
        else:
            result["mode"] = "manual"

    # 尝试读取转速（部分设备支持）
    rpm_paths = [
        "/sys/class/hwmon/hwmon0/fan1_input",
        "/sys/class/hwmon/hwmon1/fan1_input",
    ]
    for path in rpm_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r") as f:
                    result["rpm"] = int(f.read().strip())
                    break
            except Exception:
                continue

    logger.info(f"[Fan] 状态: {result}")
    return result


def set_fan_pwm(pwm: int, auto: bool = False) -> Dict[str, Any]:
    """
    设置风扇 PWM 值。

    Args:
        pwm: PWM 值 (0-255)
        auto: 是否启用自动模式

    Returns:
        {"success": bool, "message": str}
    """
    result = {"success": False, "message": ""}

    if not auto:
        pwm = max(PWM_MIN, min(PWM_MAX, pwm))

        # PWM 文件路径
        pwm_paths = [
            "/sys/devices/pwm-fan/target_pwm",
            "/sys/class/hwmon/hwmon0/pwm1",
            "/sys/kernel/debug/tegra_fan/target_pwm",
        ]

        pwm_file = None
        for path in pwm_paths:
            if os.path.isfile(path):
                pwm_file = path
                break

        if not pwm_file:
            result["message"] = "未找到风扇 PWM 文件"
            return result

        # 写入 PWM 值（可能需要 sudo）
        stdout, stderr, code = _run(f"echo {pwm} | sudo tee {pwm_file} 2>&1")
        if code == 0:
            result["success"] = True
            result["message"] = f"风扇 PWM 已设置为 {pwm} ({round(pwm/255*100, 1)}%)"
            logger.info(f"[Fan] {result['message']}")
        else:
            result["message"] = f"设置失败: {stderr}"
            logger.error(f"[Fan] 设置 PWM 失败: {stderr}")
    else:
        # 启用自动模式
        stdout, stderr, code = _run("sudo systemctl start fan_control 2>&1 || echo ''")
        if code == 0:
            result["success"] = True
            result["message"] = "风扇已切换为自动模式"
            logger.info(f"[Fan] {result['message']}")
        else:
            result["message"] = f"启用自动模式失败: {stderr}"

    return result


def get_fan_info() -> Dict[str, Any]:
    """获取风扇完整信息"""
    status = detect_fan_status()

    return {
        "status": status,
        "pwm_range": {"min": PWM_MIN, "max": PWM_MAX},
        "presets": {
            "off": 0,
            "low": 80,
            "medium": 150,
            "high": 200,
            "max": 255,
        },
    }
