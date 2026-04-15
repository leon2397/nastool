"""
nastool/utils/health_scorer.py - Health Score Calculator v2

评分体系 v4.0.2：
- 三层权重：critical=3x / important=2x / standard=1x
- 分类评分：每个类别独立评分
- 基础分：passed=100 / warning=65 / critical=0 / info=100(不扣分)
- 最终分 = weighted_sum / total_weight
"""

from typing import Optional
from dataclasses import dataclass, field
from checks.base import CheckResult, CheckSeverity, CheckCategory


# ============================================================
# 检查项权重配置
# ============================================================
# critical (3x)   : 直接影响数据安全或系统稳定，必须立即处理
# important (2x)  : 影响性能或安全，但不是立即危险
# standard (1x)    : 一般检查项
# info_only (0x)  : 仅提供信息，不计入评分

WEIGHTS = {
    # === 存储 (critical - 数据安全) ===
    "smart_health":          3.0,   # 硬盘 SMART 故障前兆
    "raid_status":           3.0,   # RAID 阵列异常
    "hdd_temperature":        2.5,   # 硬盘过热
    "storage_trend":          2.0,   # 存储趋势异常
    "log_disk":               1.5,   # 日志盘占用过高
    "docker_images":          1.0,   # Docker 镜像清理
    "storage_disk":           2.0,   # 磁盘空间
    "write_speed":            1.5,   # 写入速度
    "path_exists":            1.0,   # 存储路径
    "inode_usage":            2.0,   # Inode 使用率
    "io_wait":                1.5,   # IO 等待
    "zfs_pool":               3.0,   # ZFS 池状态
    "disk_space":             2.5,   # 磁盘空间（通用）

    # === 系统 (critical - 系统稳定) ===
    "cpu_temperature":        2.5,   # CPU 过热
    "system_uptime":          1.0,   # 长时间未重启
    "docker_containers":      1.5,   # 容器异常
    "memory_check":           2.0,   # 内存不足
    "disk_space":             2.5,   # 磁盘空间不足
    "python_version":         1.5,   # Python 版本过旧
    "pip_installed":          1.0,   # pip 未安装
    "system_libs":            1.5,   # 缺少系统库
    "kernel_version":         1.0,   # 内核版本
    "docker_service":         2.0,   # Docker 服务
    "cron_jobs":              0.5,   # 定时任务
    "package_updates":        1.0,   # 系统更新
    "process_count":          0.5,   # 进程数量
    "system_logs":            0.5,   # 系统日志

    # === 网络 (important - 连接质量) ===
    "internet_access":        2.0,   # 无法上网
    "dns_resolve":            2.5,   # DNS 解析失败
    "dns_coverage":           1.5,   # DNS 配置不足
    "nic_speed":              1.5,   # 网卡速率异常
    "nas_backend":            2.0,   # NAS 后端不可达
    "port_conflict":          2.0,   # 端口冲突
    "network_latency":        1.5,   # 网络延迟
    "bandwidth":              1.5,   # 网络带宽
    "mtu_size":               0.5,   # MTU
    "proxy_config":           0.5,   # 代理配置
    "default_route":          2.0,   # 默认路由
    "dns_cache":              0.5,   # DNS 缓存
    "wifi_status":            1.0,   # WiFi 状态

    # === 安全 (critical - 安全风险) ===
    "login_failures":         3.0,   # 暴力破解攻击
    "ssl_cert":               2.5,   # 证书过期
    "firewall":               2.0,   # 防火墙关闭
    "selinux":                1.0,   # SELinux 配置
    "ssh_root":               2.5,   # SSH root 登录开启
    "ssh_config":             1.5,   # SSH 配置
    "ssl_cert_days":          2.0,   # SSL 证书有效期
    "openssl_version":        1.5,   # OpenSSL 版本
    "fail2ban":               2.0,   # Fail2ban
    "clamav":                 1.0,   # ClamAV
    "suspicious_ports":       2.5,   # 异常端口

    # === AI 加速 (important - AI 性能) ===
    "gpu_detected":           2.0,   # GPU 未检测到
    "version_checker":        1.0,   # 版本检查
    "tensorflow_version":     1.0,   # TensorFlow
    "keras_version":          0.5,   # Keras
    "cudnn_version":          1.5,   # cuDNN
    "openvino_version":       0.5,   # OpenVINO
    "paddlepaddle_version":   0.5,   # PaddlePaddle
    "onednn_version":         0.5,   # OneDNN
    "gpu_memory":             2.0,   # GPU 显存
    "gpu_utilization":        1.0,   # GPU 利用率
    "nvidia_driver_version":  2.0,   # NVIDIA 驱动
    "nvidia_container_toolkit": 1.5, # NVIDIA Container
    "triton_server":          1.0,   # Triton
    "torchserve":             0.5,   # TorchServe
    "tensorflow_serving":     0.5,   # TF Serving
    "mlflow":                 0.5,   # MLflow
    "kubeflow":               0.5,   # Kubeflow
    "onnx_model":             0.5,   # ONNX 模型
    "model_format":           0.5,   # 模型格式

    # === NAS 系统 (important - NAS 平台) ===
    "nas_version":            2.0,   # NAS 版本过旧
    "nas_users":              2.0,   # 用户弱密码
    "shared_perms":           2.5,   # 共享权限过大
    "ups_status":             1.5,   # UPS 状态异常
    "cron_conflicts":         0.5,   # 定时任务冲突
    "nas_temperature":        1.5,   # NAS 温度
    "media_indexer":          1.0,   # 媒体索引
    "backup_status":          2.0,   # 备份状态
    "smb_service":            1.5,   # SMB
    "nfs_service":            1.5,   # NFS
    "afp_service":            1.0,   # AFP
    "ftp_service":            0.5,   # FTP
    "sftp_service":           1.0,   # SFTP
    "webdav_service":         1.0,   # WebDAV
    "snmp_service":           0.5,   # SNMP

    # === USB 连接 (v5.0.3) ===
    "usb_devices":             1.0,   # USB 设备检测
    "usb_storage_mount":        1.5,   # USB 存储挂载
    "usb_permissions":          1.5,   # USB 权限
    "usb_power":                2.0,   # USB 过流 (critical)
}

