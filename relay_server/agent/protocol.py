"""
WebSocket 消息协议定义
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


class MessageType:
    """消息类型常量"""
    
    # Agent → Relay
    REGISTER = "register"
    HEARTBEAT = "heartbeat"
    REPORT = "report"
    RESPONSE = "response"
    LOG = "log"
    ERROR = "error"
    FILE_UPLOADED = "file_uploaded"
    FILE_RESPONSE = "file_response"       # Agent 返回文件内容给 GUI
    DEPLOY_PROGRESS = "deploy_progress"    # 部署进度上报
    DEPLOY_RESULT = "deploy_result"        # 部署最终结果
    
    # Relay → Agent
    REGISTER_ACK = "register_ack"
    COMMAND = "command"
    FILE = "file"
    FILE_REQUEST = "file_request"          # GUI 请求 Agent 读取文件
    DEPLOY = "deploy"                      # 下发部署指令
    DISCONNECT = "disconnect"
    HEARTBEAT_ACK = "heartbeat_ack"
    
    # GUI → Relay
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    
    # Relay → GUI
    DEVICE_ONLINE = "device_online"
    DEVICE_OFFLINE = "device_offline"
    COMMAND_QUEUED = "command_queued"
    COMMAND_SENT = "command_sent"

    # OTA 升级（Agent ↔ Relay）
    OTA_CHECK = "ota_check"           # Agent → Relay: 询问最新版本
    OTA_VERSION = "ota_version"       # Relay → Agent: 返回版本信息
    OTA_ACK = "ota_ack"              # Agent → Relay: 确认收到指令
    OTA_START = "ota_start"           # Agent → Relay: 开始下载
    OTA_PROGRESS = "ota_progress"     # Agent → Relay: 下载进度
    OTA_READY = "ota_ready"           # Agent → Relay: 新版已就绪，准备重启
    OTA_RESULT = "ota_result"        # Agent → Relay: 升级最终结果


@dataclass
class Message:
    """WebSocket 消息"""
    
    type: str
    id: str
    timestamp: int
    payload: Dict[str, Any]
    source: Optional[str] = None  # 来源（device_id 或 gui_session_id）
    target: Optional[str] = None  # 目标（device_id）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        d = {
            "type": self.type,
            "id": self.id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }
        if self.source:
            d["source"] = self.source
        if self.target:
            d["target"] = self.target
        return d
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Message":
        """从字典创建"""
        return cls(
            type=d["type"],
            id=d["id"],
            timestamp=d["timestamp"],
            payload=d.get("payload", {}),
            source=d.get("source"),
            target=d.get("target"),
        )


@dataclass
class RegisterPayload:
    """注册消息 payload"""
    
    device_id: str
    device_name: str
    device_type: str
    version: str
    hostname: str
    ip_local: str
    capabilities: list
    agent_key: str
    os: str
    arch: str
    python_version: str


@dataclass
class CommandPayload:
    """命令消息 payload"""
    
    command_id: str
    cmd: str
    timeout_ms: int = 30000
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None


@dataclass
class ResponsePayload:
    """命令响应 payload"""
    
    command_id: str
    code: int
    stdout: str
    stderr: str
    duration_ms: int


@dataclass
class ReportPayload:
    """检测报告 payload"""
    
    overall_score: int
    categories: Dict[str, Any]
    items: list


@dataclass
class FilePayload:
    """文件传输 payload（GUI→Agent 上传）"""
    
    file_id: str
    name: str
    size: int
    content_base64: str
    path: str
    mode: str = "0644"
    checksum_sha256: Optional[str] = None


@dataclass
class FileRequestPayload:
    """文件请求 payload（GUI→Agent 下载）"""
    
    file_request_id: str
    path: str
    encoding: str = "base64"   # base64 | text


@dataclass
class FileResponsePayload:
    """文件响应 payload（Agent→GUI 返回）"""
    
    file_request_id: str
    path: str
    name: str
    size: int
    content_base64: str
    encoding: str = "base64"
    checksum_sha256: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DeployPayload:
    """部署指令 payload"""
    
    deployment_id: str
    version: str = "latest"
    url: Optional[str] = None       # 下载地址
    files: Optional[list] = None     # 直接传输的文件列表
    config: Optional[Dict] = None    # 部署配置
    backup: bool = True              # 是否备份旧版本
    restart: bool = True             # 部署后是否重启服务


@dataclass
class DeployProgressPayload:
    """部署进度 payload"""
    
    deployment_id: str
    step: str         # downloading | extracting | installing | restarting | verifying
    progress: int     # 0-100
    message: str


@dataclass
class DeployResultPayload:
    """部署结果 payload"""
    
    deployment_id: str
    success: bool
    version: str = ""
    message: str = ""
    duration_ms: int = 0
