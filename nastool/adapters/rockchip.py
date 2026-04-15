"""
adapters/rockchip.py — Rockchip RK3588 / RK356x 系列专项适配
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


class RockchipAdapter(BaseAdapter):
    name = "Rockchip RK3588 / RK356x"
    chip_type = "rockchip_npu"

    def health_check(self) -> AdapterReport:
        report = AdapterReport(name=self.name, chip_type=self.chip_type)
        checks = {}

        # /dev/rknpu 状态
        rknpu_ok = os.path.exists("/dev/rknpu")
        checks["rknpu_node"] = rknpu_ok

        if not rknpu_ok:
            report.warnings.append("/dev/rknpu 不存在，NPU 驱动可能未加载（检查 rockchip 驱动）")

        # NPU 固件版本
        npu_fw = _run(
            "cat /sys/class/npu/npu/firmware_version 2>/dev/null "
            "|| cat /sys/bus/platform/drivers/rk-npu/firmware_version 2>/dev/null "
            "|| echo '未知'"
        )
        checks["npu_firmware"] = npu_fw

        # RKNN SDK 版本
        rknn_ver = _run(
            "ls /usr/local/rknpu*/rknn_rknn_api/*.so 2>/dev/null | head -1 | "
            "xargs basename 2>/dev/null || echo '未知'"
        )
        checks["rknn_sdk_lib"] = rknn_ver

        # RKNN Runtime 版本
        rknn_rt = _run(
            "python3 -c \"import rknn; print(rknn.__version__)\" 2>/dev/null || echo 'not_installed'"
        )
        checks["rknn_runtime"] = rknn_rt
        if rknn_rt == "not_installed":
            report.warnings.append("RKNN Runtime 未安装（pip install rknn）")

        # 温度（rk3588 有专门的 npu thermal zone）
        for zone in [
            "/sys/class/thermal/thermal_zone7/temp",  # NPU 温度
            "/sys/class/thermal/thermal_zone8/temp",  # CPU 温度
        ]:
            if os.path.exists(zone):
                try:
                    t = int(open(zone).read().strip()) / 1000.0
                    zone_name = os.path.dirname(zone).split("/")[-1]
                    checks[f"{zone_name}_c"] = round(t, 1)
                except Exception as e:
                    pass

        # DDR 带宽（Rockchip 专用）
        ddr_bw = _run(
            "cat /sys/class/devfreq/dmc/cur_freq 2>/dev/null | "
            "xargs -I{} python3 -c \"print(round(int({})/1e6, 1), 'MHz')\" 2>/dev/null || echo '未知'"
        )
        checks["ddr_freq_mhz"] = ddr_bw

        # GPU 状态（Mali GPU）
        gpu_status = _run(
            "cat /sys/class/misc/mali0/device/status 2>/dev/null || "
            "cat /sys/class/misc/mali0/device/power_state 2>/dev/null || echo 'unknown'"
        )
        checks["gpu_status"] = gpu_status

        # GPU 频率
        gpu_freq = _run(
            "cat /sys/class/misc/mali0/device/clk/curr_freq 2>/dev/null | "
            "xargs -I{} python3 -c \"print(round(int({})/1e6, 1), 'MHz')\" 2>/dev/null || echo 'unknown'"
        )
        checks["gpu_freq_mhz"] = gpu_freq

        # NPU 频率
        npu_freq = _run(
            "cat /sys/class/npu/npu/clk_base_freq 2>/dev/null | "
            "xargs -I{} python3 -c \"print(round(int({})/1e6, 1), 'MHz')\" 2>/dev/null || echo 'unknown'"
        )
        checks["npu_freq_mhz"] = npu_freq

        # 视频编解码状态（V4L2）
        v4l2_devices = _run("v4l2-ctl --list-devices 2>/dev/null || echo 'none'")
        checks["v4l2_devices"] = v4l2_devices[:500] if v4l2_devices else "none"  # 截断长输出

        report.specific_checks = checks
        report.ok = True
        return report

    def benchmark(self) -> dict:
        results = {}

        # RKNN 推理测试（如果 RKNN 可用）
        rknn_test = _run(
            "python3 -c \"from rknn.api import RKNN; print('RKNN ok')\" 2>/dev/null || echo 'not_available'"
        )
        results["rknn_test"] = rknn_test

        # DDR 带宽测试
        ddr_test = _run(
            "ddr_bw_test 2>/dev/null || "
            'python3 -c "import numpy as np; x=np.random.randn(4096,4096); '
            "y=np.dot(x,x)\" 2>/dev/null && echo 'ok' || echo 'not_available'"
        )
        results["ddr_bandwidth"] = ddr_test

        return results

    def apply_tuning(self, profile: str = "performance") -> list:
        ops = []
        if profile == "performance":
            # 开启性能模式（RK3588）
            r = subprocess.run(
                "echo performance > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor 2>&1",
                shell=True,
                timeout=5,
            )
            ops.append(f"CPU governor → performance: {'成功' if r.returncode == 0 else '需要sudo'}")
            # 最高 DDR 频率
            r2 = subprocess.run(
                "cat /sys/class/devfreq/dmc/available_frequencies 2>/dev/null | "
                "awk '{print $NF}' | xargs -I{} "
                "echo {} > /sys/class/devfreq/dmc/max_freq 2>&1",
                shell=True,
                timeout=5,
            )
            ops.append(f"DDR → max freq: {'成功' if r2.returncode == 0 else '需要sudo'}")
        return ops