# 分类默认权重（未在 WEIGHTS 中定义的检查）
DEFAULT_WEIGHT = 1.0

# 分类中文名称
CATEGORY_NAMES = {
    CheckCategory.STORAGE:  "存储",
    CheckCategory.SYSTEM:  "系统",
    CheckCategory.NETWORK: "网络",
    CheckCategory.AI:      "AI加速",
    CheckCategory.SECURITY: "安全",
    CheckCategory.NAS:      "NAS",
}

# 评分等级
SCORE_LEVELS = [
    (90, "🌟 Excellent",  "优秀",  "系统处于最佳状态"),
    (80, "✅ Good",       "良好",  "存在少量可优化项"),
    (70, "👍 Fair",       "一般",  "存在需要关注的问题"),
    (60, "⚠️  Attention", "注意",  "问题较多，建议修复"),
    (50, "🔴 Poor",       "较差",  "存在严重问题，请尽快处理"),
    (0,  "💥 Critical",   "危险",  "系统处于高风险状态！"),
]


@dataclass
class CategoryScore:
    """单个类别的评分详情"""
    category: CheckCategory
    name: str
    score: int            # 0-100
    total: int            # 该类别总检查数
    passed: int
    warnings: int
    critical: int
    info: int
    weight: float
    weighted_score: float
    issues: list          # 该类别的问题列表


@dataclass
class HealthReport:
    """完整健康评分报告"""
    # Required - set by HealthScorer.calculate()
    overall_score: int = 0                  # 0-100 综合评分
    level_label: str = ""                   # 等级标签
    level_name: str = ""                   # 等级中文名
    level_desc: str = ""                   # 等级描述

    # 计数
    total_checks: int = 0
    total_passed: int = 0
    total_warnings: int = 0
    total_critical: int = 0
    total_info: int = 0

    # 加权
    total_weight: float = 0.0
    weighted_sum: float = 0.0

    # 分类详情
    category_scores: list = field(default_factory=list)

    # 建议
    critical_items: list = field(default_factory=list)   # 紧急事项（score=0 的项目）
    warnings_items: list = field(default_factory=list)    # 警告事项

    # 历史
    previous_score: Optional[int] = None
    score_change: int = 0                    # 相比上次的分数变化

    def grade(self) -> str:
        """获取等级字母（类学校评分）"""
        if self.overall_score >= 95: return "A+"
        if self.overall_score >= 90: return "A"
        if self.overall_score >= 85: return "A-"
        if self.overall_score >= 80: return "B+"
        if self.overall_score >= 75: return "B"
        if self.overall_score >= 70: return "B-"
        if self.overall_score >= 60: return "C"
        if self.overall_score >= 50: return "D"
        return "F"


