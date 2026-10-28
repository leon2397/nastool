"""connectors/webhook.py — 通用 HTTP 上报

把完整诊断 JSON POST 到任意地址，附带自定义请求头。
适合：自建巡检接口、企业微信/钉钉/飞书机器人（配合其消息格式转换）、
      Prometheus pushgateway 前置脚本、自动化运维流水线。
"""
import json
import urllib.error
import urllib.request

from .base import BaseConnector


class WebhookConnector(BaseConnector):
    name = "webhook"

    def __init__(self, url: str = "", token: str = "",
                 timeout: int = 15, header_name: str = "Authorization", **kwargs):
        self.url = (url or "").strip()
        self.token = token or ""
        self.timeout = timeout
        self.header_name = header_name

    def push(self, payload: dict) -> tuple:
        if not self.url:
            return False, "未提供 webhook 地址（--push-url）"
        if not self.url.startswith(("http://", "https://")):
            return False, f"webhook 地址需以 http(s):// 开头：{self.url}"

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if self.token:
            headers[self.header_name] = self.token

        req = urllib.request.Request(self.url, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                code = resp.status
                text = resp.read(512).decode("utf-8", errors="replace")
            if 200 <= code < 300:
                return True, f"已上报到 {self.url}（HTTP {code}）"
            return False, f"上报失败：HTTP {code} {text[:120]}"
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read(200).decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass
            return False, f"上报失败：HTTP {e.code} {detail}"
        except Exception as e:  # noqa: BLE001
            return False, f"上报失败：{e}"
