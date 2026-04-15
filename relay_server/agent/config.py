"""
Agent 配置管理
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class AgentConfig:
    """Agent 配置"""

    # Relay Server 连接
    relay_url: str = "ws://120.77.249.3:18888"  # Relay Server 地址
    agent_key: str = ""  # 设备密钥（必须）

    # 设备信息
    device_id: str = ""  # 设备ID（留空则自动生成）
    device_name: str = ""  # 设备名称
    device_type: str = "generic"  # 设备类型: synology, qnap, jetson, rk3588, pi5, generic

    # 能力标签
    capabilities: List[str] = field(default_factory=lambda: ["storage", "network", "system"])

    # 心跳与超时
    heartbeat_interval: int = 30000  # 心跳间隔（毫秒）
    read_timeout: int = 90000  # 读取超时（毫秒）
    reconnect_delay: int = 5  # 重连延迟（秒）

    # 诊断配置
    diagnose_on_start: bool = False  # 启动时执行诊断
    diagnose_interval: int = 3600  # 定期诊断间隔（秒），0表示禁用
    diagnose_script: str = "arm_diagnose.py"  # 诊断脚本路径

    # OTA 升级配置
    ota_enabled: bool = True  # 是否启用 OTA 升级
    ota_check_interval: int = 3600  # 检查新版本间隔（秒），默认1小时
    ota_download_dir: str = "/tmp/nastool-ota"  # OTA 下载目录

    # 网络与重连配置
    reconnect_base_delay: int = 1   # 初始重连延迟（秒）
    reconnect_max_delay: int = 60   # 最大重连延迟（秒）
    reconnect_jitter: float = 0.2   # 抖动幅度（±20%）
    ping_before_connect: bool = True  # 连接前先检测网络是否可达
    connect_timeout: int = 10        # 连接超时（秒）

    # 日志
    log_level: str = "INFO"
    log_file: str = ""  # 日志文件路径，空则输出到控制台

    @classmethod
    def load(cls, path: str) -> "AgentConfig":
        """从文件加载配置"""
        config = cls()

        p = Path(path)
        if not p.exists():
            # 尝试环境变量
            config.relay_url = os.environ.get("RELAY_URL", config.relay_url)
            config.agent_key = os.environ.get("AGENT_KEY", config.agent_key)
            config.device_id = os.environ.get("DEVICE_ID", config.device_id)
            config.device_name = os.environ.get("DEVICE_NAME", config.device_name)
            return config

        if p.suffix in (".yaml", ".yml"):
            if yaml is None:
                print("警告: 需要 PyYAML 解析 YAML 配置，使用默认配置")
                return config

            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # 映射
            if "relay" in data:
                config.relay_url = data["relay"].get("url", config.relay_url)
                config.agent_key = data["relay"].get("agent_key", config.agent_key)

            if "device" in data:
                config.device_id = data["device"].get("id", config.device_id)
                config.device_name = data["device"].get("name", config.device_name)
                config.device_type = data["device"].get("type", config.device_type)
                config.capabilities = data["device"].get("capabilities", config.capabilities)

            if "timing" in data:
                config.heartbeat_interval = data["timing"].get("heartbeat_interval", config.heartbeat_interval)
                config.read_timeout = data["timing"].get("read_timeout", config.read_timeout)
                config.reconnect_delay = data["timing"].get("reconnect_delay", config.reconnect_delay)

            if "diagnose" in data:
                config.diagnose_on_start = data["diagnose"].get("on_start", config.diagnose_on_start)
                config.diagnose_interval = data["diagnose"].get("interval", config.diagnose_interval)
                config.diagnose_script = data["diagnose"].get("script", config.diagnose_script)
            
            if "ota" in data:
                config.ota_enabled = data["ota"].get("enabled", config.ota_enabled)
                config.ota_check_interval = data["ota"].get("check_interval", config.ota_check_interval)
                config.ota_download_dir = data["ota"].get("download_dir", config.ota_download_dir)
            
            if "network" in data:
                config.ping_before_connect = data["network"].get("ping_before_connect", config.ping_before_connect)
                config.connect_timeout = data["network"].get("connect_timeout", config.connect_timeout)
            
            if "reconnect" in data:
                config.reconnect_base_delay = data["reconnect"].get("base_delay", config.reconnect_base_delay)
                config.reconnect_max_delay = data["reconnect"].get("max_delay", config.reconnect_max_delay)
                config.reconnect_jitter = data["reconnect"].get("jitter", config.reconnect_jitter)
            
            if "log" in data:
                config.log_level = data["log"].get("level", config.log_level)
                config.log_file = data["log"].get("file", config.log_file)
        
        elif p.suffix == ".json":
            import json
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 简单映射
            for key in ["relay_url", "agent_key", "device_id", "device_name", "device_type",
                        "heartbeat_interval", "read_timeout", "reconnect_delay"]:
                if key in data:
                    setattr(config, key, data[key])
            if "capabilities" in data:
                config.capabilities = data["capabilities"]
            if "ota" in data:
                config.ota_enabled = data["ota"].get("enabled", config.ota_enabled)
                config.ota_check_interval = data["ota"].get("check_interval", config.ota_check_interval)
                config.ota_download_dir = data["ota"].get("download_dir", config.ota_download_dir)

        # 自动生成 device_id
        if not config.device_id:
            import uuid
            import platform
            config.device_id = f"{platform.node()}-{uuid.uuid4().hex[:8]}"

        return config

    def save(self, path: str) -> None:
        """保存配置到文件"""
        p = Path(path)

        if p.suffix in (".yaml", ".yml"):
            if yaml is None:
                raise RuntimeError("需要 PyYAML 保存 YAML 配置")

            data = {
                "relay": {
                    "url": self.relay_url,
                    "agent_key": self.agent_key,
                },
                "device": {
                    "id": self.device_id,
                    "name": self.device_name,
                    "type": self.device_type,
                    "capabilities": self.capabilities,
                },
                "timing": {
                    "heartbeat_interval": self.heartbeat_interval,
                    "read_timeout": self.read_timeout,
                    "reconnect_delay": self.reconnect_base_delay,
                },
                "diagnose": {
                    "on_start": self.diagnose_on_start,
                    "interval": self.diagnose_interval,
                    "script": self.diagnose_script,
                },
                "ota": {
                    "enabled": self.ota_enabled,
                    "check_interval": self.ota_check_interval,
                    "download_dir": self.ota_download_dir,
                },
                "network": {
                    "ping_before_connect": self.ping_before_connect,
                    "connect_timeout": self.connect_timeout,
                },
                "reconnect": {
                    "base_delay": self.reconnect_base_delay,
                    "max_delay": self.reconnect_max_delay,
                    "jitter": self.reconnect_jitter,
                },
                "log": {
                    "level": self.log_level,
                    "file": self.log_file,
                },
            }

            with open(p, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        else:
            raise ValueError(f"不支持的配置格式: {p.suffix}")
