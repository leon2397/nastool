# -*- coding: utf-8 -*-
"""
adapters/sophon.py -- SOPHON（算能）AI 芯片专项适配
支持：BM1688 / BM1684 / BM1690 / SE5 / SE7 / SM5 / SM7 等
"""

import os
import subprocess
from .base import BaseAdapter, AdapterReport


def _run(cmd: str, timeout: int = 5) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return ""


class SophonAdapter(BaseAdapter):
    """SOPHON TPU 设备适配器"""

    name = "SOPHON TPU"
    chip_type = "sophon_tpu"

    def health_check(self) -> AdapterReport:
        report = AdapterReport(name=self.name, chip_type=self.chip_type)
        checks = {}

        # 1. SDK 版本
        sdk_ver = _run("cat /opt/sophon/version.txt 2>/dev/null || echo ''")
        checks["sophon_sdk_version"] = sdk_ver
        if not sdk_ver:
            report.warnings.append("SophonSDK 未安装或路径不正确")

        # 2. TPU 设备
        tpu_devs = _run("ls /dev/bm* 2>/dev/null || echo ''")
        checks["tpu_devices"] = tpu_devs
        checks["tpu_available"] = bool(tpu_devs)
        if not tpu_devs:
            report.warnings.append("TPU 设备未找到，请检查驱动是否加载")

        # 3. BMCompiler 版本
        bmcompiler = _run("bm_compiler --version 2>/dev/null || echo ''")
        checks["bmcompiler_version"] = bmcompiler

        # 4. BMRuntime 版本
        bmruntime = _run("bm_runtime --version 2>/dev/null || echo ''")
        checks["bmruntime_version"] = bmruntime

        # 5. TPU 利用率（类似 nvidia-smi）
        tpu_smi = _run("bm-smi 2>/dev/null || echo ''")
        checks["tpu_smi"] = tpu_smi

        # 6. 内存状态
        memory = _run("bm-smi --memory 2>/dev/null || free -h")
        checks["memory_info"] = memory

        # 7. 温度（如果有）
        temp = _run("cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null")
        if temp:
            try:
                temps = [int(t) / 1000.0 for t in temp.strip().split("\n") if t]
                checks["temperatures_c"] = temps
            except Exception as e:
                pass

        # 8. Python Sophon 库
        sophon_py = _run(
            "python3 -c 'import sophon; print(sophon.__version__)' 2>/dev/null || echo ''"
        )
        checks["sophon_python_version"] = sophon_py

        # 9. BMtorch 版本
        bmtorch = _run(
            "python3 -c 'import bmtorch; print(bmtorch.__version__)' 2>/dev/null || echo ''"
        )
        checks["bmtorch_version"] = bmtorch

        # 10. 视频编解码能力
        vpu_decode = _run("cat /proc/bm-vpu/decode 2>/dev/null || echo ''")
        vpu_encode = _run("cat /proc/bm-vpu/encode 2>/dev/null || echo ''")
        checks["vpu_decode"] = vpu_decode
        checks["vpu_encode"] = vpu_encode

        # 11. SAIL (Sophon AI Library) 检测
        sail_ver = _run(
            "python3 -c 'import sail; print(sail.__version__)' 2>/dev/null || echo ''"
        )
        checks["sail_version"] = sail_ver
        if not sail_ver:
            report.warnings.append("SAIL 未安装（pip install sophon-sail）")

        # 12. BMChip 类型检测
        chip_type = _run(
            "cat /sys/class/bm/bmdev*/chip_id 2>/dev/null || "
            "bm-smi -i 2>/dev/null | grep -i 'chip' | head -1 || echo 'unknown'"
        )
        checks["chip_type"] = chip_type

        # 13. PCIe 板卡检测
        pcie_devs = _run("lspci | grep -i 'bm\|sophon\|bmtpu' 2>/dev/null || echo ''")
        checks["pcie_devices"] = pcie_devs if pcie_devs else "none"

        # 14. Docker TPU 运行时检测
        docker_tpu = _run(
            "docker images 2>/dev/null | grep -i 'sophon\\|bm\\|tpu' || echo ''"
        )
        checks["docker_tpu_images"] = docker_tpu if docker_tpu else "none"

        # 15. PCIe 拓扑信息
        pcie_link = _run(
            "cat /sys/bus/pci/devices/*/uevent 2>/dev/null | grep -A5 'bm' | head -20 || echo ''"
        )
        checks["pcie_topology"] = pcie_link[:500] if pcie_link else "none"

        report.specific_checks = checks
        report.ok = bool(tpu_devs) or bool(sdk_ver)
        return report

    def benchmark(self) -> dict:
        """SOPHON TPU 基准测试"""
        results = {}

        # TPU 性能测试
        tpu_perf = _run("bm-smi --performance 2>/dev/null || echo ''")
        results["tpu_performance"] = tpu_perf

        # 检查可用的 bmodel
        models = _run("find /opt/sophon/models -name '*.bmodel' 2>/dev/null | head -10")
        results["available_models"] = models.split("\n") if models else []

        return results

    def get_chip_info(self) -> dict:
        """获取芯片信息"""
        info = {}

        # 尝试从设备节点读取
        chip_id = _run("cat /sys/class/bm/bmdev*/chip_id 2>/dev/null || echo ''")
        if chip_id:
            info["chip_id"] = chip_id

        # 从 SDK 配置读取
        board_info = _run("cat /opt/sophon/board.conf 2>/dev/null || echo ''")
        if board_info:
            info["board_config"] = board_info

        return info

    def compile_model(
        self, model_path: str, output_path: str, target: str = "bm1688", **kwargs
    ) -> dict:
        """
        编译模型为 bmodel

        Args:
            model_path: 输入模型路径（ONNX/TFLite）
            output_path: 输出 bmodel 路径
            target: 目标芯片（bm1688/bm1684/bm1690）
        """
        result = {"success": False, "command": "", "output": "", "error": ""}

        # 构建编译命令
        cmd = f"bm_compile --model {model_path} --output {output_path} --target {target}"

        # 添加可选参数
        if kwargs.get("quantize"):
            cmd += f" --quantize {kwargs['quantize']}"
        if kwargs.get("calibration_data"):
            cmd += f" --calibration {kwargs['calibration_data']}"
        if kwargs.get("shapes"):
            cmd += f" --shapes {kwargs['shapes']}"

        result["command"] = cmd

        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            result["output"] = r.stdout
            result["error"] = r.stderr
            result["success"] = r.returncode == 0
        except Exception as e:
            result["error"] = str(e)

        return result

    def load_bmodel(self, model_path: str) -> dict:
        """
        加载 bmodel 模型信息

        Args:
            model_path: bmodel 文件路径
        """
        result = {"success": False, "info": {}}

        # 使用 bm_model_info 工具
        info = _run(f"bm_model_info {model_path} 2>/dev/null || echo ''")
        if info:
            result["info"]["raw"] = info
            result["success"] = True

        # 检查文件大小
        if os.path.exists(model_path):
            result["info"]["size_mb"] = os.path.getsize(model_path) / 1024 / 1024

        return result
