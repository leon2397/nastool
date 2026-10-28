"""
adapters/nvidia_jetson.py — NVIDIA Jetson 系列专项适配
支持：Jetson Nano / Xavier NX / AGX Orin / TX2 / ...
"""
import os
import subprocess
from .base import BaseAdapter, AdapterReport


def _run(cmd: str, timeout: int = 5) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, errors="replace", timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


class NvidiaJetsonAdapter(BaseAdapter):
    name = "NVIDIA Jetson"
    chip_type = "nvidia_gpu"

    def health_check(self) -> AdapterReport:
        report = AdapterReport(name=self.name, chip_type=self.chip_type)
        checks = {}

        # 1. jetson_clocks 状态
        jc_status = _run("jetson_clocks --show 2>/dev/null | head -3")
        checks["jetson_clocks_active"] = bool(jc_status)
        if not jc_status:
            report.warnings.append(
                "jetson_clocks 未运行，建议执行 'sudo jetson_clocks' 开启性能模式"
            )

        # 2. 电源模式
        pwr_mode = _run("nvpmodel -q 2>/dev/null | grep 'NV Power Mode' || echo ''")
        checks["power_mode"] = pwr_mode
        if "MAX" not in pwr_mode and "15W" not in pwr_mode:
            report.warnings.append(
                f"电源模式可能不是最高性能: {pwr_mode}"
            )

        # 3. GPU 频率
        gpu_freq = _run(
            "cat /sys/devices/gpu.0/devfreq/17000000.gpu available_frequencies 2>/dev/null | "
            "awk '{print $NF}' | xargs -I{} echo '{} MHz' || echo '未知'"
        )
        checks["gpu_freq"] = gpu_freq

        # 4. EMC 内存带宽
        emc_freq = _run(
            "cat /sys/kernel/debug/clk/ Override | grep -i emc | awk '{print $NF}' 2>/dev/null "
            "|| cat /sys/class/devfreq/17000000.gpu/available_frequencies 2>/dev/null | "
            "awk '{print $NF}' | xargs -I{} echo '{} MHz' || echo '未知'"
        )
        checks["emc_freq"] = emc_freq

        # 5. 温度传感器（Jetson 专用）
        ts = {}
        for zone in [
            "/sys/devices/virtual/thermal/thermal_zone0/temp",
            "/sys/devices/virtual/thermal/thermal_zone1/temp",
            "/sys/class/thermal/thermal_zone0/temp",
        ]:
            if os.path.exists(zone):
                try:
                    t = int(open(zone).read().strip()) / 1000.0
                    ts[zone.split("/")[-2]] = round(t, 1)
                except Exception:
                    pass
        checks["temperatures_c"] = ts

        # 6. NVIDIA GPU 信息
        smi = _run("nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total "
                   "--format=csv,noheader 2>/dev/null || echo ''")
        checks["nvidia_smi"] = smi

        # 7. NVDEC / NVENC 编码器
        for enc in ["nvdec", "nvenc"]:
            path = f"/dev/{enc}"
            checks[f"{enc}_available"] = os.path.exists(path)

        report.specific_checks = checks
        report.ok = True
        return report

    def benchmark(self) -> dict:
        """Jetson 专用基准测试"""
        results = {}

        # GPU BFLOPS 粗估
        smi = _run(
            "nvidia-smi --query-gpu=clocks.current.sm,clocks.current.memory "
            "--format=csv,noheader 2>/dev/null || echo ''"
        )
        results["gpu_clock_info"] = smi

        # TensorRT 推理测试（如果安装了 TensorRT）
        trt_out = _run(
            "python3 -c \"import tensorrt; print(tensorrt.__version__)\" 2>/dev/null || echo 'not_installed'"
        )
        results["tensorrt_available"] = (trt_out != "not_installed")
        results["tensorrt_version"] = trt_out

        return results

    def apply_tuning(self, profile: str = "performance") -> list:
        ops = []
        if profile == "performance":
            r = subprocess.run("sudo jetson_clocks 2>&1", shell=True, timeout=30)
            ops.append(f"jetson_clocks: {'成功' if r.returncode == 0 else '需要sudo权限'}")
            r2 = subprocess.run("sudo nvpmodel -m 0 2>&1", shell=True, timeout=10)
            ops.append(f"nvpmodel MAX: {'成功' if r2.returncode == 0 else '需要sudo权限'}")
        elif profile == "power_save":
            r = subprocess.run("sudo nvpmodel -m 1 2>&1", shell=True, timeout=10)
            ops.append(f"nvpmodel 5W: {'成功' if r.returncode == 0 else '需要sudo权限'}")
        return ops
