"""
check_timeouts.py - 检测项超时配置

根据性能分析结果，为慢检测项配置更短的超时时间。
"""

# 检测项超时配置（秒）
# None 表示使用默认值（30秒）
CHECK_TIMEOUTS = {
    # 网络检测 - 设置较短超时，避免长时间等待
    "network_latency": 5.0,
    "latency_check": 5.0,
    "internet_access": 3.0,
    "port_conflict": 5.0,
    "nas_backend": 3.0,
    
    # AI服务检测 - 服务可能未启动，快速失败
    "triton_server": 2.0,
    "torchserve": 2.0,
    "tensorflow_serving": 2.0,
    
    # 系统检测 - 正常速度
    "pip_installed": 10.0,
    "memory_check": 5.0,
    "process_count": 5.0,
    "system_disk": 5.0,
    
    # 存储检测
    "write_speed": 10.0,
    
    # 其他检测使用默认30秒
}

# 可以并行的检测项分类（IO-bound）
PARALLEL_CATEGORIES = {
    "network": ["network_latency", "latency_check", "internet_access", 
                "port_conflict", "nas_backend", "nic_speed", "default_route"],
    "ai": ["triton_server", "torchserve", "tensorflow_serving", 
           "mlflow", "kubeflow"],
    "storage": ["write_speed", "smart_health", "hdd_temperature"],
}

# 必须顺序执行的检测项（有依赖关系）
SEQUENTIAL_CHECKS = [
    # 目前无强依赖，全部可以并行
]
