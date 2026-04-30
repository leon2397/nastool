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

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class TuningRecommendation:
    """调优建议"""
    category: str          # cpu / ddr / npu / gpu / thermal / storage / system
    priority: str          # critical / high / medium / low
    title: str             # 简短标题
    current_value: str     # 当前值
    recommended_value: str # 推荐值
    suggestion: str        # 详细建议
    impact: str            # 预期影响
    requires_root: bool = False  # 是否需要 root 权限
    auto_fixable: bool = False   # 是否可自动修复

    def __str__(self):
        icon = {
            "critical": "[!!!]",
            "high": "[!!]",
            "medium": "[!]",
            "low": "[i]",
        }.get(self.priority, "[?]")
        root_flag = " [ROOT]" if self.requires_root else ""
        auto_flag = " [AUTO]" if self.auto_fixable else ""
        return f"{icon} [{self.category.upper()}] {self.title}{root_flag}{auto_flag}\n    Current: {self.current_value}\n    Recommended: {self.recommended_value}\n    Suggestion: {self.suggestion}\n    Impact: {self.impact}"


class TuningAdvisor:
    """
    RK3588/RK3568 性能调优顾问
    
    基于检测结果，给出针对性的调优建议。
    """
    
    # ===== RK3588 参数规范 =====
    RK3588_SPECS = {
        "cpu_freq_mhz": {"min": 408, "max": 2400, "perf": 2400, "powersave": 408},
        "ddr_freq_mhz": {"min": 528, "max": 2112, "perf": 2112, "powersave": 528},
        "npu_freq_mhz": {"min": 200, "max": 1000, "perf": 1000, "powersave": 200},
        "gpu_freq_mhz": {"min": 200, "max": 1000, "perf": 1000, "powersave": 200},
        "thermal_warning_c": 75,
        "thermal_critical_c": 85,
        "thermal_throttle_c": 80,
    }
    
    # ===== RK3568 参数规范 =====
    RK3568_SPECS = {
        "cpu_freq_mhz": {"min": 408, "max": 2000, "perf": 2000, "powersave": 408},
        "ddr_freq_mhz": {"min": 528, "max": 1560, "perf": 1560, "powersave": 528},
        "npu_freq_mhz": {"min": 100, "max": 800, "perf": 800, "powersave": 100},
        "gpu_freq_mhz": {"min": 200, "max": 800, "perf": 800, "powersave": 200},
        "thermal_warning_c": 70,
        "thermal_critical_c": 80,
        "thermal_throttle_c": 75,
    }
    
    # ===== 调优配置文件 =====
    PROFILES = {
        "performance": {
            "description": "最大性能，功耗较高",
            "cpu_governor": "performance",
            "ddr_policy": "max_freq",
            "npu_policy": "max_freq",
            "gpu_policy": "max_freq",
            "fan_policy": "aggressive",
        },
        "balanced": {
            "description": "性能与功耗平衡",
            "cpu_governor": "ondemand",
            "ddr_policy": "auto",
            "npu_policy": "auto",
            "gpu_policy": "auto",
            "fan_policy": "normal",
        },
        "powersave": {
            "description": "最低功耗，性能受限",
            "cpu_governor": "powersave",
            "ddr_policy": "min_freq",
            "npu_policy": "min_freq",
            "gpu_policy": "min_freq",
            "fan_policy": "quiet",
        },
    }
    
    # ===== 散热方案建议 =====
    COOLING_SOLUTIONS = [
        {
            "name": "被动散热",
            "max_tdp": 5,
            "suitable": ["RK3566", "RK3568"],
            "description": "纯铝散热片，无风扇",
            "pros": "静音、免维护",
            "cons": "长时间高负载会降频",
        },
        {
            "name": "主动散热（小风扇）",
            "max_tdp": 10,
            "suitable": ["RK3588", "RK3568"],
            "description": "散热片 + 5V 小风扇",
            "pros": "性价比高，散热效果良好",
            "cons": "有噪音",
        },
        {
            "name": "主动散热（PWM 风扇）",
            "max_tdp": 15,
            "suitable": ["RK3588"],
            "description": "PWM 智能调速风扇",
            "pros": "噪音可控，散热优秀",
            "cons": "需要 GPIO 控制",
        },
        {
            "name": "液冷方案",
            "max_tdp": 25,
            "suitable": ["RK3588"],
            "description": "水冷头 + 水泵 + 散热排",
            "pros": "极限散热，完全静音",
            "cons": "成本高、体积大",
        },
    ]
    
    def __init__(self, chip_model: str = "RK3588"):
        """
        初始化调优顾问
        
        Args:
            chip_model: 芯片型号 (RK3588 / RK3568 / RK3566)
        """
        self.chip_model = chip_model.upper()
        
        if "3566" in self.chip_model:
            self.specs = self.RK3568_SPECS  # RK3566 与 RK3568 类似
        elif "3568" in self.chip_model:
            self.specs = self.RK3568_SPECS
        else:
            self.specs = self.RK3588_SPECS
    
    def analyze(self, check_results: list) -> List[TuningRecommendation]:
        """
        分析检测结果，生成调优建议
        
        Args:
            check_results: CheckResult 列表
            
        Returns:
            TuningRecommendation 列表
        """
        recommendations = []
        
        # 提取检测值到字典
        values = {}
        for r in check_results:
            if hasattr(r, 'check_id'):
                values[r.check_id] = r
            elif isinstance(r, dict):
                values[r.get('check_id', '')] = r
        
        # 各项分析
        recommendations.extend(self._analyze_cpu(values))
        recommendations.extend(self._analyze_thermal(values))
        recommendations.extend(self._analyze_npu(values))
        recommendations.extend(self._analyze_ddr(values))
        recommendations.extend(self._analyze_gpu(values))
        recommendations.extend(self._analyze_storage(values))
        recommendations.extend(self._analyze_system(values))
        
        # 按优先级排序
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 99))
        
        return recommendations
    
    def _analyze_cpu(self, values: dict) -> List[TuningRecommendation]:
        """CPU 频率与调度分析"""
        recs = []
        
        # 检查 CPU 调度器
        cpu_gov = self._get_value(values, "cpu_governor", "")
        if cpu_gov and cpu_gov != "performance":
            recs.append(TuningRecommendation(
                category="cpu",
                priority="medium",
                title="CPU governor 非性能模式",
                current_value=cpu_gov,
                recommended_value="performance",
                suggestion=(
                    "对于推理密集型任务，建议将 CPU governor 设为 performance 模式: "
                    "echo performance | sudo tee /sys/devices/system/cpu/cpufreq/policy0/scaling_governor"
                ),
                impact="CPU 频率锁定最高，推理延迟降低 10-30%",
                requires_root=True,
                auto_fixable=True,
            ))
        
        # 检查 CPU 频率
        cpu_freq = self._parse_mhz(self._get_value(values, "cpu_freq_mhz", ""))
        if cpu_freq and cpu_freq < self.specs["cpu_freq_mhz"]["perf"] * 0.8:
            recs.append(TuningRecommendation(
                category="cpu",
                priority="high",
                title="CPU 频率远低于最高值",
                current_value=f"{cpu_freq} MHz",
                recommended_value=f"{self.specs['cpu_freq_mhz']['perf']} MHz",
                suggestion="检查 CPU governor 设置和散热状态，可能存在降频保护",
                impact="提升 CPU 频率可显著改善通用计算性能",
                requires_root=True,
            ))
        
        return recs
    
    def _analyze_thermal(self, values: dict) -> List[TuningRecommendation]:
        """散热与温度分析"""
        recs = []
        
        # 检查 NPU 温度
        npu_temp = self._parse_temp(self._get_value(values, "npu_temp_c", ""))
        if npu_temp:
            if npu_temp >= self.specs["thermal_critical_c"]:
                recs.append(TuningRecommendation(
                    category="thermal",
                    priority="critical",
                    title="NPU 温度危险",
                    current_value=f"{npu_temp}C",
                    recommended_value=f"<{self.specs['thermal_warning_c']}C",
                    suggestion=(
                        "NPU 温度已达临界值! 立即检查散热: "
                        "1) 确认散热片安装正确 "
                        "2) 检查风扇是否运转 "
                        "3) 清理灰尘 "
                        "4) 考虑升级散热方案"
                    ),
                    impact="过热会导致 NPU 降频，推理性能下降 50%+",
                    requires_root=False,
                ))
            elif npu_temp >= self.specs["thermal_warning_c"]:
                recs.append(TuningRecommendation(
                    category="thermal",
                    priority="high",
                    title="NPU 温度偏高",
                    current_value=f"{npu_temp}C",
                    recommended_value=f"<{self.specs['thermal_warning_c']}C",
                    suggestion="建议改善散热条件，检查风扇转速和风道设计",
                    impact="高温导致 NPU 间歇降频，推理延迟不稳定",
                    requires_root=False,
                ))
        
        # 检查 CPU 温度
        cpu_temp = self._parse_temp(self._get_value(values, "cpu_temp_c", ""))
        if cpu_temp and cpu_temp >= self.specs["thermal_warning_c"]:
            recs.append(TuningRecommendation(
                category="thermal",
                priority="high",
                title="CPU 温度偏高",
                current_value=f"{cpu_temp}C",
                recommended_value=f"<{self.specs['thermal_warning_c']}C",
                suggestion="改善 CPU 散热：涂导热硅脂、增加风道、升级散热器",
                impact="高温导致 CPU 降频保护，整体性能下降",
                requires_root=False,
            ))
        
        # 推荐散热方案
        cooling = self._recommend_cooling(npu_temp, cpu_temp)
        if cooling:
            recs.append(TuningRecommendation(
                category="thermal",
                priority="low",
                title=f"推荐散热方案: {cooling['name']}",
                current_value=f"NPU={npu_temp or 'N/A'}C, CPU={cpu_temp or 'N/A'}C",
                recommended_value=cooling["description"],
                suggestion=f"{cooling['pros']}。注意: {cooling['cons']}",
                impact="改善散热可避免降频，维持稳定性能",
                requires_root=False,
            ))
        
        return recs
    
    def _analyze_npu(self, values: dict) -> List[TuningRecommendation]:
        """NPU 状态分析"""
        recs = []
        
        # NPU 驱动检查
        npu_driver = self._get_value(values, "rknpu_node", "")
        if npu_driver in ("False", "false", False):
            recs.append(TuningRecommendation(
                category="npu",
                priority="critical",
                title="NPU 驱动未加载",
                current_value="/dev/rknpu not found",
                recommended_value="/dev/rknpu exists",
                suggestion=(
                    "安装 Rockchip NPU 驱动: "
                    "1) sudo apt update && sudo apt install rockchip-npu "
                    "2) 或从 https://github.com/rockchip-linux/rknpu 驱动源码编译 "
                    "3) 确认内核版本与驱动版本匹配"
                ),
                impact="NPU 不可用，推理任务只能走 CPU，性能下降 10-50x",
                requires_root=True,
            ))
        
        # RKNN Runtime 检查
        rknn_rt = self._get_value(values, "rknn_runtime", "")
        if rknn_rt in ("not_installed", "False", "false", ""):
            recs.append(TuningRecommendation(
                category="npu",
                priority="high",
                title="RKNN Runtime 未安装",
                current_value="not installed",
                recommended_value="rknn-toolkit2 >= 2.0.0",
                suggestion=(
                    "安装 RKNN Toolkit2: "
                    "pip install rknn-toolkit2 "
                    "或从 https://github.com/rockchip-linux/rknn-toolkit2 获取"
                ),
                impact="无法使用 RKNN 模型推理，需转为 ONNX Runtime",
                requires_root=False,
            ))
        
        # NPU 利用率分析
        npu_util = self._parse_pct(self._get_value(values, "npu_utilization", ""))
        if npu_util is not None and npu_util < 30:
            recs.append(TuningRecommendation(
                category="npu",
                priority="medium",
                title="NPU 利用率偏低",
                current_value=f"{npu_util}%",
                recommended_value=">70%",
                suggestion=(
                    "NPU 利用率低可能原因: "
                    "1) 模型未转为 RKNN 格式 "
                    "2) 批量大小(batch_size)太小 "
                    "3) 数据预处理在 CPU 上成为瓶颈 "
                    "建议增大 batch_size 或使用多线程数据加载"
                ),
                impact="优化后 NPU 利用率可达 80%+，吞吐量提升 2-3x",
                requires_root=False,
            ))
        
        # NPU 频率
        npu_freq = self._parse_mhz(self._get_value(values, "npu_freq_mhz", ""))
        if npu_freq and npu_freq < self.specs["npu_freq_mhz"]["perf"] * 0.8:
            recs.append(TuningRecommendation(
                category="npu",
                priority="medium",
                title="NPU 频率偏低",
                current_value=f"{npu_freq} MHz",
                recommended_value=f"{self.specs['npu_freq_mhz']['perf']} MHz",
                suggestion="检查 NPU 频率策略: cat /sys/class/npu/npu/clk_base_freq",
                impact="提升 NPU 频率可降低推理延迟",
                requires_root=True,
            ))
        
        return recs
    
    def _analyze_ddr(self, values: dict) -> List[TuningRecommendation]:
        """DDR 带宽分析"""
        recs = []
        
        ddr_freq = self._parse_mhz(self._get_value(values, "ddr_freq_mhz", ""))
        if ddr_freq and ddr_freq < self.specs["ddr_freq_mhz"]["perf"] * 0.7:
            recs.append(TuningRecommendation(
                category="ddr",
                priority="high",
                title="DDR 频率过低",
                current_value=f"{ddr_freq} MHz",
                recommended_value=f"{self.specs['ddr_freq_mhz']['perf']} MHz",
                suggestion=(
                    "DDR 频率过低影响模型加载和推理吞吐。 "
                    "设置 DDR 最高频率: "
                    f"echo {self.specs['ddr_freq_mhz']['perf']}000000 | sudo tee /sys/class/devfreq/dmc/max_freq"
                ),
                impact="DDR 带宽翻倍，模型加载时间缩短 30-50%",
                requires_root=True,
                auto_fixable=True,
            ))
        
        return recs
    
    def _analyze_gpu(self, values: dict) -> List[TuningRecommendation]:
        """GPU (Mali) 分析"""
        recs = []
        
        gpu_freq = self._parse_mhz(self._get_value(values, "gpu_freq_mhz", ""))
        if gpu_freq and gpu_freq < self.specs["gpu_freq_mhz"]["perf"] * 0.7:
            recs.append(TuningRecommendation(
                category="gpu",
                priority="medium",
                title="GPU 频率偏低",
                current_value=f"{gpu_freq} MHz",
                recommended_value=f"{self.specs['gpu_freq_mhz']['perf']} MHz",
                suggestion="检查 Mali GPU 频率策略，对于图形/视频编解码任务建议锁定最高频率",
                impact="提升 GPU 频率可改善视频编解码和图形渲染性能",
                requires_root=True,
            ))
        
        return recs
    
    def _analyze_storage(self, values: dict) -> List[TuningRecommendation]:
        """存储分析"""
        recs = []
        
        # 存储类型检测
        storage_type = self._get_value(values, "storage_type", "")
        if storage_type and "emmc" in storage_type.lower():
            recs.append(TuningRecommendation(
                category="storage",
                priority="low",
                title="eMMC 存储性能有限",
                current_value="eMMC",
                recommended_value="NVMe SSD (如有 M.2 接口)",
                suggestion=(
                    "RK3588 支持 PCIe 3.0 x4，可外接 NVMe SSD。 "
                    "对于频繁读写场景（模型切换、数据集加载），"
                    "NVMe SSD 比 eMMC 快 5-10 倍"
                ),
                impact="模型加载和数据处理速度提升 5-10x",
                requires_root=False,
            ))
        
        # 磁盘空间
        disk_usage = self._parse_pct(self._get_value(values, "disk_usage", ""))
        if disk_usage and disk_usage > 85:
            recs.append(TuningRecommendation(
                category="storage",
                priority="high",
                title="磁盘空间不足",
                current_value=f"{disk_usage}% used",
                recommended_value="<80% used",
                suggestion="清理日志和临时文件，删除不用的模型文件",
                impact="磁盘满会导致系统不稳定，推理任务可能失败",
                requires_root=False,
            ))
        
        return recs
    
    def _analyze_system(self, values: dict) -> List[TuningRecommendation]:
        """系统级分析"""
        recs = []
        
        # 内存使用
        mem_pct = self._parse_pct(self._get_value(values, "mem_used_pct", ""))
        if mem_pct and mem_pct > 90:
            recs.append(TuningRecommendation(
                category="system",
                priority="high",
                title="内存使用率过高",
                current_value=f"{mem_pct}%",
                recommended_value="<80%",
                suggestion=(
                    "1) 检查占用内存最多的进程: ps aux --sort=-%mem | head -20 "
                    "2) 减少 buffer cache: echo 3 | sudo tee /proc/sys/vm/drop_caches "
                    "3) 考虑增加 swap: sudo fallocate -l 4G /swapfile"
                ),
                impact="内存不足会导致 OOM kill，影响服务稳定性",
                requires_root=True,
            ))
        
        # swap 使用
        swap_used = self._get_value(values, "swap_used", "")
        if swap_used and swap_used not in ("0", "0B", "N/A", ""):
            recs.append(TuningRecommendation(
                category="system",
                priority="medium",
                title="Swap 正在使用",
                current_value=f"Swap: {swap_used}",
                recommended_value="Swap: 0 (或极少量)",
                suggestion="Swap 使用会显著降低性能，建议增加物理内存或优化内存使用",
                impact="消除 swap 使用可提升响应速度 10-100x",
                requires_root=False,
            ))
        
        return recs
    
    def get_profile_recommendation(self, profile: str = "balanced") -> Dict[str, Any]:
        """
        获取指定配置文件的推荐设置
        
        Args:
            profile: 配置文件名 (performance / balanced / powersave)
            
        Returns:
            推荐设置字典
        """
        if profile not in self.PROFILES:
            profile = "balanced"
        
        p = self.PROFILES[profile]
        
        return {
            "chip": self.chip_model,
            "profile": profile,
            "description": p["description"],
            "settings": {
                "cpu_governor": p["cpu_governor"],
                "cpu_max_freq_mhz": self.specs["cpu_freq_mhz"].get(p["cpu_governor"], self.specs["cpu_freq_mhz"]["perf"]),
                "ddr_max_freq_mhz": self.specs["ddr_freq_mhz"]["perf"] if p["ddr_policy"] == "max_freq" else None,
                "npu_max_freq_mhz": self.specs["npu_freq_mhz"]["perf"] if p["npu_policy"] == "max_freq" else None,
                "gpu_max_freq_mhz": self.specs["gpu_freq_mhz"]["perf"] if p["gpu_policy"] == "max_freq" else None,
            },
            "commands": self._generate_commands(profile),
        }
    
    def _generate_commands(self, profile: str) -> List[str]:
        """生成调优命令列表"""
        p = self.PROFILES.get(profile, self.PROFILES["balanced"])
        cmds = []
        
        # CPU governor
        cmds.append(
            f"echo {p['cpu_governor']} | sudo tee /sys/devices/system/cpu/cpufreq/policy0/scaling_governor"
        )
        
        # DDR 频率
        if p["ddr_policy"] == "max_freq":
            cmds.append(
                f"echo {self.specs['ddr_freq_mhz']['perf']}000000 | sudo tee /sys/class/devfreq/dmc/max_freq"
            )
        
        # NPU 频率
        if p["npu_policy"] == "max_freq" and "3588" in self.chip_model:
            cmds.append(
                f"echo {self.specs['npu_freq_mhz']['perf']}000000 | sudo tee /sys/class/devfreq/fdab0000.npu/max_freq"
            )
        
        return cmds
    
    def _recommend_cooling(self, npu_temp: Optional[float], cpu_temp: Optional[float]) -> Optional[Dict]:
        """根据温度推荐散热方案"""
        max_temp = max(npu_temp or 0, cpu_temp or 0)
        
        if max_temp <= 0:
            return None
        
        # 选择适合当前芯片的散热方案
        suitable = [c for c in self.COOLING_SOLUTIONS if self.chip_model in c["suitable"] or "RK3588" in c["suitable"]]
        
        if max_temp >= self.specs["thermal_critical_c"]:
            # 需要最强散热
            return suitable[-1] if suitable else None
        elif max_temp >= self.specs["thermal_warning_c"]:
            # 需要主动散热
            active = [c for c in suitable if "风扇" in c["name"] or "液冷" in c["name"]]
            return active[0] if active else None
        elif max_temp >= 55:
            # 温度还行，基础散热即可
            return suitable[0] if suitable else None
        
        return None
    
    # ===== 工具方法 =====
    
    def _get_value(self, values: dict, key: str, default: str = "") -> str:
        """从检测结果提取值"""
        if key in values:
            v = values[key]
            if hasattr(v, 'value'):
                return str(v.value) if v.value is not None else default
            elif hasattr(v, 'current'):
                return str(v.current) if v.current is not None else default
            elif isinstance(v, dict):
                return str(v.get('value', v.get('current', default)))
            return str(v)
        return default
    
    @staticmethod
    def _parse_mhz(value: str) -> Optional[float]:
        """解析 MHz 值"""
        if not value or value in ("unknown", "N/A", ""):
            return None
        try:
            # 移除 MHz 后缀和空格
            cleaned = value.replace("MHz", "").replace("MHz", "").strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _parse_temp(value: str) -> Optional[float]:
        """解析温度值"""
        if not value or value in ("unknown", "N/A", ""):
            return None
        try:
            cleaned = value.replace("C", "").replace("c", "").replace("'", "").strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _parse_pct(value: str) -> Optional[float]:
        """解析百分比值"""
        if not value or value in ("unknown", "N/A", ""):
            return None
        try:
            cleaned = value.replace("%", "").strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None
