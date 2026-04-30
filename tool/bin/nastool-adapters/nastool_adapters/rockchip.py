"""
adapters/rockchip.py -- Rockchip RK3588 / RK356x 系列专项适配
"""

import os
import subprocess
from .base import BaseAdapter, AdapterResult


def _run(cmd: str, timeout: int = 5) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return ""


class RockchipAdapter(BaseAdapter):
    name = "Rockchip RK3588 / RK356x"
    chip_type = "rockchip_npu"

    def health_check(self) -> AdapterResult:
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

        # ===== A-1: RK3588 NPU 利用率检测 =====
        # 尝试多个可能的利用率路径
        npu_util_paths = [
            "/sys/class/rknpu/rknpu0/load",  # RK3588 常用
            "/sys/class/npu/npu/utilization",  # 备选路径
            "/sys/class/rknpu/devfreq/rknpu0/load",  # 另一个可能的路径
        ]
        npu_util = "unknown"
        for path in npu_util_paths:
            if os.path.exists(path):
                try:
                    util_val = int(open(path).read().strip())
                    npu_util = f"{util_val}%"
                    break
                except Exception:
                    pass
        checks["npu_utilization"] = npu_util

        # ===== A-1: NPU 内存使用检测 =====
        npu_mem_paths = [
            "/sys/class/rknpu/rknpu0/meminfo",  # RK3588 内存信息
            "/sys/kernel/debug/rknpu/mem",  # 调试接口
        ]
        npu_mem_used = "unknown"
        npu_mem_total = "unknown"
        for path in npu_mem_paths:
            if os.path.exists(path):
                try:
                    mem_content = open(path).read()
                    # 解析内存信息格式
                    if "rknpu mem:" in mem_content:
                        import re
                        match = re.search(r'rknpu mem:\s*(\d+)\s*KB', mem_content)
                        if match:
                            npu_mem_used = f"{int(match.group(1))} KB"
                    # 尝试解析总内存
                    match_total = re.search(r'total:\s*(\d+)\s*KB', mem_content)
                    if match_total:
                        npu_mem_total = f"{int(match_total.group(1))} KB"
                    break
                except Exception:
                    pass
        checks["npu_mem_used"] = npu_mem_used
        checks["npu_mem_total"] = npu_mem_total

        # ===== A-2: RK3568 vs RK3588 芯片识别 =====
        # 通过 /proc/cpuinfo 或 /sys/firmware/devicetree/base/model 识别芯片型号
        chip_model = _run(
            "cat /proc/cpuinfo 2>/dev/null | grep -i 'model name' | head -1 | cut -d: -f2 | xargs || "
            "cat /sys/firmware/devicetree/base/model 2>/dev/null | xargs || "
            "cat /sys/class/socinfo/socinfo 2>/dev/null | grep model || echo 'unknown'"
        )
        checks["chip_model"] = chip_model

        # RK3588 特有检测：MIPI 摄像头接口
        mipi_paths = [
            "/dev/video0",  # 可能的摄像头设备
            "/dev/video20",  # RK3588 MIPI CSI
        ]
        mipi_detected = []
        for mipi_path in mipi_paths:
            if os.path.exists(mipi_path):
                mipi_detected.append(mipi_path)
        checks["mipi_devices"] = ",".join(mipi_detected) if mipi_detected else "none"

        # ===== A-4: 驱动版本检测 =====
        # rockchip 驱动版本
        rockchip_driver_ver = _run(
            "modinfo rockchip 2>/dev/null | grep -i version | head -1 | awk '{print $2}' || "
            "cat /sys/module/rockchip/version 2>/dev/null || echo 'unknown'"
        )
        checks["rockchip_driver_ver"] = rockchip_driver_ver

        # rknpu 驱动版本
        rknpu_driver_ver = _run(
            "modinfo rknpu 2>/dev/null | grep -i version | head -1 | awk '{print $2}' || "
            "cat /sys/module/rknpu/version 2>/dev/null || echo 'unknown'"
        )
        checks["rknpu_driver_ver"] = rknpu_driver_ver

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
            ops.append(f"CPU governor -> performance: {'成功' if r.returncode == 0 else '需要sudo'}")
            # 最高 DDR 频率
            r2 = subprocess.run(
                "cat /sys/class/devfreq/dmc/available_frequencies 2>/dev/null | "
                "awk '{print $NF}' | xargs -I{} "
                "echo {} > /sys/class/devfreq/dmc/max_freq 2>&1",
                shell=True,
                timeout=5,
            )
            ops.append(f"DDR -> max freq: {'成功' if r2.returncode == 0 else '需要sudo'}")
        return ops