class HealthScorer:
    """健康评分计算器"""

    def __init__(self):
        self.results: list = []

    def add_result(self, result: CheckResult):
        """添加一个检查结果"""
        self.results.append(result)

    def add_results(self, results: list):
        """批量添加检查结果"""
        self.results.extend(results)

    def calculate(self, previous_score: Optional[int] = None) -> HealthReport:
        """
        计算完整健康评分报告
        """
        if not self.results:
            return self._empty_report(previous_score)

        report = HealthReport(
            total_checks=len(self.results),
            previous_score=previous_score,
        )

        # 1. 分类计算
        by_category = self._group_by_category()
        category_reports = []

        for category, items in by_category.items():
            cat_report = self._score_category(category, items)
            category_reports.append(cat_report)
            report.total_weight += cat_report.weight
            report.weighted_sum += cat_report.weighted_score

            # 汇总计数
            report.total_passed += cat_report.passed
            report.total_warnings += cat_report.warnings
            report.total_critical += cat_report.critical
            report.total_info += cat_report.info

            # 收集问题
            report.critical_items.extend(cat_report.issues)

        report.category_scores = category_reports

        # 2. 计算综合评分
        if report.total_weight > 0:
            raw_score = report.weighted_sum / report.total_weight
            report.overall_score = int(round(raw_score))
        else:
            report.overall_score = 100

        # 3. 确定等级
        level_info = self._get_level(report.overall_score)
        report.level_label = level_info[1]
        report.level_name = level_info[2]
        report.level_desc = level_info[3]

        # 4. 计算分数变化
        if previous_score is not None:
            report.score_change = report.overall_score - previous_score

        return report

    def _group_by_category(self) -> dict:
        """按类别分组"""
        groups = {}
        for result in self.results:
            cat = result.category
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(result)
        return groups

    def _score_category(self, category: CheckCategory, items: list) -> CategoryScore:
        """计算单个类别的评分"""
        name = CATEGORY_NAMES.get(category, str(category.value))
        issues = []
        weighted_sum = 0.0
        total_weight = 0.0
        passed = warnings = critical = info = 0

        for r in items:
            w = WEIGHTS.get(r.check_id, DEFAULT_WEIGHT)
            base_score = self._base_score(r)
            weighted_sum += base_score * w
            total_weight += w

            if r.passed:
                passed += 1
            elif r.severity == CheckSeverity.WARNING:
                warnings += 1
                issues.append(r)
            elif r.severity == CheckSeverity.CRITICAL:
                critical += 1
                issues.append(r)
            elif r.severity == CheckSeverity.INFO:
                info += 1

        # 该类别的基础权重（用于跨类别汇总）
        category_base_weight = len(items) * DEFAULT_WEIGHT

        if total_weight > 0:
            score = int(round(weighted_sum / total_weight))
            weighted_score = score * category_base_weight
        else:
            score = 100
            weighted_score = 100 * category_base_weight

        return CategoryScore(
            category=category,
            name=name,
            score=score,
            total=len(items),
            passed=passed,
            warnings=warnings,
            critical=critical,
            info=info,
            weight=category_base_weight,
            weighted_score=weighted_score,
            issues=issues,
        )

    def _base_score(self, result: CheckResult) -> float:
        """
        单个检查项的基础分（0-100）
        规则：
        - PASSED / INFO → 100（不扣分）
        - WARNING       → 65
        - CRITICAL      → 0
        """
        if result.passed:
            return 100.0
        elif result.severity == CheckSeverity.CRITICAL:
            return 0.0
        elif result.severity == CheckSeverity.WARNING:
            return 65.0
        elif result.severity == CheckSeverity.INFO:
            return 100.0
        return 100.0

    def _get_level(self, score: int) -> tuple:
        """根据分数获取等级信息 (threshold, label, name, desc)"""
        for threshold, label, name, desc in SCORE_LEVELS:
            if score >= threshold:
                return (threshold, label, name, desc)
        return SCORE_LEVELS[-1]

    def _empty_report(self, previous_score: Optional[int] = None) -> HealthReport:
        """空报告"""
        report = HealthReport(
            overall_score=100,
            level_label="🌟 Excellent",
            level_name="优秀",
            level_desc="无检查数据",
            total_checks=0,
            previous_score=previous_score,
        )
        if previous_score is not None:
            report.score_change = 100 - previous_score
        return report


# ============================================================
# 辅助函数（可直接调用）
# ============================================================

def calculate_health_score(results: list, previous_score: Optional[int] = None) -> HealthReport:
    """
    一行调用：传入 CheckResult 列表，返回完整健康评分报告
    """
    scorer = HealthScorer()
    scorer.add_results(results)
    return scorer.calculate(previous_score)


def score_color(score: int) -> str:
    """根据分数返回对应颜色（用于终端显示）"""
    if score >= 90: return "green"
    if score >= 80: return "cyan"
    if score >= 70: return "yellow"
    if score >= 60: return "magenta"
    return "red"
