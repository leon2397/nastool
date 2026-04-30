# -*- coding: utf-8 -*-
"""
准确性配置中心 - 统一管理所有准确性参数

提供全局准确性配置管理，支持：
- 数据融合配置
- 一致性验证配置
- 置信度计算配置
- 异常值检测配置
- 动态配置热更新
"""

from __future__ import annotations

import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OutlierDetectionConfig:
    """异常值检测配置"""
    enabled: bool = True
    method: str = "IQR"  # IQR, Z-score, MAD
    threshold: float = 1.5  # IQR倍数或Z-score阈值
    min_samples: int = 3  # 最小样本数


@dataclass
class TimeConsistencyConfig:
    """时间一致性验证配置"""
    enabled: bool = True
    max_time_diff: float = 30.0  # 最大时间差(秒)
    strict_mode: bool = False  # 严格模式：所有源时间必须一致


@dataclass
class ValueConsistencyConfig:
    """值一致性验证配置"""
    enabled: bool = True
    max_value_diff: float = 10.0  # 最大差值百分比
    allow_relative_diff: bool = True  # 允许相对差异


@dataclass
class TrendConsistencyConfig:
    """趋势一致性验证配置"""
    enabled: bool = True
    min_trend_points: int = 3  # 最小趋势点数
    trend_window: int = 5  # 趋势窗口大小


@dataclass
class SourceConsistencyConfig:
    """源一致性验证配置"""
    enabled: bool = True
    min_sources: int = 2  # 最小数据源数量
    required_sources: List[str] = field(default_factory=list)  # 必需数据源列表


@dataclass
class DataFusionConfig:
    """数据融合配置"""
    enabled: bool = True
    method: str = "weighted_average"  # weighted_average, median, mean, voting
    outlier_detection: OutlierDetectionConfig = field(default_factory=OutlierDetectionConfig)
    time_consistency: TimeConsistencyConfig = field(default_factory=TimeConsistencyConfig)
    confidence_weight: float = 0.3  # 置信度权重
    source_count_weight: float = 0.4  # 源数量权重
    consistency_weight: float = 0.3  # 一致性权重


@dataclass
class ConsistencyConfig:
    """一致性验证配置"""
    time_consistency: TimeConsistencyConfig = field(default_factory=TimeConsistencyConfig)
    value_consistency: ValueConsistencyConfig = field(default_factory=ValueConsistencyConfig)
    trend_consistency: TrendConsistencyConfig = field(default_factory=TrendConsistencyConfig)
    source_consistency: SourceConsistencyConfig = field(default_factory=SourceConsistencyConfig)


@dataclass
class AccuracyThresholds:
    """准确性阈值配置"""
    minimum_confidence: float = 0.7  # 最小置信度要求
    warning_confidence: float = 0.85  # 警告置信度阈值
    critical_confidence: float = 0.5  # 临界置信度阈值
    data_freshness_seconds: float = 60.0  # 数据新鲜度要求


