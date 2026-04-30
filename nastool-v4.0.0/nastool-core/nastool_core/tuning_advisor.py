# -*- coding: utf-8 -*-
"""
nastool-core Tuning Advisor

基于检测结果给出 RK3588/RK3568 性能调优建议。
支持 CPU/DDR/NPU 频率推荐、散热方案建议。

Usage:
    advisor = TuningAdvisor()
    recommendations = advisor.analyze(check_results)
    for rec in recommendations:
        print(f"[{rec.priority}] {rec.title}: {rec.suggestion}")
"""

import subprocess
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum


PRIORITY_SYMBOLS = {
    "critical": "[!!!]",
    "high": "[!!]",
    "medium": "[!]",
    "low": "[i]",
}


@dataclass
class TuningRecommendation:
    """调优建议"""
    category: str
    priority: str
    title: str
    current_value: str
    recommended_value: str
    suggestion: str
    impact: str
    requires_root: bool = False
    auto_fixable: bool = False
    fix_command: Optional[str] = None
    fix_callback: Optional[Callable[[], bool]] = None

    def __str__(self):
        icon = PRIORITY_SYMBOLS.get(self.priority, "[?]")
        root_flag = " [ROOT]" if self.requires_root else ""
        auto_flag = " [AUTO]" if self.auto_fixable else ""
        return f"{icon} [{self.category.upper()}] {self.title}{root_flag}{auto_flag}\n    Current: {self.current_value}\n    Recommended: {self.recommended_value}\n    Suggestion: {self.suggestion}\n    Impact: {self.impact}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "current_value": self.current_value,
            "recommended_value": self.recommended_value,
            "suggestion": self.suggestion,
            "impact": self.impact,
            "requires_root": self.requires_root,
            "auto_fixable": self.auto_fixable,
        }


class ChipSpecs:
    """芯片规格定义"""
    SPECS = {
        "RK3588": {
            "cpu_freq_mhz": {"min": 408, "max": 2400, "perf": 2400, "powersave": 408},
            "ddr_freq_mhz": {"min": 528, "max": 2112, "perf": 2112, "powersave": 528},
            "npu_freq_mhz": {"min": 200, "max": 1000, "perf": 1000, "powersave": 200},
            "gpu_freq_mhz": {"min": 200, "max": 1000, "perf": 1000, "powersave": 200},
            "thermal_warning_c": 75,
            "thermal_critical_c": 85,
            "thermal_throttle_c": 80,
        },
        "RK3568": {
            "cpu_freq_mhz": {"min": 408, "max": 2000, "perf": 2000, "powersave": 408},
            "ddr_freq_mhz": {"min": 528, "max": 1560, "perf": 1560, "powersave": 528},
            "npu_freq_mhz": {"min": 100, "max": 800, "perf": 800, "powersave": 100},
            "gpu_freq_mhz": {"min": 200, "max": 800, "perf": 800, "powersave": 200},
            "thermal_warning_c": 70,
            "thermal_critical_c": 80,
            "thermal_throttle_c": 75,
        },
        "RK3566": {
            "cpu_freq_mhz": {"min": 408, "max": 1800, "perf": 1800, "powersave": 408},
            "ddr_freq_mhz": {"min": 528, "max": 1560, "perf": 1560, "powersave": 528},
            "npu_freq_mhz": {"min": 100, "max": 600, "perf": 600, "powersave": 100},
            "gpu_freq_mhz": {"min": 200, "max": 800, "perf": 800, "powersave": 200},
            "thermal_warning_c": 70,
            "thermal_critical_c": 80,
            "thermal_throttle_c": 75,
        },
        "RK3399": {
            "cpu_freq_mhz": {"min": 400, "max": 1800, "perf": 1800, "powersave": 400},
            "ddr_freq_mhz": {"min": 400, "max": 1200, "perf": 1200, "powersave": 400},
            "npu_freq_mhz": {"min": 100, "max": 600, "perf": 600, "powersave": 100},
            "gpu_freq_mhz": {"min": 200, "max": 600, "perf": 600, "powersave": 200},
            "thermal_warning_c": 80,
            "thermal_critical_c": 90,
            "thermal_throttle_c": 85,
        },
        "RK3326": {
            "cpu_freq_mhz": {"min": 408, "max": 1300, "perf": 1300, "powersave": 408},
            "ddr_freq_mhz": {"min": 528, "max": 800, "perf": 800, "powersave": 528},
            "npu_freq_mhz": {"min": 100, "max": 500, "perf": 500, "powersave": 100},
            "gpu_freq_mhz": {"min": 200, "max": 500, "perf": 500, "powersave": 200},
            "thermal_warning_c": 75,
            "thermal_critical_c": 85,
            "thermal_throttle_c": 80,
        },
        "Jetson": {
            "cpu_freq_mhz": {"min": 408, "max": 2200, "perf": 2200, "powersave": 408},
            "ddr_freq_mhz": {"min": 528, "max": 1600, "perf": 1600, "powersave": 528},
            "npu_freq_mhz": {"min": 100, "max": 800, "perf": 800, "powersave": 100},
            "gpu_freq_mhz": {"min": 200, "max": 1000, "perf": 1000, "powersave": 200},
            "thermal_warning_c": 80,
            "thermal_critical_c": 90,
            "thermal_throttle_c": 85,
        },
        "Generic": {
            "cpu_freq_mhz": {"min": 408, "max": 2000, "perf": 2000, "powersave": 408},
            "ddr_freq_mhz": {"min": 528, "max": 1500, "perf": 1500, "powersave": 528},
            "npu_freq_mhz": {"min": 100, "max": 800, "perf": 800, "powersave": 100},
            "gpu_freq_mhz": {"min": 200, "max": 800, "perf": 800, "powersave": 200},
            "thermal_warning_c": 75,
            "thermal_critical_c": 85,
            "thermal_throttle_c": 80,
        },
    }

    @classmethod
    def get_specs(cls, chip_model: str) -> Dict[str, Any]:
        """根据芯片型号获取规格"""
        chip_upper = chip_model.upper()
        for key in cls.SPECS:
            if key.upper() in chip_upper:
                return cls.SPECS[key].copy()
        return cls.SPECS["Generic"].copy()


