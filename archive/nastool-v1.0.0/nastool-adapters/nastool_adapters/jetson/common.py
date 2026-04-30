# -*- coding: utf-8 -*-
"""
nastool adapters.jetson.common - Jetson 通用适配器

支持 6 类设备：
- Orin AGX（Ada，275/170TOPS）
- Orin NX（Ada，100/70TOPS）
- Orin Nano（Ada，40/20TOPS）
- AGX Xavier（Volta，11TOPS）
- Xavier NX（Volta，6TOPS）
- Nano/TX2（Maxwell/Pascal）

主要工具：tegrastats / JetPack / CUDA / cuDNN / TensorRT / ONNX Runtime
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Any, Optional

from nastool_adapters.base import BaseAdapter, AdapterResult, ErrorCode

logger = logging.getLogger("nastool.jetson")

# ------------------------------------------------------------------ #
# tegrastats 路径
# ------------------------------------------------------------------ #

TEGRASTATS_PATHS = [
    "tegrastats",
    "/usr/bin/tegrastats",
    "/tegrastats",
]

# ------------------------------------------------------------------ #
# 设备族到型号的映射
# ------------------------------------------------------------------ #

JETSON_FAMILY_MODELS = {
    "Orin AGX": [
        "NVIDIA Jetson AGX Orin 64GB",
        "NVIDIA Jetson AGX Orin 32GB",
        "NVIDIA Jetson AGX Orin",
    ],
    "Orin NX": [
        "NVIDIA Jetson Orin NX 16GB",
        "NVIDIA Jetson Orin NX 8GB",
        "NVIDIA Jetson Orin NX",
    ],
    "Orin Nano": [
        "NVIDIA Jetson Orin Nano 8GB",
        "NVIDIA Jetson Orin Nano 4GB",
        "NVIDIA Jetson Orin Nano",
    ],
    "AGX Xavier": [
        "NVIDIA Jetson AGX Xavier 64GB",
        "NVIDIA Jetson AGX Xavier 32GB",
        "NVIDIA Jetson AGX Xavier",
    ],
    "Xavier NX": [
        "NVIDIA Jetson Xavier NX",
    ],
    "Nano/TX2": [
        "NVIDIA Jetson Nano",
        "NVIDIA Jetson TX2",
    ],
}

# Jetson 架构映射
JETSON_ARCH = {
    "Orin AGX": "Ada Lovelace",
    "Orin NX": "Ada Lovelace",
    "Orin Nano": "Ada Lovelace",
    "AGX Xavier": "Volta",
    "Xavier NX": "Volta",
    "Nano/TX2": "Maxwell / Pascal",
}

# 设备族算力（TOPS，官方标称）
JETSON_TOPS = {
    "Orin AGX": 275,
    "Orin NX": 100,
    "Orin Nano": 40,
    "AGX Xavier": 11,
    "Xavier NX": 6,
    "Nano/TX2": 1,
}

# 评分阈值
JETSON_THRESHOLDS = {
    "Orin AGX": {"temp_warn": 80, "temp_crit": 90, "util_high": 90},
    "Orin NX":  {"temp_warn": 80, "temp_crit": 90, "util_high": 90},
    "Orin Nano": {"temp_warn": 80, "temp_crit": 90, "util_high": 90},
    "AGX Xavier": {"temp_warn": 85, "temp_crit": 95, "util_high": 85},
    "Xavier NX": {"temp_warn": 85, "temp_crit": 95, "util_high": 85},
    "Nano/TX2": {"temp_warn": 85, "temp_crit": 95, "util_high": 85},
}


# ------------------------------------------------------------------ #
# 工具函数
# ------------------------------------------------------------------ #

def _run(cmd: str, timeout: int = 10) -> tuple[str, str, int]:
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except subprocess.TimeoutExpired:
        return "", "命令执行超时", -1
    except Exception as e:
        return "", str(e), -1


def _find_tegrastats() -> Optional[str]:
    for path in TEGRASTATS_PATHS:
        stdout, _, code = _run(f"{path} --help 2>&1 || echo __FAIL__", timeout=5)
        if code == 0 and "__FAIL__" not in stdout:
            return path
    return None


def _parse_tegrastats(output: str) -> dict[str, Any]:
    r"""
    解析 tegrastats 单次输出。

    格式（因 JetPack 版本而异）：

    JetPack 5.x（Orin/Xavier）:
        RAM 7813/31652MB (lfb 3722x4MB) CPU [3%@1374,5%@1375,4%@1374,4%@1376] EMC_FREQ 2133 GR3D_FREQ 0%
        NPU[0] temp:41.0 rail_power:0.000 rail_voltage:0.000

    JetPack 4.x（Nano/TX2）:
        RAM: 3241MB / 3964MB | CPU: [23.4%] | TEMP: 38.7C | VDD: 4432mV / 4418mV

    通用正则：
    - RAM:  (\d+)MB / (\d+)MB
    - CPU:  ([\d.]+)%
    - GR3D: GPU 利用率
    - TEMP: 温度
    - NPU:  NPU 温度/功率（JetsonNX with DLA）
    """
    result: dict[str, Any] = {}

    # RAM - 支持多种格式
    # JetPack 5.x/6.x: RAM 12543/63488MB (lfb ...)
    # JetPack 4.x: RAM: 3241MB / 3964MB
    m = re.search(r"RAM\s+(\d+)/(\d+)MB", output, re.IGNORECASE)
    if not m:
        m = re.search(r"RAM:\s*(\d+)MB\s*/\s*(\d+)MB", output, re.IGNORECASE)
    if m:
        result["ram_used_mb"] = int(m.group(1))
        result["ram_total_mb"] = int(m.group(2))
        result["ram_util_pct"] = round(int(m.group(1)) / int(m.group(2)) * 100, 1)

    # CPU 利用率（方括号格式）
    m = re.search(r"CPU\s*\[([^\]]+)\]", output)
    if m:
        cpu_str = m.group(1)
        cpus = re.findall(r"(\d+)%", cpu_str)
        if cpus:
            cpu_vals = [int(c) for c in cpus]
            result["cpu_util_pct"] = round(sum(cpu_vals) / len(cpu_vals), 1)
            result["cpu_cores"] = len(cpu_vals)

    # CPU 利用率（老格式）
    if "cpu_util_pct" not in result:
        m = re.search(r"CPU:\s*\[?([\d.]+)%\]?", output, re.IGNORECASE)
        if m:
            result["cpu_util_pct"] = float(m.group(1))

    # GPU 利用率
    m = re.search(r"GR3D_FREQ\s+(\d+)%", output, re.IGNORECASE)
    if m:
        result["gpu_util_pct"] = int(m.group(1))

    # 温度（多种格式）
    temps = []
    for pattern in [
        r"temperature[:\s]+([\d.]+)C",
        r"TEMP[:\s]+([\d.]+)C",
        r"temp[:\s]+([\d.]+)",
        r"CPU:.*TEMP[:\s]+([\d.]+)",
    ]:
        m = re.findall(pattern, output, re.IGNORECASE)
        for match in m:
            try:
                temps.append(float(match))
            except ValueError:
                continue
    if temps:
        result["temperature_c"] = round(sum(temps) / len(temps), 1)
        result["max_temperature_c"] = max(temps)

    # NPU 温度（Jetson NX DLA）
    npu_temps = re.findall(r"NPU\[(\d+)\] temp:([\d.]+)", output)
    if npu_temps:
        result["npu_temperatures"] = {int(k): float(v) for k, v in npu_temps}

    # VDD 电压（老格式）
    m = re.search(r"VDD:\s*(\d+)mV", output)
    if m:
        result["vdd_mv"] = int(m.group(1))

    return result


def _detect_jetpack() -> Optional[str]:
    """探测 JetPack 版本"""
    # 优先从 /etc/nv_tegra_release
    if os.path.isfile("/etc/nv_tegra_release"):
        try:
            with open("/etc/nv_tegra_release", "r", errors="ignore") as f:
                content = f.read()
                m = re.search(r"JetPack\s*(\d+[\.\d]*)", content, re.IGNORECASE)
                if m:
                    return m.group(1)
                # L4T 版本对应 JetPack
                m = re.search(r"L4T\s+(\d+\.\d+)", content)
                if m:
                    l4t = float(m.group(1))
                    # L4T 35.x -> JetPack 6.0, L4T 32.x -> JetPack 5.x
                    if l4t >= 35:
                        return f"6.{int((l4t - 35) * 10 + 0)}"
                    elif l4t >= 34:
                        return "5.1"
                    elif l4t >= 32:
                        return "4.6"
        except Exception:
            pass

    # 从 dpkg 查询
    stdout, _, _ = _run("dpkg -l | grep -i 'jetpack' 2>&1 | head -3")
    if stdout:
        m = re.search(r"jetpack[_-]?(\d+[\.\d]*)", stdout, re.IGNORECASE)
        if m:
            return m.group(1)

    return None


def _detect_cuda() -> Optional[str]:
    """探测 CUDA 版本"""
    for path in [
        "/usr/local/cuda/version.txt",
        "/usr/local/cuda/version.json",
    ]:
        if os.path.isfile(path):
            try:
                with open(path, "r", errors="ignore") as f:
                    content = f.read()
                    m = re.search(r"(\d+\.\d+[\.\d]*)", content)
                    if m:
                        return m.group(1)
            except Exception:
                continue

    stdout, _, _ = _run("nvcc --version 2>&1 | grep 'release' || echo ''")
    if stdout:
        m = re.search(r"release\s+(\d+\.\d+)", stdout)
        if m:
            return m.group(1)
    return None


def _detect_tensorrt() -> Optional[str]:
    """探测 TensorRT 版本"""
    stdout, _, _ = _run(
        "python3 -c 'import tensorrt; print(tensorrt.__version__)' 2>&1 || echo ''"
    )
    if stdout and "Error" not in stdout and "Traceback" not in stdout:
        return stdout.strip()
    return None


def _detect_cudnn() -> Optional[str]:
    """探测 cuDNN 版本"""
    cudnn_file = "/usr/include/cudnn_version.h"
    if os.path.isfile(cudnn_file):
        try:
            with open(cudnn_file, "r", errors="ignore") as f:
                content = f.read()
                m = re.search(r"#define\s+CUDNN_VERSION\s+(\d+)", content)
                if m:
                    major = int(m.group(1)[0])
                    minor = int(m.group(1)[1])
                    patch = int(m.group(1)[2:])
                    return f"{major}.{minor}.{patch}"
        except Exception:
            pass
    return None


# ------------------------------------------------------------------ #
# 适配器类
# ------------------------------------------------------------------ #

class JetsonAdapter(BaseAdapter):
    """
    Jetson 适配器。

    自动识别 6 类设备：
    - Orin AGX / Orin NX / Orin Nano（Ada Lovelace 架构）
    - AGX Xavier / Xavier NX（Volta 架构）
    - Nano / TX2（Maxwell / Pascal 架构）

    检测内容：
    - tegrastats：GPU 利用率/温度/RAM/CPU
    - JetPack / CUDA / cuDNN / TensorRT 版本
    - 系统：CPU/内存/存储/网络
    """

    NAME = "jetson"
    DEVICE_FAMILIES = list(JETSON_FAMILY_MODELS.keys())

    def __init__(self):
        super().__init__()
        self.tegrastats_cmd: Optional[str] = None

    # ------------------------------------------------------------------ #
    # BaseAdapter 实现
    # ------------------------------------------------------------------ #

    def identify(self) -> str:
        """
        识别 Jetson 设备族。

        策略：读取设备树 model 文件，关键词匹配。
        """
        for path in [
            "/sys/firmware/devicetree/base/model",
            "/proc/device-tree/model",
        ]:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    model_str = f.read().strip()
                    if model_str:
                        logger.info(f"[Jetson] 设备树: {model_str}")

                        # 优先级：Orin 系列优先
                        if "Orin AGX" in model_str or "AGX Orin" in model_str:
                            return "Orin AGX"
                        if "Orin NX" in model_str:
                            return "Orin NX"
                        if "Orin Nano" in model_str:
                            return "Orin Nano"
                        if "AGX Xavier" in model_str or "Xavier AGX" in model_str:
                            return "AGX Xavier"
                        if "Xavier NX" in model_str or "Jetson NX" in model_str:
                            return "Xavier NX"
                        if "TX2" in model_str:
                            return "Nano/TX2"
                        if "Nano" in model_str or "Jetson Nano" in model_str:
                            return "Nano/TX2"

                        break
            except Exception:
                continue

        # 兜底：tegrastats 存在但无法匹配
        if not self.tegrastats_cmd:
            self.tegrastats_cmd = _find_tegrastats()
        if self.tegrastats_cmd:
            logger.warning("[Jetson] 无法识别具体型号，使用 Nano/TX2 默认")
            return "Nano/TX2"

        return ""

    def check_tools(self) -> None:
        """检测 Jetson 工具链是否可用"""
        tools: dict[str, bool] = {}

        # tegrastats
        self.tegrastats_cmd = _find_tegrastats()
        tools["tegrastats"] = self.tegrastats_cmd is not None
        if self.tegrastats_cmd:
            tools["tegrastats_path"] = self.tegrastats_cmd

        # JetPack
        jp = _detect_jetpack()
        tools["jetpack"] = jp is not None
        if jp:
            tools["jetpack_version"] = jp
            # JetPack 版本兼容性检查
            from adapters.jetson.jetpack import get_jetpack_info, check_version_compatibility
            jp_info = get_jetpack_info(jp)
            if jp_info:
                tools["expected_cuda"] = jp_info.get("cuda")
                tools["expected_tensorrt"] = jp_info.get("tensorrt")

        # CUDA
        cuda = _detect_cuda()
        tools["cuda"] = cuda is not None
        if cuda:
            tools["cuda_version"] = cuda

        # cuDNN
        cudnn = _detect_cudnn()
        tools["cudnn"] = cudnn is not None
        if cudnn:
            tools["cudnn_version"] = cudnn

        # TensorRT
        trt = _detect_tensorrt()
        tools["tensorrt"] = trt is not None
        if trt:
            tools["tensorrt_version"] = trt

        # ONNX Runtime
        stdout, _, _ = _run(
            "python3 -c 'import onnxruntime; print(onnxruntime.__version__)' 2>&1 || echo ''"
        )
        tools["onnx_runtime"] = (
            stdout and "Error" not in stdout and "Traceback" not in stdout
        )
        if tools["onnx_runtime"]:
            tools["onnx_runtime_version"] = stdout.strip()

        # 功耗模式
        from adapters.jetson.power import detect_power_mode
        power = detect_power_mode()
        if power.get("nvpmodel_installed"):
            tools["nvpmodel"] = True
            tools["power_mode"] = power.get("mode")
            tools["power_mode_name"] = power.get("name")

        # 风扇状态
        from adapters.jetson.fan import detect_fan_status
        fan = detect_fan_status()
        if fan.get("present"):
            tools["fan_present"] = True
            tools["fan_pwm"] = fan.get("pwm")
            tools["fan_mode"] = fan.get("mode")

        self.result.tools = tools
        logger.info(f"[Jetson] 工具链: {json.dumps(tools, ensure_ascii=False)}")

    def detect_npu(self) -> None:
        """
        Jetson 没有独立 NPU，通过 tegrastats 采集 GPU/系统数据。
        GPU 信息存入 gpu_status（NPU 字段统一复用此结构）。
        """
        gpu_status: dict[str, Any] = {
            "tegrastats_found": self.tegrastats_cmd is not None,
            "tegrastats_path": self.tegrastats_cmd,
        }

        if not self.tegrastats_cmd:
            self.result.gpu_status = gpu_status
            return

        # 运行 tegrastats 一次（1秒采样）
        stdout, _, code = _run(f"timeout 2 {self.tegrastats_cmd} 2>&1 || echo ''", timeout=3)
        if stdout and code != -1:
            parsed = _parse_tegrastats(stdout)
            gpu_status.update(parsed)
            gpu_status["raw_tegrastats"] = stdout

        self.result.gpu_status = gpu_status
        logger.info(f"[Jetson] GPU状态: {json.dumps(gpu_status, ensure_ascii=False)}")

    def detect_system(self) -> None:
        """检测通用系统状态"""
        system: dict[str, Any] = {}

        # 内存
        stdout, _, code = _run("cat /proc/meminfo 2>&1", timeout=5)
        if code == 0:
            mem_info = {}
            for line in stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    mem_info[k.strip()] = v.strip()
            try:
                mem_total = int(mem_info.get("MemTotal", 0)) / 1024
                mem_free = int(mem_info.get("MemFree", 0)) / 1024
                mem_available = int(mem_info.get("MemAvailable", mem_free)) / 1024
                system["memory"] = {
                    "total_mb": round(mem_total, 1),
                    "free_mb": round(mem_free, 1),
                    "available_mb": round(mem_available, 1),
                    "used_mb": round(mem_total - mem_available, 1),
                    "util_pct": round((mem_total - mem_available) / mem_total * 100, 1) if mem_total > 0 else 0,
                }
            except Exception as e:
                logger.warning(f"[Jetson] 解析 /proc/meminfo 失败: {e}")

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

        # 系统版本（从 L4T）
        if os.path.isfile("/etc/nv_tegra_release"):
            try:
                with open("/etc/nv_tegra_release", "r", errors="ignore") as f:
                    for line in f:
                        if line.startswith("VERSION="):
                            system["os"] = f"Linux L4T {line.split('=',1)[1].strip()}"
                            break
            except Exception:
                pass

        self.result.system = system
        logger.info(f"[Jetson] 系统状态: {json.dumps(system, ensure_ascii=False)}")

    def get_model_name(self) -> str:
        """返回具体型号名称"""
        family = self.result.device_family
        models = JETSON_FAMILY_MODELS.get(family, [])
        if models:
            return models[0]
        return family

    def calc_score(self) -> None:
        """
        计算 Jetson 健康评分（0-100）。

        维度（4个，各25分）：
        - GPU 利用率
        - 温度
        - 系统内存
        - 推理性能基准（TODO）
        """
        thresholds = JETSON_THRESHOLDS.get(
            self.result.device_family,
            {"temp_warn": 85, "temp_crit": 95, "util_high": 85}
        )

        breakdown: dict[str, int] = {}
        score = 0

        # 1. GPU 利用率（25分）
        gpu_util = self.result.gpu_status.get("gpu_util_pct", 0)
        if gpu_util < thresholds["util_high"]:
            breakdown["gpu_util"] = 25
        elif gpu_util < 95:
            breakdown["gpu_util"] = 15
        else:
            breakdown["gpu_util"] = 5
        score += breakdown["gpu_util"]

        # 2. 温度（25分）
        temp = self.result.gpu_status.get("temperature_c", 0)
        if temp < thresholds["temp_warn"]:
            breakdown["temp"] = 25
        elif temp < thresholds["temp_crit"]:
            breakdown["temp"] = 15
        else:
            breakdown["temp"] = 5
        score += breakdown["temp"]

        # 3. 系统内存（25分）
        sys_mem = self.result.system.get("memory", {})
        sys_util = sys_mem.get("util_pct", 0)
        if sys_util < 70:
            breakdown["sys_mem"] = 25
        elif sys_util < 85:
            breakdown["sys_mem"] = 15
        else:
            breakdown["sys_mem"] = 5
        score += breakdown["sys_mem"]

        # 4. 推理性能基准（25分，TODO：实现后替换）
        # 暂时用工具链完整度代替
        tools = self.result.tools
        tool_count = sum(1 for k in ["jetpack", "cuda", "tensorrt", "onnx_runtime"] if tools.get(k))
        if tool_count >= 4:
            breakdown["toolchain"] = 25
        elif tool_count >= 2:
            breakdown["toolchain"] = 15
        else:
            breakdown["toolchain"] = 5
        score += breakdown["toolchain"]

        self.result.score = min(100, score)
        self.result.score_breakdown = breakdown
        logger.info(f"[Jetson] 健康评分: {self.result.score}分 {breakdown}")

    def run_benchmark(self) -> None:
        """
        推理基准测试：MobileNetV2 在 Jetson GPU 上推理延迟。

        策略：
        1. 优先 TensorRT（最高效）
        2. 其次 ONNX Runtime CUDA（通用）
        3. 最后 ONNX Runtime CPU（兜底）
        4. 启发式估算作为最终兜底
        """
        from adapters.benchmark import run_tensorrt_benchmark, run_onnx_benchmark, run_heuristic_benchmark

        benchmark: dict[str, Any] = {
            "model": "MobileNetV2",
            "framework": None,
            "latency_ms": None,
            "throughput_fps": None,
            "status": "skip",
            "error": None,
        }

        tools = self.result.tools

        # 1. TensorRT（最高效）
        if tools.get("tensorrt"):
            result = run_tensorrt_benchmark(
                model_name="mobilenetv2",
                warmup=3,
                iterations=10,
            )
            if result["status"] == "success":
                self.result.benchmark = result
                return
            benchmark = result

        # 2. ONNX Runtime CUDA
        if tools.get("onnx_runtime"):
            result = run_onnx_benchmark(
                model_name="mobilenetv2",
                warmup=3,
                iterations=10,
                provider="CUDAExecutionProvider",
            )
            if result["status"] == "success":
                self.result.benchmark = result
                return
            # 3. ONNX Runtime CPU
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
