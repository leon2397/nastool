#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建默认配置文件
"""

import os
import json
from pathlib import Path

# 默认阈值配置
DEFAULT_THRESHOLDS = {
    "thresholds": {
        "rk3588": {
            "cpu_temp": {"warning": 70, "critical": 80},
            "gpu_temp": {"warning": 75, "critical": 85}
        },
        "jetson_xavier": {
            "cpu_temp": {"warning": 75, "critical": 85},
            "gpu_temp": {"warning": 80, "critical": 90}
        },
        "jetson_nano": {
            "cpu_temp": {"warning": 70, "critical": 80},
            "gpu_temp": {"warning": 75, "critical": 85}
        },
        "rk3568": {
            "cpu_temp": {"warning": 70, "critical": 80},
            "gpu_temp": {"warning": 75, "critical": 85}
        },
        "rk3566": {
            "cpu_temp": {"warning": 70, "critical": 80},
            "gpu_temp": {"warning": 75, "critical": 85}
        },
        "generic": {
            "cpu_temp": {"warning": 75, "critical": 85},
            "gpu_temp": {"warning": 80, "critical": 90}
        }
    },
    "data_fusion": {
        "outlier_detection": True,
        "outlier_method": "iqr",
        "outlier_threshold": 1.5,
        "fusion_method": "weighted_average",
        "min_sources": 2,
        "time_consistency": True,
        "max_age_seconds": 30.0,
        "trend_consistency": True,
        "trend_window": 3
    },
    "history": {
        "enabled": True,
        "retention_days": 30,
        "storage_path": "~/.nastool/history"
    },
    "confidence": {
        "source_weight": 0.4,
        "consistency_weight": 0.3,
        "historical_weight": 0.15,
        "device_weight": 0.1,
        "check_weight": 0.05,
        "min_confidence": 0.0,
        "max_confidence": 1.0
    }
}

def create_default_config():
    """创建默认配置文件"""
    # 配置文件路径
    config_path = os.path.expanduser("~/.nastool/config.json")
    
    # 创建目录
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # 写入配置文件
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_THRESHOLDS, f, indent=2, ensure_ascii=False)
    
    print(f"默认配置文件已创建: {config_path}")
    print(f"配置内容:")
    print(json.dumps(DEFAULT_THRESHOLDS, indent=2, ensure_ascii=False))
    
    return config_path

if __name__ == "__main__":
    create_default_config()