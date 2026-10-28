"""connectors — 检测结果的上报通道（可选）

nastool 本身不依赖任何后端，detach 状态下只输出本地报告。
需要把结果送到别处时，按需启用：

  none     默认，不上报
  webhook  通用 HTTP POST，任意接收端（自建接口、告警平台、自动化流程）
  ainas    AINAS 家庭媒体 NAS 的官方接入（可选项，非依赖）
"""
from .base import BaseConnector
from .webhook import WebhookConnector
from .ainas import AinasConnector

CONNECTORS = {
    "none": None,
    "webhook": WebhookConnector,
    "ainas": AinasConnector,
}


def get_connector(name: str, **kwargs) -> BaseConnector:
    """按名称取连接器；未知名称返回 None（调用方应回退到不上报）。"""
    key = (name or "none").lower()
    cls = CONNECTORS.get(key)
    if cls is None:
        return None
    return cls(**kwargs)


def connector_names() -> list:
    return [k for k, v in CONNECTORS.items() if v is not None]
