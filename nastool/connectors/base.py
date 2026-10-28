"""connectors/base.py — 上报通道基类"""
from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """把诊断结果推送到外部系统。"""

    name = "base"

    @abstractmethod
    def push(self, payload: dict) -> tuple:
        """
        推送报告。
        payload: DiagnosticResult 的完整 JSON（dict）
        返回 (ok: bool, message: str)
        """
        raise NotImplementedError
