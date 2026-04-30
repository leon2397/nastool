# -*- coding: utf-8 -*-
"""
nastool adapters.ascend.common - 华为昇腾通用适配器

支持 4 类设备：
- Atlas 200系（嵌入式模组/开发板）
- Atlas 300系（PCIe 推理卡）
- Atlas 500系（边缘小站）
- Atlas A2 Lite系（新代际边缘）

主要工具：npu-smi / CANN / ACL / MindSpore / TF-Ascend / PyTorch-Ascend
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Any, Optional

from nastool_adapters.base import BaseAdapter, AdapterResult, ErrorCode

logger = logging.getLogger("nastool.ascend")

# ------------------------------------------------------------------ #
# npu-smi 路径探测
# ------------------------------------------------------------------ #

NPU_SMI_PATHS = [
    "npu-smi",
    "/usr/local/Ascend/npu/sbin/npu-smi",
    "/usr/local/Ascend/npu/bin/npu-smi",
    "/usr/local/Ascend/common/bin/npu-smi",
    "/usr/local/Ascend/tools/bin/npu-smi",
    "/home/HwHiAiUser/npu/toolchains/npu-smi",
]

# CANN 安装路径
CANN_PATHS = [
    "/usr/local/Ascend",
    "/home/HwHiAiUser/Ascend",
    "/opt/Ascend",
    "/usr/local/Ascend/npu",
]

# ------------------------------------------------------------------ #
# 设备族到型号的映射
# ------------------------------------------------------------------ #

ATLAS_FAMILY_MODELS = {
    "Atlas 200系": [
        "Atlas 200I A2",
        "Atlas 200DK A2",
        "Atlas 200 (一代)",
    ],
    "Atlas 300系": [
        "Atlas 300I Pro",
        "Atlas 300I Duo",
        "Atlas 300V 寿光卡",
        "Atlas 300I 寿光卡",
    ],
    "Atlas 500系": [
        "Atlas 500 A2",
    ],
    "Atlas A2 Lite系": [
        "Atlas A2 智能小站",
        "Atlas A2 边缘计算网关",
    ],
}


# ------------------------------------------------------------------ #
# 工具函数
# ------------------------------------------------------------------ #

def _run(cmd: str, timeout: int = 10) -> tuple[str, str, int]:
    """执行 shell 命令"""
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except subprocess.TimeoutExpired:
        return "", "命令执行超时", -1
    except Exception as e:
        return "", str(e), -1


def _find_npu_smi() -> Optional[str]:
    """查找 npu-smi 可执行文件路径"""
    for path in NPU_SMI_PATHS:
        stdout, stderr, code = _run(f"{path} -i 0 -q 2>&1 || echo __FAIL__", timeout=5)
        if code == 0 and "__FAIL__" not in stdout and "not found" not in stdout.lower():
            return path
    return None


def _find_cann_version() -> Optional[str]:
    """探测 CANN 版本"""
    for base in CANN_PATHS:
        for sub in ["", "/npu", "/driver", "/latest"]:
            cann_root = os.path.join(base, sub)
            version_file = os.path.join(cann_root, "version.info")
            if os.path.isfile(version_file):
                try:
                    with open(version_file, "r", errors="ignore") as f:
                        content = f.read().strip()
                        # 格式：version=6.3.T50 或类似
                        m = re.search(r"version\s*=\s*([\d.]+)", content)
                        if m:
                            return m.group(1)
                except Exception:
                    continue
            # 另一种常见格式：ascend-nna-ease.m包版本文件
            ease_file = os.path.join(cann_root, "ascend_nna_ease.info")
            if os.path.isfile(ease_file):
                try:
                    with open(ease_file, "r", errors="ignore") as f:
                        content = f.read().strip()
                        m = re.search(r"(\d+\.\d+\.\d+)", content)
                        if m:
                            return m.group(1)
                except Exception:
                    continue
    return None


def _parse_npu_smi_list(npu_smi_cmd: str) -> list[dict[str, str]]:
    """npu-smi -i all -L 获取设备列表"""
    stdout, _, code = _run(f"{npu_smi_cmd} -i all -L 2>&1", timeout=10)
    if code != 0:
        return []

    devices = []
    # 格式：Card 0 [Ascend 310P3]
    #       Card 1 [Ascend 310]
    pattern = re.compile(r"Card\s+(\d+)\s+\[([^\]]+)\]")
    for line in stdout.splitlines():
        m = pattern.search(line)
        if m:
            devices.append({
                "id": m.group(1),
                "chip": m.group(2),
            })
    return devices


def _parse_npu_smi_query(npu_smi_cmd: str, card_id: str = "0") -> dict[str, str]:
    """npu-smi -i {card_id} -q 获取单卡详细信息"""
    stdout, _, code = _run(f"{npu_smi_cmd} -i {card_id} -q 2>&1", timeout=10)
    if code != 0:
        return {}

    info = {}
    # 解析 key = value 格式
    # 支持多种格式：
    #   Chip Frequency(MHz)        : 1512
    #   NPU Utilization(%)          : 17
    #   Chip Temperature(C)         : 61
    for line in stdout.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        # 取最后一个冒号分割的值
        parts = line.rsplit(":", 1)
        if len(parts) == 2:
            key = parts[0].strip().strip("*|")
            val = parts[1].strip()
            info[key] = val
    return info


def _parse_memory(mem_str: str) -> float:
    """解析内存字符串（如 "15736 MB" 或 "15.3 GB"）返回 MB"""
    mem_str = mem_str.strip()
    m = re.search(r"([\d.]+)\s*(MB|GB|TB|KB|B)?", mem_str, re.IGNORECASE)
    if not m:
        return 0.0
    value = float(m.group(1))
    unit = (m.group(2) or "MB").upper()
    if unit == "GB":
        return value * 1024
    elif unit == "TB":
        return value * 1024 * 1024
    elif unit == "KB":
        return value / 1024
    elif unit == "B":
        return value / (1024 * 1024)
    return value


# ------------------------------------------------------------------ #
# 适配器类
# ------------------------------------------------------------------ #

class AscendAdapter(BaseAdapter):
    """
    华为昇腾适配器。

    自动识别 4 类设备：
    - Atlas 200系：嵌入式模组（单 NPU，适合轻量推理）
    - Atlas 300系：PCIe 推理卡（多 NPU，支持高吞吐）
    - Atlas 500系：边缘小站（集成度高）
    - Atlas A2 Lite系：新代际边缘推理设备

    检测内容：
    - npu-smi：NPU 数量/型号/利用率/温度/内存/功耗
    - CANN：版本/安装完整性
    - ACL：运行时库可用性
    - MindSpore / TF-Ascend / PyTorch-Ascend
    - 系统：CPU/内存/存储/网络
    """

    NAME = "ascend"
    DEVICE_FAMILIES = list(ATLAS_FAMILY_MODELS.keys())

    # 设备族 -> 推荐的 NPU 利用率阈值
    FAMILY_THRESHOLDS = {
        "Atlas 200系":   {"util_high": 90, "temp_warn": 80, "temp_crit": 90},
        "Atlas 300系":   {"util_high": 85, "temp_warn": 85, "temp_crit": 95},
        "Atlas 500系":   {"util_high": 80, "temp_warn": 80, "temp_crit": 90},
        "Atlas A2 Lite系": {"util_high": 85, "temp_warn": 85, "temp_crit": 95},
    }

    def __init__(self):
        super().__init__()
        self.npu_smi_cmd: Optional[str] = None

    # ------------------------------------------------------------------ #
    # BaseAdapter 实现
    # ------------------------------------------------------------------ #

    def identify(self) -> str:
        """
        识别昇腾设备族。

        策略：
        1. 读取设备树 /proc/device-tree/model（关键词匹配）
        2. npu-smi -i all -L 输出匹配
        3. npu-smi -i 0 -q 详细输出匹配
        """
        # 1. 设备树
        dt_model = ""
        for path in [
            "/sys/firmware/devicetree/base/model",
            "/proc/device-tree/model",
        ]:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    dt_model = f.read().strip()
                    if dt_model:
                        break
            except Exception:
                continue

        if dt_model:
            logger.info(f"[Ascend] 设备树: {dt_model}")

        # 2. 关键词匹配设备树
        for keyword, family in [
            ("200I A2", "Atlas 200系"), ("200DK A2", "Atlas 200系"),
            ("300I Pro", "Atlas 300系"), ("300I Duo", "Atlas 300系"),
            ("300V", "Atlas 300系"), ("300 寿光", "Atlas 300系"),
            ("500 A2", "Atlas 500系"), ("500", "Atlas 500系"),
            ("A2 智能小站", "Atlas A2 Lite系"), ("A2 边缘计算", "Atlas A2 Lite系"),
            ("Atlas A2", "Atlas A2 Lite系"),
            ("Atlas 200", "Atlas 200系"),
            ("Atlas 300", "Atlas 300系"),
            ("Ascend", "Atlas 300系"),  # 通用昇腾默认 300系
        ]:
            if keyword in dt_model:
                self.result.device_family = family
                return family

        # 3. npu-smi 辅助识别
        if not self.npu_smi_cmd:
            self.npu_smi_cmd = _find_npu_smi()

        if self.npu_smi_cmd:
            devices = _parse_npu_smi_list(self.npu_smi_cmd)
            if devices:
                chip = devices[0].get("chip", "")
                logger.info(f"[Ascend] npu-smi chip: {chip}")

                # Atlas 200 系列芯片
                if "310" in chip or "200" in chip:
                    return "Atlas 200系"
                # Atlas 300 系列（310P3 / 910）
                if "310P" in chip or "310P3" in chip:
                    return "Atlas 300系"
                if "910" in chip:
                    return "Atlas 300系"
                # Atlas 500 / A2
                if "A2" in chip or "500" in chip:
                    return "Atlas A2 Lite系"

        # 兜底：昇腾设备但无法细分 -> 默认 Atlas 300系
        return "Atlas 300系"

    def check_tools(self) -> None:
        """检测昇腾工具链是否可用"""
        tools: dict[str, bool] = {}

        # npu-smi
        self.npu_smi_cmd = _find_npu_smi()
        tools["npu-smi"] = self.npu_smi_cmd is not None
        if tools["npu-smi"]:
            tools["npu-smi_path"] = self.npu_smi_cmd

        # CANN
        cann_ver = _find_cann_version()
        tools["cann"] = cann_ver is not None
        if cann_ver:
            tools["cann_version"] = cann_ver

        # ACL（算子库）
        acl_paths = [
            "/usr/local/Ascend/acllib",
            "/usr/local/Ascend/npu/acllib",
            "/usr/lib64/acllib",
        ]
        tools["acl"] = any(os.path.isdir(p) or os.path.isfile(p) for p in acl_paths)

        # MindSpore
        stdout, _, _ = _run("python3 -c 'import mindspore; print(mindspore.__version__)' 2>&1", timeout=5)
        tools["mindspore"] = stdout and "Error" not in stdout and "Traceback" not in stdout
        if tools["mindspore"]:
            tools["mindspore_version"] = stdout.strip()

        # TF-Ascend
        stdout, _, _ = _run("python3 -c 'import tensorflow as tf; print(tf.__version__)' 2>&1", timeout=5)
        tools["tf_ascend"] = "ascend" in stdout.lower() or (
            stdout and "Error" not in stdout and "Traceback" not in stdout
        )
        if tools["tf_ascend"]:
            # 提取 TensorFlow 版本
            m = re.search(r"(\d+\.\d+)", stdout)
            if m:
                tools["tf_version"] = m.group(1)

        # PyTorch-Ascend
        stdout, _, _ = _run("python3 -c 'import torch; print(torch.__version__)' 2>&1", timeout=5)
        tools["pytorch_ascend"] = "ascend" in stdout.lower() or (
            stdout and "Error" not in stdout and "Traceback" not in stdout
        )
        if tools["pytorch_ascend"]:
            m = re.search(r"(\d+\.\d+)", stdout)
            if m:
                tools["pytorch_version"] = m.group(1)

        self.result.tools = tools
        logger.info(f"[Ascend] 工具链: {json.dumps(tools, ensure_ascii=False)}")

    def detect_npu(self) -> None:
        """检测 NPU 状态"""
        if not self.npu_smi_cmd:
            self.npu_smi_cmd = _find_npu_smi()

        npu_status: dict[str, Any] = {
            "npu_smi_found": self.npu_smi_cmd is not None,
            "npu_smi_path": self.npu_smi_cmd,
            "devices": [],
            "total_memory": "",
            "total_used_memory": "",
            "total_free_memory": "",
            "average_util": 0,
            "average_temp": 0,
        }

        if not self.npu_smi_cmd:
            self.result.npu_status = npu_status
            return

        # 获取设备列表
        devices = _parse_npu_smi_list(self.npu_smi_cmd)
        npu_status["device_count"] = len(devices)
        npu_status["device_list"] = devices

        # 逐卡查询
        util_sum = 0
        temp_sum = 0
        for dev in devices:
            card_id = dev["id"]
            info = _parse_npu_smi_query(self.npu_smi_cmd, card_id)

            util = 0
            temp = 0
            mem_total = 0.0
            mem_used = 0.0

            for key, value in info.items():
                key_lower = key.lower()
                if "util" in key_lower and "%" in value:
                    try:
                        util = int(re.search(r"\d+", value).group())
                        util_sum += util
                    except Exception:
                        pass
                if "temperature" in key_lower or "temp" in key_lower:
                    try:
                        temp = int(re.search(r"\d+", value).group())
                        temp_sum += temp
                    except Exception:
                        pass
                if "memory" in key_lower and "total" in key_lower:
                    mem_total = _parse_memory(value)
                if "memory" in key_lower and ("used" in key_lower or "占用" in key_lower):
                    mem_used = _parse_memory(value)

            dev.update({
                "utilization": util,
                "temperature": temp,
                "memory_total_mb": mem_total,
                "memory_used_mb": mem_used,
                "memory_free_mb": max(0, mem_total - mem_used),
                "memory_util_pct": int(mem_used / mem_total * 100) if mem_total > 0 else 0,
                "raw_info": info,
            })

        npu_status["devices"] = devices
        if devices:
            npu_status["average_util"] = util_sum // len(devices)
            npu_status["average_temp"] = temp_sum // len(devices)

        # 整体内存汇总
        total_mem = sum(d.get("memory_total_mb", 0) for d in devices)
        total_used = sum(d.get("memory_used_mb", 0) for d in devices)
        npu_status["total_memory_mb"] = total_mem
        npu_status["total_used_memory_mb"] = total_used
        npu_status["total_free_memory_mb"] = max(0, total_mem - total_used)

        # 保存原始输出
        stdout, _, _ = _run(f"{self.npu_smi_cmd} -i all -L 2>&1")
        npu_status["raw_list"] = stdout
        stdout2, _, _ = _run(f"{self.npu_smi_cmd} -i 0 -q 2>&1")
        npu_status["raw_query"] = stdout2

        self.result.npu_status = npu_status
        logger.info(f"[Ascend] NPU状态: {len(devices)}卡, 平均利用率{npu_status['average_util']}%, 平均温度{npu_status['average_temp']}°C")

    def detect_system(self) -> None:
        """检测通用系统状态"""
        system: dict[str, Any] = {}

        # CPU / 内存
        stdout, _, code = _run("cat /proc/meminfo 2>&1", timeout=5)
        if code == 0:
            mem_info = {}
            for line in stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    mem_info[k.strip()] = v.strip()
            try:
                mem_total = int(mem_info.get("MemTotal", 0)) / 1024  # KB -> MB
                mem_free = int(mem_info.get("MemFree", 0)) / 1024
                mem_available = int(mem_info.get("MemAvailable", mem_free)) / 1024
                mem_buffers = int(mem_info.get("Buffers", 0)) / 1024
                system["memory"] = {
                    "total_mb": round(mem_total, 1),
                    "free_mb": round(mem_free, 1),
                    "available_mb": round(mem_available, 1),
                    "buffers_mb": round(mem_buffers, 1),
                    "used_mb": round(mem_total - mem_available, 1),
                    "util_pct": round((mem_total - mem_available) / mem_total * 100, 1) if mem_total > 0 else 0,
                }
            except Exception as e:
                logger.warning(f"[Ascend] 解析 /proc/meminfo 失败: {e}")

        # CPU 型号
        stdout, _, _ = _run("cat /proc/cpuinfo 2>&1 | grep 'model name' | head -1", timeout=5)
        if stdout:
            system["cpu_model"] = stdout.split(":", 1)[-1].strip()

        # CPU 核心数
        stdout, _, _ = _run("nproc 2>&1", timeout=5)
        if stdout.isdigit():
            system["cpu_cores"] = int(stdout)

        # 负载
        stdout, _, _ = _run("cat /proc/loadavg 2>&1", timeout=5)
        if stdout:
            parts = stdout.split()
            if parts:
                system["loadavg_1m"] = parts[0]
                system["loadavg_5m"] = parts[1]
                system["loadavg_15m"] = parts[2]

        # 磁盘
        stdout, _, _ = _run("df -h / 2>&1 | tail -1", timeout=5)
        if stdout:
            parts = stdout.split()
            if len(parts) >= 5:
                system["disk_root"] = {
                    "filesystem": parts[0],
                    "size": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "use_pct": parts[4].rstrip("%"),
                }

        # 系统版本
        for f in ["/etc/os-release", "/etc/lsb-release"]:
            try:
                with open(f, "r", errors="ignore") as fp:
                    for line in fp:
                        if line.startswith("PRETTY_NAME="):
                            system["os"] = line.split("=", 1)[1].strip().strip('"')
                            break
            except Exception:
                continue

        self.result.system = system
        logger.info(f"[Ascend] 系统状态: {json.dumps(system, ensure_ascii=False)}")

    def get_model_name(self) -> str:
        """返回具体型号名称"""
        family = self.result.device_family
        models = ATLAS_FAMILY_MODELS.get(family, [])
        if models:
            return models[0]  # 取第一个作为代表
        return family

    def calc_score(self) -> None:
        """
        计算昇腾设备健康评分（0-100）。

        维度（4个，各25分）：
        - NPU 利用率（空闲/正常/高负载）
        - NPU 温度（正常/警告/危险）
        - NPU 内存（充足/紧张/耗尽）
        - 系统内存（充足/紧张/耗尽）
        """
        thresholds = self.FAMILY_THRESHOLDS.get(
            self.result.device_family,
            {"util_high": 85, "temp_warn": 80, "temp_crit": 90}
        )

        breakdown: dict[str, int] = {}
        score = 0

        # 1. NPU 利用率（25分）
        util = self.result.npu_status.get("average_util", 0)
        if util < thresholds["util_high"]:
            breakdown["npu_util"] = 25
        elif util < 95:
            breakdown["npu_util"] = 15
        else:
            breakdown["npu_util"] = 5
        score += breakdown["npu_util"]

        # 2. NPU 温度（25分）
        temp = self.result.npu_status.get("average_temp", 0)
        if temp < thresholds["temp_warn"]:
            breakdown["npu_temp"] = 25
        elif temp < thresholds["temp_crit"]:
            breakdown["npu_temp"] = 15
        else:
            breakdown["npu_temp"] = 5
        score += breakdown["npu_temp"]

        # 3. NPU 内存（25分）
        total_mem = self.result.npu_status.get("total_memory_mb", 0)
        used_mem = self.result.npu_status.get("total_used_memory_mb", 0)
        if total_mem > 0:
            mem_util = used_mem / total_mem
            if mem_util < 0.7:
                breakdown["npu_mem"] = 25
            elif mem_util < 0.9:
                breakdown["npu_mem"] = 15
            else:
                breakdown["npu_mem"] = 5
        else:
            breakdown["npu_mem"] = 0  # 无法获取时给0
        score += breakdown["npu_mem"]

        # 4. 系统内存（25分）
        sys_mem = self.result.system.get("memory", {})
        sys_util = sys_mem.get("util_pct", 0)
        if sys_util < 70:
            breakdown["sys_mem"] = 25
        elif sys_util < 85:
            breakdown["sys_mem"] = 15
        else:
            breakdown["sys_mem"] = 5
        score += breakdown["sys_mem"]

        self.result.score = min(100, score)
        self.result.score_breakdown = breakdown
        logger.info(f"[Ascend] 健康评分: {self.result.score}分 {breakdown}")

    def run_benchmark(self) -> None:
        """
        推理基准测试：MobileNetV2 在昇腾 NPU 上推理延迟。

        策略：
        1. 优先 ACL（最高效，需 .om 模型）
        2. 其次 MindSpore Ascend
        3. 再次 ONNX Runtime
        4. 启发式估算作为兜底
        """
        from adapters.benchmark import run_acl_benchmark, run_mindspore_benchmark, run_onnx_benchmark, run_heuristic_benchmark

        benchmark: dict[str, Any] = {
            "model": "MobileNetV2",
            "framework": None,
            "latency_ms": None,
            "throughput_fps": None,
            "status": "skip",
            "error": None,
        }

        tools = self.result.tools

        # 1. ACL（昇腾原生）
        if tools.get("acl"):
            result = run_acl_benchmark(
                model_name="mobilenetv2",
                warmup=3,
                iterations=10,
            )
            if result["status"] == "success":
                self.result.benchmark = result
                return
            benchmark = result

        # 2. MindSpore Ascend
        if tools.get("mindspore"):
            result = run_mindspore_benchmark(
                model_name="mobilenetv2",
                warmup=3,
                iterations=10,
                device_target="Ascend",
            )
            if result["status"] == "success":
                self.result.benchmark = result
                return
            benchmark = result

        # 3. ONNX Runtime（通用方案）
        if tools.get("onnx_runtime"):
            result = run_onnx_benchmark(
                model_name="mobilenetv2",
                warmup=3,
                iterations=10,
                provider="CPUExecutionProvider",
            )
            if result["status"] == "success":
                self.result.benchmark = result
                return
            benchmark = result

        # 4. 启发式兜底
        if not benchmark.get("latency_ms"):
            result = run_heuristic_benchmark()
            result["model"] = "MobileNetV2 (heuristic)"
            benchmark = result

        self.result.benchmark = benchmark
