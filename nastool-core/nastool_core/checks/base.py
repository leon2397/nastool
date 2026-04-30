"""
checks/base.py - Base classes for all checks with accuracy enhancement
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Any, Tuple, Dict

# Configure logger
logger = logging.getLogger(__name__)

# 导入准确性保障模块
from ..utils.data_source import DataFusionEngine, DataSourceResult, FusionMethod, DataFusionConfig
from ..utils.consistency_validator import ConsistencyValidator, ConsistencyConfig, ConsistencyCheckResult
from ..utils.async_data_source import AsyncDataFusionEngine, AsyncDataCollector, AsyncDataSourceTask
# 导入配置中心
from ..config.accuracy_config import get_accuracy_config


class CheckSeverity(Enum):
    """Check result severity levels"""

    INFO = "info"  # Informational, no action needed
    WARNING = "warning"  # Warning, should fix but not critical
    CRITICAL = "critical"  # Critical, must fix before proceeding
    PASSED = "passed"  # Check passed


class CheckCategory(Enum):
    """Check categories for organization"""

    SYSTEM = "system"
    NETWORK = "network"
    STORAGE = "storage"
    AI = "ai"
    SECURITY = "security"
    NAS = "nas"
    USB = "usb"  # v5.0.3


@dataclass
class CheckResult:
    """Result of a single check with confidence scoring"""

    check_id: str  # Unique identifier: "python_version"
    category: CheckCategory  # Category for grouping
    severity: CheckSeverity  # Result severity
    passed: bool  # True if check passed
    title: str  # Human-readable title: "Python Version"
    current: str  # Current state: "3.6.9"
    expected: str  # Expected state: "3.8+"
    message: str  # Detailed message
    fix_available: bool = False  # Can be auto-fixed?
    fix_id: Optional[str] = None  # Corresponding fix ID
    fix_command: Optional[str] = None  # Command to fix
    fix_description: Optional[str] = None  # Human-readable fix description
    fix_risk: str = "low"  # Fix risk: low/medium/high
    url: Optional[str] = None  # Reference URL
    details: dict = field(default_factory=dict)  # Additional details
    
    # 新增：准确性相关字段
    confidence: float = 1.0  # 置信度评分 (0.0-1.0)
    data_sources: List[str] = field(default_factory=list)  # 数据来源列表
    consistency_report: Optional[Dict[str, Any]] = None  # 一致性验证报告


@dataclass
class CheckSummary:
    """Summary of all check results"""

    total: int = 0
    passed: int = 0
    warnings: int = 0
    critical: int = 0
    info: int = 0
    score: int = 0  # 0-100
    results: List[CheckResult] = field(default_factory=list)

    def add_result(self, result: CheckResult):
        """Add a result and update counters"""
        self.results.append(result)
        self.total += 1

        if result.passed:
            self.passed += 1
        else:
            # 归一化 severity：支持枚举和字符串
            sev = result.severity
            if isinstance(sev, str):
                m = {"info": CheckSeverity.INFO, "warning": CheckSeverity.WARNING,
                     "critical": CheckSeverity.CRITICAL, "passed": CheckSeverity.PASSED}
                sev = m.get(sev.lower(), CheckSeverity.INFO)
            if sev == CheckSeverity.WARNING:
                self.warnings += 1
            elif sev == CheckSeverity.CRITICAL:
                self.critical += 1
            elif sev == CheckSeverity.INFO:
                self.info += 1

    def calculate_score(self):
        """Calculate overall health score (0-100) [legacy]"""
        if self.total == 0:
            return 0

        # Weighted scoring
        passed_weight = 100
        warning_weight = 70
        critical_weight = 0

        total_score = (
            self.passed * passed_weight
            + self.warnings * warning_weight
            + self.critical * critical_weight
        )
        max_score = self.total * passed_weight

        self.score = int((total_score / max_score) * 100) if max_score > 0 else 0
        return self.score

    def get_health_report(self, previous_score: int = None) -> "HealthReport":
        """
        Calculate detailed health score using HealthScorer (v4.0.2).
        Returns a HealthReport with category-level scores and recommendations.
        """
        from utils.health_scorer import calculate_health_score
        report = calculate_health_score(self.results, previous_score)
        self.score = report.overall_score
        return report


class Check(ABC):
    """Abstract base class for all checks with accuracy enhancement"""

    # Subclasses should override these
    check_id: str = "base_check"
    category: CheckCategory = CheckCategory.SYSTEM
    title: str = "Base Check"
    description: str = "Base check class"
    
    # 准确性配置
    enable_data_fusion: bool = True  # 是否启用数据融合
    enable_consistency_check: bool = True  # 是否启用一致性检查
    fusion_method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE  # 默认融合方法

    def __init__(self):
        """Initialize check with accuracy enhancement components"""
        logger.debug(f"Initializing check: {self.check_id}")
        # 从配置中心获取准确性配置
        self.accuracy_config = get_accuracy_config()
        
        # 初始化数据融合引擎（使用配置中心配置）
        df_config = self.accuracy_config.data_fusion
        self.fusion_engine = DataFusionEngine(
            config=DataFusionConfig(
                outlier_detection=df_config.outlier_detection.enabled,
                outlier_threshold=df_config.outlier_detection.threshold,
                time_consistency=df_config.time_consistency.enabled,
                max_age_seconds=df_config.time_consistency.max_time_diff,
                trend_consistency=True,
                min_sources=df_config.outlier_detection.min_samples
            )
        )
        
        # 初始化一致性验证器（使用配置中心配置）
        c_config = self.accuracy_config.consistency
        self.consistency_validator = ConsistencyValidator(
            config=ConsistencyConfig(
                time_consistency=c_config.time_consistency.enabled,
                max_time_diff=c_config.time_consistency.max_time_diff,
                value_consistency=c_config.value_consistency.enabled,
                max_value_diff=c_config.value_consistency.max_value_diff,
                trend_consistency=c_config.trend_consistency.enabled,
                min_trend_points=c_config.trend_consistency.min_trend_points,
                source_consistency=c_config.source_consistency.enabled,
                min_sources=c_config.source_consistency.min_sources
            )
        )

    @abstractmethod
    def run(self) -> CheckResult:
        """
        Run the check and return result.
        Must be implemented by subclasses.
        """
        pass

    def _run_command(self, cmd: str, timeout: int = 10) -> str:
        """Helper to run shell command"""
        import subprocess

        try:
            logger.debug(f"Running command: {cmd} (timeout: {timeout}s)")
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, errors="replace", timeout=timeout
            )
            if result.returncode != 0:
                logger.debug(f"Command failed with return code {result.returncode}: {cmd}")
                logger.debug(f"stderr: {result.stderr}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out: {cmd}")
            return ""
        except Exception as e:
            logger.error(f"Command error: {cmd}, exception: {e}")
            return ""

    def _read_file(self, path: str) -> str:
        """Helper to read file contents"""
        try:
            logger.debug(f"Reading file: {path}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            logger.debug(f"Read {len(content)} characters from {path}")
            return content
        except FileNotFoundError:
            logger.debug(f"File not found: {path}")
            return ""
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return ""

    def _file_exists(self, path: str) -> bool:
        """Check if file exists"""
        import os

        return os.path.exists(path)

    def _command_exists(self, cmd: str) -> bool:
        """Check if command exists"""
        import shutil

        return shutil.which(cmd) is not None

    # ========== 准确性保障方法 ==========
    
    def _create_data_source_result(self, value: Any, source: str, 
                                   confidence: float = 1.0) -> DataSourceResult:
        """Create a data source result"""
        from datetime import datetime
        return DataSourceResult(
            value=value,
            source=source,
            timestamp=datetime.now().timestamp(),
            confidence=confidence
        )

    def _fuse_multiple_sources(self, results: List[DataSourceResult]) -> Tuple[Any, Dict[str, Any]]:
        """
        Fuse data from multiple sources using data fusion engine.
        
        Args:
            results: List of DataSourceResult objects
            
        Returns:
            Tuple of (fused_value, metadata)
        """
        if not self.enable_data_fusion:
            if results:
                return results[0].value, {
                    "sources": [r.source for r in results],
                    "source_count": len(results),
                    "confidence": results[0].confidence,
                    "fusion_method": "disabled"
                }
            return None, {"error": "No results"}
        
        return self.fusion_engine.fuse_data(results, self.fusion_method)

    def _validate_consistency(self, results: List[DataSourceResult]) -> Dict[str, ConsistencyCheckResult]:
        """
        Validate consistency of data from multiple sources.
        
        Args:
            results: List of DataSourceResult objects
            
        Returns:
            Dictionary of consistency check results
        """
        if not self.enable_consistency_check or len(results) < 2:
            return {
                "overall": ConsistencyCheckResult(
                    is_consistent=True,
                    check_name="overall",
                    details={"message": "Consistency check disabled or insufficient sources"},
                    confidence=1.0
                )
            }
        
        return self.consistency_validator.validate(results)

    def _calculate_overall_confidence(self, fusion_metadata: Dict[str, Any], 
                                       consistency_result: Dict[str, Any]) -> float:
        """
        Calculate overall confidence score based on fusion and consistency results.
        
        Args:
            fusion_metadata: Metadata from data fusion
            consistency_result: Result from consistency validation
            
        Returns:
            Overall confidence score (0.0-1.0)
        """
        fusion_confidence = fusion_metadata.get("confidence", 0.7)
        consistency_confidence = consistency_result.get("overall", {}).get("confidence", 0.7)
        
        # 融合置信度 = 数据融合置信度 * 0.6 + 一致性置信度 * 0.4
        overall = (fusion_confidence * 0.6) + (consistency_confidence * 0.4)
        return round(max(0.0, min(1.0, overall)), 2)

    def _enhance_result_with_accuracy(self, result: CheckResult, 
                                       data_sources: List[DataSourceResult]) -> CheckResult:
        """
        Enhance a CheckResult with accuracy information.
        
        Args:
            result: Original CheckResult
            data_sources: List of DataSourceResult objects used
            
        Returns:
            Enhanced CheckResult with confidence and consistency info
        """
        if not data_sources:
            return result
        
        # 执行数据融合
        fused_value, fusion_metadata = self._fuse_multiple_sources(data_sources)
        
        # 执行一致性验证
        consistency_result = self._validate_consistency(data_sources)
        
        # 计算综合置信度
        result.confidence = self._calculate_overall_confidence(fusion_metadata, consistency_result)
        
        # 更新数据来源信息
        result.data_sources = fusion_metadata.get("sources", [])
        
        # 添加一致性报告
        result.consistency_report = {
            "time_consistent": consistency_result.get("time", {}).get("is_consistent", True),
            "value_consistent": consistency_result.get("value", {}).get("is_consistent", True),
            "trend_consistent": consistency_result.get("trend", {}).get("is_consistent", True),
            "source_consistent": consistency_result.get("source", {}).get("is_consistent", True),
            "overall_confidence": consistency_result.get("overall", {}).get("confidence", 1.0)
        }
        
        return result

    # ========== 异步数据采集方法 ==========
    
    def _create_async_collector(self) -> AsyncDataCollector:
        """创建异步数据收集器"""
        return AsyncDataCollector()
    
    def _add_async_source(self, collector: AsyncDataCollector, name: str, 
                         task, *args, confidence: float = 1.0, **kwargs):
        """
        向收集器添加数据源
        
        Args:
            collector: AsyncDataCollector实例
            name: 数据源名称
            task: 数据采集任务（同步函数、异步函数或协程）
            args: 位置参数
            confidence: 置信度
            kwargs: 关键字参数
        """
        collector.add_source(name, task, *args, confidence=confidence, **kwargs)
    
    def _collect_data_parallel(self, sources: List[Tuple[str, callable, Dict]]) -> List[DataSourceResult]:
        """
        同步并行采集多源数据（内部使用线程池）
        
        Args:
            sources: [(name, func, kwargs), ...]
            
        Returns:
            数据源结果列表
        """
        collector = self._create_async_collector()
        for name, func, kwargs in sources:
            collector.add_source(name, func, **kwargs)
        return collector.collect_sync()
    
    def _collect_and_fuse_parallel(self, sources: List[Tuple[str, callable, Dict]],
                                   method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE
                                   ) -> Tuple[Any, Dict[str, Any], List[DataSourceResult]]:
        """
        同步并行采集并融合数据
        
        Args:
            sources: [(name, func, kwargs), ...]
            method: 融合方法
            
        Returns:
            (融合值, 元数据, 原始数据源结果)
        """
        collector = self._create_async_collector()
        for name, func, kwargs in sources:
            collector.add_source(name, func, **kwargs)
        return collector.collect_and_fuse_sync(method)