@dataclass
class AccuracyConfig:
    """全局准确性配置"""
    enabled: bool = True
    data_fusion: DataFusionConfig = field(default_factory=DataFusionConfig)
    consistency: ConsistencyConfig = field(default_factory=ConsistencyConfig)
    thresholds: AccuracyThresholds = field(default_factory=AccuracyThresholds)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccuracyConfig':
        """从字典加载配置"""
        config = cls()
        
        if 'enabled' in data:
            config.enabled = data['enabled']
        
        if 'data_fusion' in data:
            df_data = data['data_fusion']
            if 'enabled' in df_data:
                config.data_fusion.enabled = df_data['enabled']
            if 'method' in df_data:
                config.data_fusion.method = df_data['method']
            if 'confidence_weight' in df_data:
                config.data_fusion.confidence_weight = df_data['confidence_weight']
            if 'source_count_weight' in df_data:
                config.data_fusion.source_count_weight = df_data['source_count_weight']
            if 'consistency_weight' in df_data:
                config.data_fusion.consistency_weight = df_data['consistency_weight']
            
            if 'outlier_detection' in df_data:
                od_data = df_data['outlier_detection']
                config.data_fusion.outlier_detection.enabled = od_data.get('enabled', True)
                config.data_fusion.outlier_detection.method = od_data.get('method', 'IQR')
                config.data_fusion.outlier_detection.threshold = od_data.get('threshold', 1.5)
                config.data_fusion.outlier_detection.min_samples = od_data.get('min_samples', 3)
            
            if 'time_consistency' in df_data:
                tc_data = df_data['time_consistency']
                config.data_fusion.time_consistency.enabled = tc_data.get('enabled', True)
                config.data_fusion.time_consistency.max_time_diff = tc_data.get('max_time_diff', 30.0)
        
        if 'consistency' in data:
            c_data = data['consistency']
            
            if 'time_consistency' in c_data:
                tc_data = c_data['time_consistency']
                config.consistency.time_consistency.enabled = tc_data.get('enabled', True)
                config.consistency.time_consistency.max_time_diff = tc_data.get('max_time_diff', 30.0)
            
            if 'value_consistency' in c_data:
                vc_data = c_data['value_consistency']
                config.consistency.value_consistency.enabled = vc_data.get('enabled', True)
                config.consistency.value_consistency.max_value_diff = vc_data.get('max_value_diff', 10.0)
            
            if 'trend_consistency' in c_data:
                tc_data = c_data['trend_consistency']
                config.consistency.trend_consistency.enabled = tc_data.get('enabled', True)
                config.consistency.trend_consistency.min_trend_points = tc_data.get('min_trend_points', 3)
            
            if 'source_consistency' in c_data:
                sc_data = c_data['source_consistency']
                config.consistency.source_consistency.enabled = sc_data.get('enabled', True)
                config.consistency.source_consistency.min_sources = sc_data.get('min_sources', 2)
        
        if 'thresholds' in data:
            t_data = data['thresholds']
            config.thresholds.minimum_confidence = t_data.get('minimum_confidence', 0.7)
            config.thresholds.warning_confidence = t_data.get('warning_confidence', 0.85)
            config.thresholds.critical_confidence = t_data.get('critical_confidence', 0.5)
            config.thresholds.data_freshness_seconds = t_data.get('data_freshness_seconds', 60.0)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'enabled': self.enabled,
            'data_fusion': {
                'enabled': self.data_fusion.enabled,
                'method': self.data_fusion.method,
                'confidence_weight': self.data_fusion.confidence_weight,
                'source_count_weight': self.data_fusion.source_count_weight,
                'consistency_weight': self.data_fusion.consistency_weight,
                'outlier_detection': {
                    'enabled': self.data_fusion.outlier_detection.enabled,
                    'method': self.data_fusion.outlier_detection.method,
                    'threshold': self.data_fusion.outlier_detection.threshold,
                    'min_samples': self.data_fusion.outlier_detection.min_samples,
                },
                'time_consistency': {
                    'enabled': self.data_fusion.time_consistency.enabled,
                    'max_time_diff': self.data_fusion.time_consistency.max_time_diff,
                    'strict_mode': self.data_fusion.time_consistency.strict_mode,
                },
            },
            'consistency': {
                'time_consistency': {
                    'enabled': self.consistency.time_consistency.enabled,
                    'max_time_diff': self.consistency.time_consistency.max_time_diff,
                    'strict_mode': self.consistency.time_consistency.strict_mode,
                },
                'value_consistency': {
                    'enabled': self.consistency.value_consistency.enabled,
                    'max_value_diff': self.consistency.value_consistency.max_value_diff,
                    'allow_relative_diff': self.consistency.value_consistency.allow_relative_diff,
                },
                'trend_consistency': {
                    'enabled': self.consistency.trend_consistency.enabled,
                    'min_trend_points': self.consistency.trend_consistency.min_trend_points,
                    'trend_window': self.consistency.trend_consistency.trend_window,
                },
                'source_consistency': {
                    'enabled': self.consistency.source_consistency.enabled,
                    'min_sources': self.consistency.source_consistency.min_sources,
                    'required_sources': self.consistency.source_consistency.required_sources,
                },
            },
            'thresholds': {
                'minimum_confidence': self.thresholds.minimum_confidence,
                'warning_confidence': self.thresholds.warning_confidence,
                'critical_confidence': self.thresholds.critical_confidence,
                'data_freshness_seconds': self.thresholds.data_freshness_seconds,
            },
        }