class AutoFixer:
    """自动修复执行器"""

    @staticmethod
    def set_cpu_governor(governor: str = "performance") -> bool:
        """设置 CPU governor"""
        try:
            path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
            if os.path.exists(path):
                with open(path, 'w') as f:
                    f.write(governor)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def set_ddr_freq(freq_mhz: int) -> bool:
        """设置 DDR 频率"""
        try:
            path = "/sys/class/devfreq/dmc/max_freq"
            if os.path.exists(path):
                with open(path, 'w') as f:
                    f.write(str(freq_mhz * 1000000))
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def drop_caches() -> bool:
        """清理缓存"""
        try:
            with open("/proc/sys/vm/drop_caches", 'w') as f:
                f.write('3')
            return True
        except Exception:
            pass
        return False

    @staticmethod
    def enable_npu() -> bool:
        """启用 NPU"""
        try:
            result = subprocess.run(
                ["modprobe", "rknpu"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False


class TuningAdvisor:
    """
    RK3588/RK3568 性能调优顾问

    基于检测结果，给出针对性的调优建议。
    """

    PROFILES = {
        "performance": {
            "description": "Maximum performance, higher power consumption",
            "cpu_governor": "performance",
            "ddr_policy": "max_freq",
            "npu_policy": "max_freq",
            "gpu_policy": "max_freq",
            "fan_policy": "aggressive",
        },
        "balanced": {
            "description": "Balance between performance and power",
            "cpu_governor": "ondemand",
            "ddr_policy": "auto",
            "npu_policy": "auto",
            "gpu_policy": "auto",
            "fan_policy": "normal",
        },
        "powersave": {
            "description": "Lowest power consumption, limited performance",
            "cpu_governor": "powersave",
            "ddr_policy": "min_freq",
            "npu_policy": "min_freq",
            "gpu_policy": "min_freq",
            "fan_policy": "quiet",
        },
    }

    COOLING_SOLUTIONS = [
        {
            "name": "Passive Cooling",
            "max_tdp": 5,
            "suitable": ["RK3566", "RK3568"],
            "description": "Aluminum heatsink, no fan",
            "pros": "Silent, maintenance-free",
            "cons": "Throttling under sustained high load",
        },
        {
            "name": "Active Cooling (Small Fan)",
            "max_tdp": 10,
            "suitable": ["RK3588", "RK3568"],
            "description": "Heatsink + 5V small fan",
            "pros": "Cost-effective, good cooling",
            "cons": "Some noise",
        },
        {
            "name": "Active Cooling (PWM Fan)",
            "max_tdp": 15,
            "suitable": ["RK3588"],
            "description": "PWM intelligent fan",
            "pros": "Controllable noise, excellent cooling",
            "cons": "Requires GPIO control",
        },
        {
            "name": "Liquid Cooling",
            "max_tdp": 25,
            "suitable": ["RK3588"],
            "description": "Water cooling block + pump + radiator",
            "pros": "Ultimate cooling, completely silent",
            "cons": "High cost, large size",
        },
    ]

    def __init__(self, chip_model: str = "RK3588"):
        """
        初始化调优顾问

        Args:
            chip_model: 芯片型号 (RK3588 / RK3568 / RK3566 / RK3399 / Jetson)
        """
        self.chip_model = chip_model.upper()
        self.specs = ChipSpecs.get_specs(chip_model)

    def analyze(self, check_results: list) -> List[TuningRecommendation]:
        """
        分析检测结果，生成调优建议

        Args:
            check_results: CheckResult 列表

        Returns:
            TuningRecommendation 列表
        """
        recommendations = []

        values = {}
        for r in check_results:
            if hasattr(r, 'check_id'):
                values[r.check_id] = r
            elif isinstance(r, dict):
                values[r.get('check_id', '')] = r

        recommendations.extend(self._analyze_cpu(values))
        recommendations.extend(self._analyze_thermal(values))
        recommendations.extend(self._analyze_npu(values))
        recommendations.extend(self._analyze_ddr(values))
        recommendations.extend(self._analyze_gpu(values))
        recommendations.extend(self._analyze_storage(values))
        recommendations.extend(self._analyze_system(values))

        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 99))

        return recommendations

    def _analyze_cpu(self, values: dict) -> List[TuningRecommendation]:
        """CPU 频率与调度分析"""
        recs = []

        cpu_gov = self._get_value(values, "cpu_governor", "")
        if cpu_gov and cpu_gov != "performance":
            rec = TuningRecommendation(
                category="cpu",
                priority="medium",
                title="CPU governor non-performance mode",
                current_value=cpu_gov,
                recommended_value="performance",
                suggestion=(
                    "For inference-intensive tasks, set CPU governor to performance: "
                    "echo performance | sudo tee /sys/devices/system/cpu/cpufreq/policy0/scaling_governor"
                ),
                impact="CPU frequency locked to maximum, inference latency reduced by 10-30%",
                requires_root=True,
                auto_fixable=True,
                fix_command="echo performance | sudo tee /sys/devices/system/cpu/cpufreq/policy0/scaling_governor",
                fix_callback=lambda: AutoFixer.set_cpu_governor("performance")
            )
            recs.append(rec)

        cpu_freq = self._parse_mhz(self._get_value(values, "cpu_freq_mhz", ""))
        if cpu_freq and cpu_freq < self.specs["cpu_freq_mhz"]["perf"] * 0.8:
            recs.append(TuningRecommendation(
                category="cpu",
                priority="high",
                title="CPU frequency far below maximum",
                current_value=f"{cpu_freq} MHz",
                recommended_value=f"{self.specs['cpu_freq_mhz']['perf']} MHz",
                suggestion="Check CPU governor settings and thermal status, may be throttling",
                impact="Increasing CPU frequency can significantly improve general computing performance",
                requires_root=True,
            ))

        return recs

    def _analyze_thermal(self, values: dict) -> List[TuningRecommendation]:
        """散热与温度分析"""
        recs = []

        npu_temp = self._parse_temp(self._get_value(values, "npu_temp_c", ""))
        if npu_temp:
            if npu_temp >= self.specs["thermal_critical_c"]:
                recs.append(TuningRecommendation(
                    category="thermal",
                    priority="critical",
                    title="NPU temperature danger",
                    current_value=f"{npu_temp}C",
                    recommended_value=f"<{self.specs['thermal_warning_c']}C",
                    suggestion=(
                        "NPU temperature at critical level! Check cooling immediately: "
                        "1) Verify heatsink installation "
                        "2) Check if fan is running "
                        "3) Clean dust "
                        "4) Consider upgrading cooling solution"
                    ),
                    impact="Overheating causes NPU throttling, inference performance drops 50%+",
                    requires_root=False,
                ))
            elif npu_temp >= self.specs["thermal_warning_c"]:
                recs.append(TuningRecommendation(
                    category="thermal",
                    priority="high",
                    title="NPU temperature high",
                    current_value=f"{npu_temp}C",
                    recommended_value=f"<{self.specs['thermal_warning_c']}C",
                    suggestion="Improve cooling conditions, check fan speed and airflow design",
                    impact="High temperature causes intermittent NPU throttling, unstable inference latency",
                    requires_root=False,
                ))

        cpu_temp = self._parse_temp(self._get_value(values, "cpu_temp_c", ""))
        if cpu_temp and cpu_temp >= self.specs["thermal_warning_c"]:
            recs.append(TuningRecommendation(
                category="thermal",
                priority="high",
                title="CPU temperature high",
                current_value=f"{cpu_temp}C",
                recommended_value=f"<{self.specs['thermal_warning_c']}C",
                suggestion="Improve CPU cooling: apply thermal paste, increase airflow, upgrade heatsink",
                impact="High temperature triggers CPU throttling, overall performance degradation",
                requires_root=False,
            ))

        cooling = self._recommend_cooling(npu_temp, cpu_temp)
        if cooling:
            recs.append(TuningRecommendation(
                category="thermal",
                priority="low",
                title=f"Recommended cooling: {cooling['name']}",
                current_value=f"NPU={npu_temp or 'N/A'}C, CPU={cpu_temp or 'N/A'}C",
                recommended_value=cooling["description"],
                suggestion=f"{cooling['pros']}. Note: {cooling['cons']}",
                impact="Better cooling prevents throttling and maintains stable performance",
                requires_root=False,
            ))

        return recs

    def _analyze_npu(self, values: dict) -> List[TuningRecommendation]:
        """NPU 状态分析"""
        recs = []

        npu_driver = self._get_value(values, "rknpu_node", "")
        if npu_driver in ("False", "false", False):
            rec = TuningRecommendation(
                category="npu",
                priority="critical",
                title="NPU driver not loaded",
                current_value="/dev/rknpu not found",
                recommended_value="/dev/rknpu exists",
                suggestion=(
                    "Install Rockchip NPU driver: "
                    "1) sudo apt update && sudo apt install rockchip-npu "
                    "2) Or compile from https://github.com/rockchip-linux/rknpu "
                    "3) Ensure kernel version matches driver version"
                ),
                impact="NPU unavailable, inference must use CPU, performance drops 10-50x",
                requires_root=True,
                auto_fixable=True,
                fix_command="sudo modprobe rknpu",
                fix_callback=AutoFixer.enable_npu
            )
            recs.append(rec)

        rknn_rt = self._get_value(values, "rknn_runtime", "")
        if rknn_rt in ("not_installed", "False", "false", ""):
            recs.append(TuningRecommendation(
                category="npu",
                priority="high",
                title="RKNN Runtime not installed",
                current_value="not installed",
                recommended_value="rknn-toolkit2 >= 2.0.0",
                suggestion=(
                    "Install RKNN Toolkit2: "
                    "pip install rknn-toolkit2 "
                    "or get from https://github.com/rockchip-linux/rknn-toolkit2"
                ),
                impact="Cannot use RKNN model inference, must use ONNX Runtime",
                requires_root=False,
            ))

        npu_util = self._parse_pct(self._get_value(values, "npu_utilization", ""))
        if npu_util is not None and npu_util < 30:
            recs.append(TuningRecommendation(
                category="npu",
                priority="medium",
                title="NPU utilization low",
                current_value=f"{npu_util}%",
                recommended_value=">70%",
                suggestion=(
                    "Low NPU utilization possible causes: "
                    "1) Model not converted to RKNN format "
                    "2) Batch size too small "
                    "3) Data preprocessing on CPU becomes bottleneck "
                    "Increase batch_size or use multi-threaded data loading"
                ),
                impact="After optimization, NPU utilization can reach 80%+, throughput improved 2-3x",
                requires_root=False,
            ))

        npu_freq = self._parse_mhz(self._get_value(values, "npu_freq_mhz", ""))
        if npu_freq and npu_freq < self.specs["npu_freq_mhz"]["perf"] * 0.8:
            recs.append(TuningRecommendation(
                category="npu",
                priority="medium",
                title="NPU frequency low",
                current_value=f"{npu_freq} MHz",
                recommended_value=f"{self.specs['npu_freq_mhz']['perf']} MHz",
                suggestion="Check NPU frequency policy: cat /sys/class/npu/npu/clk_base_freq",
                impact="Increasing NPU frequency reduces inference latency",
                requires_root=True,
            ))

        return recs

    def _analyze_ddr(self, values: dict) -> List[TuningRecommendation]:
        """DDR 带宽分析"""
        recs = []

        ddr_freq = self._parse_mhz(self._get_value(values, "ddr_freq_mhz", ""))
        if ddr_freq and ddr_freq < self.specs["ddr_freq_mhz"]["perf"] * 0.7:
            perf_freq = self.specs["ddr_freq_mhz"]["perf"]
            rec = TuningRecommendation(
                category="ddr",
                priority="high",
                title="DDR frequency too low",
                current_value=f"{ddr_freq} MHz",
                recommended_value=f"{perf_freq} MHz",
                suggestion=(
                    f"Low DDR frequency affects model loading and inference throughput. "
                    f"Set DDR to maximum frequency: "
                    f"echo {perf_freq}000000 | sudo tee /sys/class/devfreq/dmc/max_freq"
                ),
                impact="DDR bandwidth doubled, model loading time reduced 30-50%",
                requires_root=True,
                auto_fixable=True,
                fix_command=f"echo {perf_freq}000000 | sudo tee /sys/class/devfreq/dmc/max_freq",
                fix_callback=lambda: AutoFixer.set_ddr_freq(perf_freq)
            )
            recs.append(rec)

        return recs

    def _analyze_gpu(self, values: dict) -> List[TuningRecommendation]:
        """GPU (Mali) 分析"""
        recs = []

        gpu_freq = self._parse_mhz(self._get_value(values, "gpu_freq_mhz", ""))
        if gpu_freq and gpu_freq < self.specs["gpu_freq_mhz"]["perf"] * 0.7:
            recs.append(TuningRecommendation(
                category="gpu",
                priority="medium",
                title="GPU frequency low",
                current_value=f"{gpu_freq} MHz",
                recommended_value=f"{self.specs['gpu_freq_mhz']['perf']} MHz",
                suggestion="Check Mali GPU frequency policy, for video encoding/decoding tasks consider locking to maximum frequency",
                impact="Increasing GPU frequency improves video encoding/decoding and graphics rendering performance",
                requires_root=True,
            ))

        return recs

    def _analyze_storage(self, values: dict) -> List[TuningRecommendation]:
        """存储分析"""
        recs = []

        storage_type = self._get_value(values, "storage_type", "")
        if storage_type and "emmc" in storage_type.lower():
            recs.append(TuningRecommendation(
                category="storage",
                priority="low",
                title="eMMC storage performance limited",
                current_value="eMMC",
                recommended_value="NVMe SSD (if M.2 available)",
                suggestion=(
                    "RK3588 supports PCIe 3.0 x4, can connect external NVMe SSD. "
                    "For frequent read/write scenarios (model switching, dataset loading), "
                    "NVMe SSD is 5-10x faster than eMMC"
                ),
                impact="Model loading and data processing speed improved 5-10x",
                requires_root=False,
            ))

        disk_usage = self._parse_pct(self._get_value(values, "disk_usage", ""))
        if disk_usage and disk_usage > 85:
            recs.append(TuningRecommendation(
                category="storage",
                priority="high",
                title="Disk space insufficient",
                current_value=f"{disk_usage}% used",
                recommended_value="<80% used",
                suggestion="Clean logs and temp files, delete unused model files",
                impact="Full disk causes system instability, inference tasks may fail",
                requires_root=False,
            ))

        return recs

    def _analyze_system(self, values: dict) -> List[TuningRecommendation]:
        """系统级分析"""
        recs = []

        mem_pct = self._parse_pct(self._get_value(values, "mem_used_pct", ""))
        if mem_pct and mem_pct > 90:
            rec = TuningRecommendation(
                category="system",
                priority="high",
                title="Memory usage too high",
                current_value=f"{mem_pct}%",
                recommended_value="<80%",
                suggestion=(
                    "1) Check top memory-consuming processes: ps aux --sort=-%mem | head -20 "
                    "2) Reduce buffer cache: echo 3 | sudo tee /proc/sys/vm/drop_caches "
                    "3) Consider adding swap: sudo fallocate -l 4G /swapfile"
                ),
                impact="Memory exhaustion causes OOM kill, affecting service stability",
                requires_root=True,
                auto_fixable=True,
                fix_command="echo 3 | sudo tee /proc/sys/vm/drop_caches",
                fix_callback=AutoFixer.drop_caches
            )
            recs.append(rec)

        swap_used = self._get_value(values, "swap_used", "")
        if swap_used and swap_used not in ("0", "0B", "N/A", ""):
            recs.append(TuningRecommendation(
                category="system",
                priority="medium",
                title="Swap in use",
                current_value=f"Swap: {swap_used}",
                recommended_value="Swap: 0 (or minimal)",
                suggestion="Swap usage significantly reduces performance, consider adding physical memory or optimizing memory usage",
                impact="Eliminating swap usage can improve response speed by 10-100x",
                requires_root=False,
            ))

        return recs

    def get_profile_recommendation(self, profile: str = "balanced") -> Dict[str, Any]:
        """获取指定配置文件的推荐设置"""
        if profile not in self.PROFILES:
            profile = "balanced"

        p = self.PROFILES[profile]

        return {
            "chip": self.chip_model,
            "profile": profile,
            "description": p["description"],
            "settings": {
                "cpu_governor": p["cpu_governor"],
                "ddr_freq": self.specs["ddr_freq_mhz"][p["ddr_policy"].split('_')[0]] if '_' in p["ddr_policy"] else None,
                "npu_policy": p["npu_policy"],
                "gpu_policy": p["gpu_policy"],
            }
        }

    def _recommend_cooling(self, npu_temp: Optional[float], cpu_temp: Optional[float]) -> Optional[Dict[str, Any]]:
        """推荐散热方案"""
        max_temp = max(npu_temp or 0, cpu_temp or 0)

        for solution in self.COOLING_SOLUTIONS:
            if self.chip_model in solution["suitable"] and max_temp <= solution["max_tdp"] + 10:
                return solution

        return None

    def _get_value(self, values: dict, key: str, default: str = "") -> str:
        """从检测结果中获取值"""
        if key in values:
            v = values[key]
            if hasattr(v, 'result'):
                return str(v.result) if v.result is not None else default
            elif isinstance(v, dict):
                return str(v.get('result', default))
            return str(v)
        return default

    def _parse_mhz(self, value: str) -> Optional[float]:
        """解析 MHz 值"""
        if not value:
            return None
        try:
            import re
            match = re.search(r'(\d+\.?\d*)', str(value))
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None

    def _parse_temp(self, value: str) -> Optional[float]:
        """解析温度值"""
        return self._parse_mhz(value)

    def _parse_pct(self, value: str) -> Optional[float]:
        """解析百分比值"""
        if not value:
            return None
        try:
            import re
            match = re.search(r'(\d+\.?\d*)', str(value))
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None

    def apply_fix(self, recommendation: TuningRecommendation) -> bool:
        """
        应用修复建议

        Args:
            recommendation: 调优建议

        Returns:
            是否成功
        """
        if not recommendation.auto_fixable:
            return False

        if recommendation.fix_callback:
            try:
                return recommendation.fix_callback()
            except Exception:
                return False

        if recommendation.fix_command:
            try:
                result = subprocess.run(
                    recommendation.fix_command,
                    shell=True,
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            except Exception:
                return False

        return False