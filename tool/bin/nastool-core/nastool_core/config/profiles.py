# -*- coding: utf-8 -*-
"""
nastool_core/config/profiles.py - 设备配置文件

定义不同使用场景下的检测策略。
"""

from typing import Dict, List

# Profile定义
PROFILES: Dict[str, dict] = {
    "nas": {
        "description": "NAS服务器模式 - 完整检测，包括网络和存储",
        "skip_checks": [],
        "skip_categories": [],
        "weights_override": None,
    },
    
    "dev": {
        "description": "开发/测试机模式 - 跳过外网检测",
        "skip_checks": [
            "internet_access",
            "dns_resolve",
        ],
        "skip_categories": [],
        "weights_override": None,
    },
    
    "jetson": {
        "description": "Jetson嵌入式模式 - 降低网络权重，增强AI检测",
        "skip_checks": [
            "internet_access",
        ],
        "skip_categories": [],
        "weights_override": {
            "gpu_detected": 3.0,
            "cuda_version": 2.5,
            "tensorrt_version": 2.0,
            "jetpack_version": 2.0,
            "internet_access": 0.5,
            "dns_resolve": 0.5,
        },
    },
    
    "isolated": {
        "description": "网络隔离模式 - 跳过所有网络检测",
        "skip_checks": [
            "internet_access",
            "dns_resolve",
            "dns_coverage",
            "nas_backend",
            "network_latency",
            "bandwidth",
            "default_route",
        ],
        "skip_categories": [],
        "weights_override": None,
    },
    
    "ai_server": {
        "description": "AI推理服务器模式 - 增强AI检测，降低网络权重",
        "skip_checks": [],
        "skip_categories": [],
        "weights_override": {
            "gpu_detected": 4.0,
            "gpu_memory": 3.0,
            "gpu_utilization": 2.5,
            "cuda_version": 3.0,
            "cudnn_version": 2.5,
            "tensorflow_version": 2.0,
            "pytorch_version": 2.0,
            "tensorrt_version": 2.5,
            "internet_access": 0.5,
            "cron_jobs": 0.3,
        },
    },
}

DEFAULT_PROFILE = "nas"


def get_profile(profile_name: str) -> dict:
    """获取profile配置"""
    if profile_name not in PROFILES:
        raise ValueError(
            f"Unknown profile: {profile_name}. "
            f"Available profiles: {', '.join(PROFILES.keys())}"
        )
    return PROFILES[profile_name]


def list_profiles() -> List[str]:
    """列出所有可用的profile"""
    return list(PROFILES.keys())