class AccuracyConfigManager:
    """准确性配置管理器 - 单例模式"""
    
    _instance = None
    _config: AccuracyConfig = None
    _config_path: Optional[str] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        if self._config is not None:
            return
        
        self._config_path = config_path or self._find_config_path()
        self._config = self._load_config()
    
    def _find_config_path(self) -> str:
        """查找配置文件路径"""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), 'accuracy_config.json'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'accuracy_config.json'),
            '/etc/nastool/accuracy_config.json',
            os.path.expanduser('~/.nastool/accuracy_config.json'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 返回默认配置路径
        default_path = os.path.join(os.path.dirname(__file__), 'accuracy_config.json')
        os.makedirs(os.path.dirname(default_path), exist_ok=True)
        return default_path
    
    def _load_config(self) -> AccuracyConfig:
        """加载配置"""
        if self._config_path and os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return AccuracyConfig.from_dict(data)
            except Exception as e:
                print(f"警告: 加载配置失败，使用默认配置 - {e}")
        
        return AccuracyConfig()
    
    def _save_config(self):
        """保存配置到文件"""
        if self._config_path:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config.to_dict(), f, indent=2, ensure_ascii=False)
    
    def get_config(self) -> AccuracyConfig:
        """获取当前配置"""
        return self._config
    
    def update_config(self, updates: Dict[str, Any]):
        """更新配置（支持热更新）"""
        self._config = AccuracyConfig.from_dict({**self._config.to_dict(), **updates})
        self._save_config()
    
    def set_enabled(self, enabled: bool):
        """设置全局准确性保障开关"""
        self._config.enabled = enabled
        self._save_config()
    
    def set_outlier_detection(self, enabled: bool, method: str = "IQR", threshold: float = 1.5):
        """设置异常值检测配置"""
        self._config.data_fusion.outlier_detection.enabled = enabled
        self._config.data_fusion.outlier_detection.method = method
        self._config.data_fusion.outlier_detection.threshold = threshold
        self._save_config()
    
    def set_consistency_weights(self, confidence_weight: float, source_count_weight: float, consistency_weight: float):
        """设置置信度计算权重"""
        self._config.data_fusion.confidence_weight = confidence_weight
        self._config.data_fusion.source_count_weight = source_count_weight
        self._config.data_fusion.consistency_weight = consistency_weight
        self._save_config()
    
    def set_thresholds(self, minimum_confidence: float, warning_confidence: float, critical_confidence: float):
        """设置置信度阈值"""
        self._config.thresholds.minimum_confidence = minimum_confidence
        self._config.thresholds.warning_confidence = warning_confidence
        self._config.thresholds.critical_confidence = critical_confidence
        self._save_config()
    
    def validate_config(self) -> List[str]:
        """验证配置有效性"""
        errors = []
        
        if not (0 <= self._config.data_fusion.confidence_weight <= 1):
            errors.append("置信度权重必须在0-1之间")
        if not (0 <= self._config.data_fusion.source_count_weight <= 1):
            errors.append("源数量权重必须在0-1之间")
        if not (0 <= self._config.data_fusion.consistency_weight <= 1):
            errors.append("一致性权重必须在0-1之间")
        
        total_weight = (self._config.data_fusion.confidence_weight +
                      self._config.data_fusion.source_count_weight +
                      self._config.data_fusion.consistency_weight)
        if abs(total_weight - 1.0) > 0.01:
            errors.append(f"权重总和应为1.0，当前为{total_weight}")
        
        if not (0 <= self._config.thresholds.minimum_confidence <= 1):
            errors.append("最小置信度必须在0-1之间")
        if not (0 <= self._config.thresholds.warning_confidence <= 1):
            errors.append("警告置信度必须在0-1之间")
        if not (0 <= self._config.thresholds.critical_confidence <= 1):
            errors.append("临界置信度必须在0-1之间")
        
        return errors


# 全局配置实例
accuracy_config = AccuracyConfigManager()


def get_accuracy_config() -> AccuracyConfig:
    """获取准确性配置（便捷函数）"""
    return accuracy_config.get_config()


def update_accuracy_config(updates: Dict[str, Any]):
    """更新准确性配置（便捷函数）"""
    accuracy_config.update_config(updates)
