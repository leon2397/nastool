# -*- coding: utf-8 -*-
"""
Relay Server Detector

通过 relay_server 中继检测远程 RK/NAS 设备。
支持跨网段设备发现、命令下发、结果收集。

Usage:
    detector = RelayDetector("http://120.77.249.3:18888")
    devices = detector.list_devices()
    result = detector.run_diagnosis("nvidia-01")
"""

import json
import time
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from nastool_core.checks import CheckResult, CheckSeverity, CheckCategory
from nastool_adapters.utils.retry import RetryConfig, DEFAULT_RETRY_CONFIG


@dataclass
class RelayDeviceInfo:
    """Relay 中继设备信息"""
    device_id: str
    device_name: str
    device_type: str
    status: str  # "online" | "offline"
    hostname: str
    ip_local: str
    version: str
    capabilities: List[str]
    group: str
    last_seen: int
    registered_at: int


class RelayDetector:
    """
    Relay Server 远程检测器
    
    通过 relay_server 中继连接远程设备，下发检测命令，收集诊断结果。
    
    工作流程:
    1. 连接 relay_server
    2. 发现在线设备
    3. 下发诊断命令
    4. 轮询命令结果
    5. 解析诊断报告
    """
    
    # 默认诊断脚本（在远程设备上执行）
    DIAGNOSIS_SCRIPT = (
        "python3 -c \""
        "import json, platform, os, subprocess; "
        "r = {"
        "'hostname': platform.node(), "
        "'os': platform.system(), "
        "'arch': platform.machine(), "
        "'cpu_count': os.cpu_count(), "
        "'python': platform.python_version()"
        "}; "
        "print(json.dumps(r))"
        "\""
    )
    
    # NPU 检测脚本（Rockchip 设备）
    NPU_DIAGNOSIS_SCRIPT = (
        "python3 -c \""
        "import json, os; "
        "r = {'npu_driver': False, 'rknn_runtime': False, 'rknpu_util': 'N/A'}; "
        "r['npu_driver'] = os.path.exists('/dev/rknpu'); "
        "try: "
        "  import rknn.api; r['rknn_runtime'] = True "
        "except: pass; "
        "try: "
        "  with open('/sys/class/rknpu/rknpu0/utilization') as f: r['rknpu_util'] = f.read().strip() "
        "except: pass; "
        "print(json.dumps(r))"
        "\""
    )
    
    def __init__(
        self,
        relay_url: str = "http://120.77.249.3:18888",
        api_key: Optional[str] = None,
        timeout: int = 30,
        poll_interval: float = 2.0,
        max_polls: int = 30,
        retry_config: Optional[RetryConfig] = None,
    ):
        """
        初始化 Relay 检测器
        
        Args:
            relay_url: Relay Server URL
            api_key: API 密钥（可选，某些端点需要）
            timeout: HTTP 请求超时
            poll_interval: 命令结果轮询间隔（秒）
            max_polls: 最大轮询次数
            retry_config: 重试配置（可选，默认使用 DEFAULT_RETRY_CONFIG）
        """
        self.relay_url = relay_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_polls = max_polls
        self.retry_config = retry_config or DEFAULT_RETRY_CONFIG
        self._connected = False
        
    def _url(self, path: str) -> str:
        return f"{self.relay_url}{path}"
    
    def _request_no_retry(self, method: str, path: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """发送 HTTP 请求到 relay_server（无重试）"""
        url = self._url(path)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NASTool-Relay/2.0"
        }
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
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
                print(f"HTTP {e.code}: {error_body[:200]}")
            except Exception as decode_err:
                print(f"HTTP {e.code} (decode error: {decode_err})")
            return None
            
        except urllib.error.URLError as e:
            print(f"连接 relay_server 失败: {e.reason}")
            raise
            
        except Exception as e:
            print(f"请求异常: {e}")
            return None
    
    def _request_with_retry(self, method: str, path: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """发送 HTTP 请求到 relay_server（带重试）"""
        max_retries = self.retry_config.max_retries
        delay = self.retry_config.delay
        backoff = self.retry_config.backoff
        current_delay = delay
        
        for attempt in range(max_retries + 1):
            try:
                return self._request_no_retry(method, path, data)
            except (ConnectionError, TimeoutError, OSError, urllib.error.URLError) as e:
                if attempt < max_retries:
                    print(f"[RETRY] 请求失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    print(f"[RETRY] {current_delay:.1f} 秒后重试...")
                    time.sleep(current_delay)
                    current_delay *= backoff
                else:
                    print(f"[FAIL] 请求在 {max_retries + 1} 次尝试后仍然失败: {e}")
                    return None
            except Exception as e:
                print(f"[ERROR] 请求异常: {e}")
                return None
        
        return None
    
    def _request(self, method: str, path: str, data: Optional[Dict] = None, use_retry: bool = True) -> Optional[Dict]:
        """发送 HTTP 请求到 relay_server"""
        if use_retry and self.retry_config.enable:
            return self._request_with_retry(method, path, data)
        else:
            return self._request_no_retry(method, path, data)
    
    # ========== 连接管理 ==========
    
    def connect(self) -> bool:
        """连接到 relay_server"""
        result = self._request("GET", "/health")
        
        if result and result.get("status") == "ok":
            self._connected = True
            print(f"[OK] Connected to relay_server: {self.relay_url}")
            print(f"  Version: {result.get('version', 'unknown')}")
            return True
        else:
            print(f"[FAIL] Cannot connect to relay_server: {self.relay_url}")
            return False
    
    def is_connected(self) -> bool:
        return self._connected
    
    # ========== 设备发现 ==========
    
    def list_devices(self) -> List[RelayDeviceInfo]:
        """列出所有已注册设备"""
        if not self._connected:
            print("请先调用 connect()")
            return []
        
        result = self._request("GET", "/devices")
        
        if not result:
            return []
        
        devices = []
        for d in result.get("devices", []):
            devices.append(RelayDeviceInfo(
                device_id=d.get("device_id", ""),
                device_name=d.get("device_name", ""),
                device_type=d.get("device_type", ""),
                status=d.get("status", "offline"),
                hostname=d.get("hostname", ""),
                ip_local=d.get("ip_local", ""),
                version=d.get("version", ""),
                capabilities=d.get("capabilities", []),
                group=d.get("group", "default"),
                last_seen=d.get("last_seen", 0),
                registered_at=d.get("registered_at", 0),
            ))
        
        return devices
    
    def list_online_devices(self) -> List[RelayDeviceInfo]:
        """列出在线设备"""
        return [d for d in self.list_devices() if d.status == "online"]
    
    def get_device(self, device_id: str) -> Optional[RelayDeviceInfo]:
        """获取指定设备信息"""
        if not self._connected:
            return None
        
        result = self._request("GET", f"/devices/{device_id}")
        
        if not result:
            return None
        
        return RelayDeviceInfo(
            device_id=result.get("device_id", ""),
            device_name=result.get("device_name", ""),
            device_type=result.get("device_type", ""),
            status=result.get("status", "offline"),
            hostname=result.get("hostname", ""),
            ip_local=result.get("ip_local", ""),
            version=result.get("version", ""),
            capabilities=result.get("capabilities", []),
            group=result.get("group", "default"),
            last_seen=result.get("last_seen", 0),
            registered_at=result.get("registered_at", 0),
        )
    
    # ========== 命令下发 ==========
    
    def send_command(self, device_id: str, cmd: str, timeout_ms: int = 30000) -> Optional[str]:
        """
        向远程设备下发命令
        
        Args:
            device_id: 设备 ID
            cmd: 命令字符串
            timeout_ms: 命令超时（毫秒）
            
        Returns:
            命令 ID（用于查询结果），失败返回 None
        """
        if not self._connected:
            print("请先调用 connect()")
            return None
        
        result = self._request("POST", f"/devices/{device_id}/commands", {
            "cmd": cmd,
            "timeout_ms": timeout_ms
        })
        
        if result:
            command_id = result.get("command_id")
            status = result.get("status")
            print(f"  命令已下发: {command_id} (状态: {status})")
            return command_id
        
        return None
    
    def get_command_result(self, device_id: str, command_id: str) -> Optional[Dict]:
        """
        查询命令执行结果
        
        Args:
            device_id: 设备 ID
            command_id: 命令 ID
            
        Returns:
            命令结果字典
        """
        return self._request("GET", f"/devices/{device_id}/commands/{command_id}")
    
    def wait_for_command(self, device_id: str, command_id: str) -> Optional[Dict]:
        """
        等待命令执行完成
        
        Args:
            device_id: 设备 ID
            command_id: 命令 ID
            
        Returns:
            命令结果（包含 stdout, stderr, exit_code）
        """
        for i in range(self.max_polls):
            result = self.get_command_result(device_id, command_id)
            
            if not result:
                time.sleep(self.poll_interval)
                continue
            
            status = result.get("status")
            
            if status == "completed":
                return result
            elif status in ("failed", "timeout"):
                print(f"  命令执行失败: {status}")
                return result
            elif status == "queued":
                if i % 5 == 0:
                    print(f"  等待设备上线... (状态: {status})")
            elif status == "sent":
                if i % 5 == 0:
                    print(f"  等待命令执行... (状态: {status})")
            
            time.sleep(self.poll_interval)
        
        print(f"  命令超时（等待了 {self.max_polls * self.poll_interval:.0f} 秒）")
        return None
    
    # ========== 诊断检测 ==========
    
    def run_diagnosis(self, device_id: str, full_mode: bool = False) -> List[CheckResult]:
        """
        通过 relay_server 对远程设备执行诊断
        
        Args:
            device_id: 设备 ID
            full_mode: 是否完整诊断（含基准测试）
            
        Returns:
            检测结果列表
        """
        if not self._connected:
            print("请先调用 connect()")
            return []
        
        # 检查设备在线状态
        device = self.get_device(device_id)
        if not device:
            print(f"设备 {device_id} 未找到")
            return []
        
        if device.status != "online":
            print(f"设备 {device_id} 离线，命令将排队等待")
        
        # 步骤 1：基本信息采集
        print(f"\n[1/3] 采集设备基本信息...")
        cmd_id = self.send_command(device_id, self.DIAGNOSIS_SCRIPT)
        if not cmd_id:
            return []
        
        basic_result = self.wait_for_command(device_id, cmd_id)
        basic_info = {}
        if basic_result and basic_result.get("exit_code") == 0:
            try:
                basic_info = json.loads(basic_result.get("stdout", "{}"))
            except json.JSONDecodeError:
                pass
        
        # 步骤 2：NPU 检测（Rockchip 设备）
        print(f"[2/3] 检测 NPU 状态...")
        npu_info = {}
        cmd_id = self.send_command(device_id, self.NPU_DIAGNOSIS_SCRIPT)
        if cmd_id:
            npu_result = self.wait_for_command(device_id, cmd_id)
            if npu_result and npu_result.get("exit_code") == 0:
                try:
                    npu_info = json.loads(npu_result.get("stdout", "{}"))
                except json.JSONDecodeError:
                    pass
        
        # 步骤 3：获取历史诊断报告（如果有）
        print(f"[3/3] 获取诊断报告...")
        report = self._request("GET", f"/devices/{device_id}/reports/latest")
        
        # 组装检测结果
        results = []
        
        # 基本信息检测项
        if basic_info:
            results.append(CheckResult(
                check_id="remote_hostname",
                title="Hostname",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.PASSED if basic_info.get("hostname") else CheckSeverity.WARNING,
                passed=bool(basic_info.get("hostname")),
                current=basic_info.get("hostname", "N/A"),
                expected="non-empty",
                message=f"Hostname: {basic_info.get('hostname', 'N/A')}",
                details={"basic_info": basic_info},
            ))
            
            results.append(CheckResult(
                check_id="remote_arch",
                title="Architecture",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.PASSED,
                passed=True,
                current=basic_info.get("arch", "N/A"),
                expected="aarch64/arm64",
                message=f"Arch: {basic_info.get('arch', 'N/A')}",
            ))
            
            results.append(CheckResult(
                check_id="remote_cpu_count",
                title="CPU Cores",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.PASSED if basic_info.get("cpu_count", 0) > 0 else CheckSeverity.WARNING,
                passed=basic_info.get("cpu_count", 0) > 0,
                current=str(basic_info.get("cpu_count", 0)),
                expected=">0",
                message=f"CPU cores: {basic_info.get('cpu_count', 'N/A')}",
            ))
        
        # NPU 检测项
        if npu_info:
            results.append(CheckResult(
                check_id="remote_npu_driver",
                title="NPU Driver",
                category=CheckCategory.AI,
                severity=CheckSeverity.PASSED if npu_info.get("npu_driver") else CheckSeverity.CRITICAL,
                passed=npu_info.get("npu_driver", False),
                current=str(npu_info.get("npu_driver")),
                expected="True",
                message=f"NPU driver: {'loaded' if npu_info.get('npu_driver') else 'not loaded'}",
                fix_description="安装 Rockchip NPU 驱动" if not npu_info.get("npu_driver") else "",
            ))
            
            results.append(CheckResult(
                check_id="remote_rknn_runtime",
                title="RKNN Runtime",
                category=CheckCategory.AI,
                severity=CheckSeverity.PASSED if npu_info.get("rknn_runtime") else CheckSeverity.WARNING,
                passed=npu_info.get("rknn_runtime", False),
                current=str(npu_info.get("rknn_runtime")),
                expected="True",
                message="rknn.api import " + ("OK" if npu_info.get("rknn_runtime") else "failed"),
                fix_description="安装 rknn-toolkit2" if not npu_info.get("rknn_runtime") else "",
            ))
            
            if npu_info.get("rknpu_util") != "N/A":
                results.append(CheckResult(
                    check_id="remote_npu_utilization",
                    title="NPU Utilization",
                    category=CheckCategory.AI,
                    severity=CheckSeverity.INFO,
                    passed=True,
                    current=str(npu_info.get("rknpu_util", "")),
                    expected="",
                    message=f"NPU utilization: {npu_info.get('rknpu_util')}%",
                ))
        
        # 历史报告检测项
        if report and report.get("overall_score") is not None:
            score = report["overall_score"]
            results.append(CheckResult(
                check_id="remote_overall_score",
                title="Overall Health Score",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.PASSED if score >= 80 else (CheckSeverity.WARNING if score >= 60 else CheckSeverity.CRITICAL),
                passed=score >= 80,
                current=str(score),
                expected=">=80",
                message=f"Health score: {score}/100",
            ))
        
        return results
    
    def quick_scan(self) -> Dict[str, Any]:
        """
        快速扫描所有在线设备
        
        Returns:
            {
                "total": int,
                "online": int,
                "devices": [...]
            }
        """
        if not self.connect():
            return {"error": "无法连接 relay_server", "total": 0, "online": 0, "devices": []}
        
        devices = self.list_devices()
        online = [d for d in devices if d.status == "online"]
        
        return {
            "relay_url": self.relay_url,
            "total": len(devices),
            "online": len(online),
            "devices": [
                {
                    "device_id": d.device_id,
                    "device_name": d.device_name or d.device_id,
                    "status": d.status,
                    "hostname": d.hostname,
                    "type": d.device_type,
                }
                for d in devices
            ]
        }


def create_relay_detector(target: str, retry_config: Optional[RetryConfig] = None) -> RelayDetector:
    """
    创建 Relay 检测器
    
    Args:
        target: relay://host:port 或 http://host:port
        retry_config: 重试配置（可选）
        
    Returns:
        RelayDetector 实例
    """
    if target.startswith("relay://"):
        url = target.replace("relay://", "http://")
    elif target.startswith("http"):
        url = target
    else:
        url = f"http://{target}"
    
    return RelayDetector(url, retry_config=retry_config)
