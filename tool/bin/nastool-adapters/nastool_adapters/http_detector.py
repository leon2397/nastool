# -*- coding: utf-8 -*-
"""
HTTP Remote Detector

支持通过 HTTP API 远程检测设备。
用于跨网段设备检测和 relay_server 集成。

Usage:
    detector = RemoteHTTPDetector("http://192.168.1.100:8000")
    results = detector.run_diagnosis()
"""

import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from nastool_core.checks import CheckResult, CheckSeverity


@dataclass
class RemoteDeviceInfo:
    """远程设备信息"""
    device_id: str
    device_name: str
    hostname: str
    ip_address: str
    backend_type: str  # "synology", "qnap", "rockchip", "ai_nas"
    backend_version: str
    cpu_model: str
    cpu_cores: int
    memory_total: int


class RemoteHTTPDetector:
    """
    HTTP 远程检测器
    
    通过 HTTP API 与远程设备通信，执行诊断检测。
    """
    
    # API 端点
    ENDPOINTS = {
        "health": "/api/health",
        "device_info": "/api/device/info",
        "diagnose": "/api/diagnose",
        "full_diagnosis": "/api/diagnose/full",
        "checks": "/api/checks",
        "benchmark": "/api/benchmark",
    }
    
    def __init__(self, target_url: str, api_key: Optional[str] = None, timeout: int = 30):
        """
        初始化远程检测器
        
        Args:
            target_url: 目标 URL，如 http://192.168.1.100:8000
            api_key: API 密钥（可选）
            timeout: 请求超时（秒）
        """
        self.target_url = target_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self._connected = False
        self._device_info: Optional[RemoteDeviceInfo] = None
        
    def _url(self, path: str) -> str:
        """构建完整 URL"""
        return f"{self.target_url}{path}"
    
    def _request(self, method: str, path: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """发送 HTTP 请求"""
        url = self._url(path)
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NASTool-Remote/2.0"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            if method == "GET":
                req = urllib.request.Request(url, headers=headers)
            else:
                body = json.dumps(data).encode('utf-8') if data else b'{}'
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
                
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
                print(f"HTTP {e.code}: {error_body}")
            except:
                print(f"HTTP {e.code}")
            return None
            
        except urllib.error.URLError as e:
            print(f"连接失败: {e.reason}")
            return None
            
        except Exception as e:
            print(f"请求异常: {e}")
            return None
    
    # ========== 连接管理 ==========
    
    def connect(self) -> bool:
        """连接到远程设备"""
        result = self._request("GET", self.ENDPOINTS["health"])
        
        if result:
            self._connected = True
            print(f"[OK] 已连接到 {self.target_url}")
            return True
        else:
            print(f"[X] 无法连接到 {self.target_url}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self._connected = False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    # ========== 设备信息 ==========
    
    def get_device_info(self) -> Optional[RemoteDeviceInfo]:
        """获取远程设备信息"""
        if not self._connected:
            print("请先调用 connect()")
            return None
            
        result = self._request("GET", self.ENDPOINTS["device_info"])
        
        if result:
            self._device_info = RemoteDeviceInfo(
                device_id=result.get("device_id", ""),
                device_name=result.get("device_name", ""),
                hostname=result.get("hostname", ""),
                ip_address=result.get("ip_address", ""),
                backend_type=result.get("backend_type", ""),
                backend_version=result.get("backend_version", ""),
                cpu_model=result.get("cpu_model", ""),
                cpu_cores=result.get("cpu_cores", 0),
                memory_total=result.get("memory_total", 0),
            )
            return self._device_info
        
        return None
    
    # ========== 诊断检测 ==========
    
    def run_diagnosis(self, full_mode: bool = False) -> List[CheckResult]:
        """
        运行远程诊断
        
        Args:
            full_mode: 是否运行完整诊断（含基准测试）
            
        Returns:
            检测结果列表
        """
        if not self._connected:
            print("请先调用 connect()")
            return []
        
        # 调用诊断 API
        endpoint = self.ENDPOINTS["full_diagnosis"] if full_mode else self.ENDPOINTS["diagnose"]
        result = self._request("GET", endpoint)
        
        if not result:
            print("诊断请求失败")
            return []
        
        # 解析结果
        results = []
        for item in result.get("results", []):
            check = CheckResult(
                check_id=item.get("check_id", ""),
                name=item.get("name", ""),
                severity=item.get("severity", "INFO"),
                passed=item.get("passed", True),
                summary=item.get("summary", ""),
                details=item.get("details", ""),
                value=item.get("value"),
                threshold=item.get("threshold", ""),
                fix_suggestion=item.get("fix_suggestion", ""),
            )
            results.append(check)
        
        return results
    
    def run_checks(self, categories: Optional[List[str]] = None) -> List[CheckResult]:
        """
        运行特定类别的检测
        
        Args:
            categories: 检测类别列表，如 ["ai", "nas", "network"]
            
        Returns:
            检测结果列表
        """
        if not self._connected:
            print("请先调用 connect()")
            return []
        
        params = {}
        if categories:
            params["categories"] = ",".join(categories)
        
        # 构建 URL 参数
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        endpoint = self.ENDPOINTS["checks"]
        if query:
            endpoint += f"?{query}"
        
        result = self._request("GET", endpoint)
        
        if not result:
            return []
        
        results = []
        for item in result.get("checks", []):
            check = CheckResult(
                check_id=item.get("check_id", ""),
                name=item.get("name", ""),
                severity=item.get("severity", "INFO"),
                passed=item.get("passed", True),
                summary=item.get("summary", ""),
                details=item.get("details", ""),
                value=item.get("value"),
                threshold=item.get("threshold", ""),
                fix_suggestion=item.get("fix_suggestion", ""),
            )
            results.append(check)
        
        return results
    
    def run_benchmark(self, model: str = "mobilenetv2") -> Dict[str, Any]:
        """
        运行远程基准测试
        
        Args:
            model: 基准测试模型
            
        Returns:
            基准测试结果
        """
        if not self._connected:
            print("请先调用 connect()")
            return {}
        
        result = self._request("POST", self.ENDPOINTS["benchmark"], {"model": model})
        
        return result or {}
    
    # ========== 便捷方法 ==========
    
    def quick_diagnosis(self) -> Dict[str, Any]:
        """快速诊断（连接 + 设备信息 + 诊断）"""
        if not self.connect():
            return {"error": "连接失败"}
        
        device_info = self.get_device_info()
        results = self.run_diagnosis(full_mode=False)
        
        # 统计
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        
        return {
            "device": device_info.__dict__ if device_info else {},
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
            },
            "results": [r.__dict__ for r in results]
        }


def detect_remote_target(target: str) -> RemoteHTTPDetector:
    """
    自动检测目标类型并返回对应的检测器
    
    Args:
        target: 目标地址 (http://host:port 或 user@host)
        
    Returns:
        对应的检测器实例
    """
    if target.startswith("http://") or target.startswith("https://"):
        # HTTP/HTTPS 目标
        return RemoteHTTPDetector(target)
    elif "@" in target:
        # SSH 目标（需要通过中转服务器）
        # TODO: 实现 SSH 隧道
        raise NotImplementedError("SSH 目标需要通过 relay_server 中转")
    else:
        # 默认为 HTTP
        return RemoteHTTPDetector(f"http://{target}")
