"""
Synology Notification Center - 群晖通知中心集成

支持将诊断结果推送到群晖通知中心：
- 设备异常告警
- 存储空间警告
- 系统健康状态变更
- 诊断完成通知

通知方式：
- DSM 通知中心
- 邮件通知
- SMS 短信（需配置）
- Webhook 推送
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """通知级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """通知渠道"""

    DSM = "dsm"  # DSM 通知中心
    EMAIL = "email"  # 邮件
    SMS = "sms"  # 短信
    WEBHOOK = "webhook"  # Webhook
    PUSH = "push"  # 推送服务（如 Pushover）


@dataclass
class NotificationMessage:
    """通知消息"""

    title: str  # 标题
    message: str  # 消息内容
    level: NotificationLevel = NotificationLevel.INFO
    timestamp: float = None  # 时间戳
    source: str = "nastool"  # 来源

    # 扩展信息
    device_id: str = ""  # 设备 ID
    category: str = "diagnostic"  # 分类
    details: Dict = None  # 详细信息

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.details is None:
            self.details = {}

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "device_id": self.device_id,
            "category": self.category,
            "details": self.details,
        }


class SynologyNotifier:
    """
    群晖通知管理器

    将诊断结果推送到群晖通知中心。
    """

    # DSM 通知配置路径
    DSM_NOTIFY_PATH = "/usr/syno/etc/notification"
    DSM_LOG_PATH = "/var/log/synolog"

    # 通知模板
    TEMPLATES = {
        "device_offline": {
            "title": "设备离线告警",
            "message": "设备 {device_name} ({device_id}) 已离线，最后在线时间: {last_seen}",
            "level": NotificationLevel.ERROR,
        },
        "storage_warning": {
            "title": "存储空间警告",
            "message": "存储池 {pool_name} 可用空间不足 {available_percent}%，建议清理或扩容",
            "level": NotificationLevel.WARNING,
        },
        "storage_critical": {
            "title": "存储空间严重不足",
            "message": "存储池 {pool_name} 可用空间仅剩 {available_percent}%，请立即处理！",
            "level": NotificationLevel.CRITICAL,
        },
        "health_degraded": {
            "title": "系统健康状态降级",
            "message": "系统健康分数从 {old_score} 降至 {new_score}，主要问题: {issues}",
            "level": NotificationLevel.WARNING,
        },
        "diagnostic_complete": {
            "title": "诊断完成",
            "message": "设备 {device_name} 诊断完成，健康分数: {health_score}，发现问题: {issue_count}",
            "level": NotificationLevel.INFO,
        },
        "ai_accelerator_error": {
            "title": "AI 加速器异常",
            "message": "AI 加速器 {accelerator} 检测异常: {error}",
            "level": NotificationLevel.ERROR,
        },
    }

    def __init__(self, config: Dict = None):
        """
        初始化通知管理器

        Args:
            config: 通知配置
        """
        self.config = config or {}
        self.channels = self.config.get("channels", [NotificationChannel.DSM])
        self.email_config = self.config.get("email", {})
        self.webhook_config = self.config.get("webhook", {})

        # 通知历史
        self.history: List[NotificationMessage] = []
        self.max_history = 100

        # 去重配置
        self.dedup_window = self.config.get("dedup_window", 3600)  # 1小时内去重
        self.sent_messages: Dict[str, float] = {}

    def send(self, notification: NotificationMessage) -> bool:
        """
        发送通知

        Args:
            notification: 通知消息

        Returns:
            True 如果发送成功
        """
        # 检查去重
        msg_key = self._get_message_key(notification)
        if msg_key in self.sent_messages:
            last_sent = self.sent_messages[msg_key]
            if time.time() - last_sent < self.dedup_window:
                logger.debug(f"Duplicate notification skipped: {notification.title}")
                return True

        # 发送到各渠道
        success = False
        for channel in self.channels:
            if channel == NotificationChannel.DSM:
                success = self._send_to_dsm(notification) or success
            elif channel == NotificationChannel.EMAIL:
                success = self._send_email(notification) or success
            elif channel == NotificationChannel.WEBHOOK:
                success = self._send_webhook(notification) or success

        # 记录发送历史
        if success:
            self.sent_messages[msg_key] = time.time()
            self.history.append(notification)

            # 限制历史长度
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history :]

        return success

    def send_from_template(self, template_name: str, **kwargs) -> bool:
        """
        使用模板发送通知

        Args:
            template_name: 模板名称
            **kwargs: 模板参数

        Returns:
            True 如果发送成功
        """
        if template_name not in self.TEMPLATES:
            logger.error(f"Unknown template: {template_name}")
            return False

        template = self.TEMPLATES[template_name]

        notification = NotificationMessage(
            title=template["title"],
            message=template["message"].format(**kwargs),
            level=template["level"],
            category=template_name,
        )

        return self.send(notification)

    def _get_message_key(self, notification: NotificationMessage) -> str:
        """生成消息去重 key"""
        return f"{notification.category}:{notification.title}:{hash(notification.message)}"

    def _send_to_dsm(self, notification: NotificationMessage) -> bool:
        """
        发送到 DSM 通知中心

        使用 synonotifytool 命令发送通知
        """
        try:
            # 构建命令
            cmd = (
                f"/usr/syno/bin/synonotifytool "
                f'--title "{notification.title}" '
                f'--content "{notification.message}" '
                f'--level "{notification.level.value}"'
            )

            # 执行命令
            result = os.system(cmd)

            if result == 0:
                logger.info(f"Sent to DSM: {notification.title}")
                return True
            else:
                logger.error(f"Failed to send to DSM: {result}")
                return False

        except Exception as e:
            logger.error(f"Error sending to DSM: {e}")
            return False

    def _send_email(self, notification: NotificationMessage) -> bool:
        """发送邮件通知"""
        if not self.email_config:
            return False

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # 创建邮件
            msg = MIMEMultipart()
            msg["From"] = self.email_config.get("from", "nastool@localhost")
            msg["To"] = self.email_config.get("to", "")
            msg["Subject"] = f"[{notification.level.value.upper()}] {notification.title}"

            # 邮件正文
            body = f"""
{notification.message}

---
Time: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(notification.timestamp))}
Level: {notification.level.value}
Source: {notification.source}
Device: {notification.device_id}
"""

            msg.attach(MIMEText(body, "plain"))

            # 发送邮件
            smtp_server = self.email_config.get("smtp_server", "localhost")
            smtp_port = self.email_config.get("smtp_port", 25)

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if self.email_config.get("username"):
                    server.login(
                        self.email_config["username"], self.email_config.get("password", "")
                    )
                server.send_message(msg)

            logger.info(f"Sent email: {notification.title}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def _send_webhook(self, notification: NotificationMessage) -> bool:
        """发送 Webhook 通知"""
        if not self.webhook_config or not self.webhook_config.get("url"):
            return False

        try:
            import urllib.request

            url = self.webhook_config["url"]
            data = json.dumps(notification.to_dict()).encode("utf-8")

            headers = {
                "Content-Type": "application/json",
            }

            if self.webhook_config.get("token"):
                headers["Authorization"] = f"Bearer {self.webhook_config['token']}"

            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"Sent webhook: {notification.title}")
                    return True
                else:
                    logger.error(f"Webhook failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            return False

    def get_history(self, limit: int = 20) -> List[NotificationMessage]:
        """
        获取通知历史

        Args:
            limit: 最大返回数量

        Returns:
            通知消息列表
        """
        return self.history[-limit:]

    def clear_history(self):
        """清空通知历史"""
        self.history.clear()
        self.sent_messages.clear()


def create_notifier(config: Dict = None) -> SynologyNotifier:
    """
    创建通知管理器

    Args:
        config: 通知配置

    Returns:
        通知管理器实例
    """
    return SynologyNotifier(config)


# 便捷函数
def notify_device_offline(device_name: str, device_id: str, last_seen: str):
    """通知设备离线"""
    notifier = create_notifier()
    return notifier.send_from_template(
        "device_offline", device_name=device_name, device_id=device_id, last_seen=last_seen
    )


def notify_storage_warning(pool_name: str, available_percent: float):
    """通知存储空间警告"""
    notifier = create_notifier()
    return notifier.send_from_template(
        "storage_warning", pool_name=pool_name, available_percent=available_percent
    )


def notify_storage_critical(pool_name: str, available_percent: float):
    """通知存储空间严重不足"""
    notifier = create_notifier()
    return notifier.send_from_template(
        "storage_critical", pool_name=pool_name, available_percent=available_percent
    )


def notify_diagnostic_complete(device_name: str, health_score: int, issue_count: int):
    """通知诊断完成"""
    notifier = create_notifier()
    return notifier.send_from_template(
        "diagnostic_complete",
        device_name=device_name,
        health_score=health_score,
        issue_count=issue_count,
    )


if __name__ == "__main__":
    # 测试
    notifier = create_notifier(
        {
            "channels": [NotificationChannel.DSM],
        }
    )

    # 测试通知
    print("Testing notifications...")

    # 创建测试通知
    test_notification = NotificationMessage(
        title="测试通知",
        message="这是一条来自 nastool 的测试通知",
        level=NotificationLevel.INFO,
    )

    # 发送（在非群晖环境中会失败，但不会报错）
    # notifier.send(test_notification)

    print("Notification module loaded successfully")
    print(f"Available templates: {list(SynologyNotifier.TEMPLATES.keys())}")
