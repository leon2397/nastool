# -*- coding: utf-8 -*-
"""
nastool/core/weight_loader.py - 健康评分权重配置加载器

v7.0 新增：从 YAML 文件加载权重配置

使用方式：
    from core.weight_loader import WeightLoader
    
    # 使用默认配置（内置 WEIGHTS）
    loader = WeightLoader()
    
    # 使用自定义配置文件
    loader = WeightLoader(config_file="config/health_weights.yaml")
    
    # 获取权重
    weight = loader.get_weight("gpu_detected")
    
    # 批量覆盖
    loader.override({"gpu_detected": 3.0, "nvidia_driver_version": 3.0})
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml


DEFAULT_WEIGHT = 1.0


class WeightLoader:
    """
    权重配置加载器
    
    支持：
    - 默认配置（内置）
    - YAML 配置文件
    - 命令行覆盖
    """

    # 内置默认权重（与 health_scorer.py 保持一致）
    DEFAULT_WEIGHTS = {
        # 存储 (critical)
        "smart_health": 3.0,
        "raid_status": 3.0,
        "hdd_temperature": 2.5,
        "storage_trend": 2.0,
        "log_disk": 1.5,
        "docker_images": 1.0,
        "storage_disk": 2.0,
        "write_speed": 1.5,
        "path_exists": 1.0,
        "inode_usage": 2.0,
        "io_wait": 1.5,
        "zfs_pool": 3.0,
        "disk_space": 2.5,
        # 系统
        "cpu_temperature": 2.5,
        "system_uptime": 1.0,
        "docker_containers": 1.5,
        "memory_check": 2.0,
        "python_version": 1.5,
        "pip_installed": 1.0,
        "system_libs": 1.5,
        "kernel_version": 1.0,
        "docker_service": 2.0,
        "cron_jobs": 0.5,
        "package_updates": 1.0,
        "process_count": 0.5,
        "system_logs": 0.5,
        # 网络
        "internet_access": 2.0,
        "dns_resolve": 2.5,
        "dns_coverage": 1.5,
        "nic_speed": 1.5,
        "nas_backend": 2.0,
        "port_conflict": 2.0,
        "network_latency": 1.5,
        "bandwidth": 1.5,
        "mtu_size": 0.5,
        "proxy_config": 0.5,
        "default_route": 2.0,
        "dns_cache": 0.5,
        "wifi_status": 1.0,
        # 安全
        "login_failures": 3.0,
        "ssl_cert": 2.5,
        "firewall": 2.0,
        "selinux": 1.0,
        "ssh_root": 2.5,
        "ssh_config": 1.5,
        "ssl_cert_days": 2.0,
        "openssl_version": 1.5,
        "fail2ban": 2.0,
        "clamav": 1.0,
        "suspicious_ports": 2.5,
        # AI 加速
        "gpu_detected": 2.0,
        "version_checker": 1.0,
        "tensorflow_version": 1.0,
        "keras_version": 0.5,
        "cudnn_version": 1.5,
        "openvino_version": 0.5,
        "paddlepaddle_version": 0.5,
        "onednn_version": 0.5,
        "gpu_memory": 2.0,
        "gpu_utilization": 1.0,
        "nvidia_driver_version": 2.0,
        "nvidia_container_toolkit": 1.5,
        "triton_server": 1.0,
        "torchserve": 0.5,
        "tensorflow_serving": 0.5,
        "mlflow": 0.5,
        "kubeflow": 0.5,
        "onnx_model": 0.5,
        "model_format": 0.5,
        # NAS
        "nas_version": 2.0,
        "nas_users": 2.0,
        "shared_perms": 2.5,
        "ups_status": 1.5,
        "cron_conflicts": 0.5,
        "nas_temperature": 1.5,
        "media_indexer": 1.0,
        "backup_status": 2.0,
        "smb_service": 1.5,
        "nfs_service": 1.5,
        "afp_service": 1.0,
        "ftp_service": 0.5,
        "sftp_service": 1.0,
        "webdav_service": 1.0,
        "snmp_service": 0.5,
        # USB
        "usb_devices": 1.0,
        "usb_storage_mount": 1.5,
        "usb_permissions": 1.5,
        "usb_power": 2.0,
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化加载器
        
        Args:
            config_file: YAML 配置文件路径（可选）
        """
        self._weights = dict(self.DEFAULT_WEIGHTS)
        self._overrides = {}
        self._base_score = {
            "passed": 100,
            "warning": 65,
            "critical": 0,
            "info": 100,
        }
        
        if config_file:
            self.load_from_file(config_file)

    def load_from_file(self, config_file: str) -> bool:
        """
        从 YAML 文件加载配置
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            是否加载成功
        """
        path = Path(config_file)
        
        # 尝试相对于 nastool 目录
        if not path.exists():
            nastool_dir = Path(__file__).parent.parent
            path = nastool_dir / config_file
            
        if not path.exists():
            print(f"[WeightLoader] 配置文件未找到: {config_file}")
            return False
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            if not config:
                return False
            
            # 加载权重
            if "weights" in config:
                self._weights.update(config["weights"])
            
            # 加载默认配置
            if "default" in config:
                if "weight" in config["default"]:
                    global DEFAULT_WEIGHT
                    DEFAULT_WEIGHT = config["default"]["weight"]
                if "base_score" in config["default"]:
                    self._base_score.update(config["default"]["base_score"])
            
            print(f"[WeightLoader] 已加载配置: {path}")
            return True
            
        except Exception as e:
            print(f"[WeightLoader] 加载配置失败: {e}")
            return False

    def get_weight(self, check_id: str) -> float:
        """
        获取检查项权重
        
        Args:
            check_id: 检查项 ID
            
        Returns:
            权重值
        """
        # 优先使用覆盖值
        if check_id in self._overrides:
            return self._overrides[check_id]
        return self._weights.get(check_id, DEFAULT_WEIGHT)

    def override(self, overrides: dict) -> None:
        """
        批量覆盖权重
        
        Args:
            overrides: {check_id: weight} 字典
        """
        self._overrides.update(overrides)

    def get_base_score(self, status: str) -> int:
        """
        获取基础分
        
        Args:
            status: passed / warning / critical / info
            
        Returns:
            基础分数
        """
        return self._base_score.get(status, 100)

    def get_all_weights(self) -> dict:
        """获取所有权重配置"""
        result = dict(self._weights)
        result.update(self._overrides)
        return result

    def reset(self) -> None:
        """重置覆盖，恢复默认"""
        self._overrides = {}


# ============================================================
# 便捷函数
# ============================================================

# 全局默认加载器
_default_loader: Optional[WeightLoader] = None


def get_weight_loader(config_file: Optional[str] = None) -> WeightLoader:
    """
    获取全局权重加载器（单例）
    
    Args:
        config_file: 配置文件路径（仅首次生效）
    """
    global _default_loader
    
    if _default_loader is None:
        _default_loader = WeightLoader(config_file)
    elif config_file:
        # 重新加载配置文件
        _default_loader.load_from_file(config_file)
    
    return _default_loader


def get_weight(check_id: str) -> float:
    """快速获取权重（使用全局加载器）"""
    return get_weight_loader().get_weight(check_id)


# 导出
__all__ = [
    "WeightLoader",
    "get_weight_loader",
    "get_weight",
    "DEFAULT_WEIGHT",
]
