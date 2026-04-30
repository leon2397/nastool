# -*- coding: utf-8 -*-
"""
SSH Remote Detector

支持通过 SSH 远程检测设备。
用于直接连接到设备并执行诊断检测。

Usage:
    detector = RemoteSSHDetector("192.168.1.100", username="admin", password="password")
    results = detector.run_diagnosis()
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import paramiko

from nastool_core.checks import CheckResult, CheckSeverity, CheckCategory
from nastool_adapters.utils.retry import RetryConfig, DEFAULT_RETRY_CONFIG


@dataclass
class RemoteDeviceInfo:
    """远程设备信息"""
    device_id: str
    device_name: str
    hostname: str
    ip_address: str
    backend_type: str
    backend_version: str
    cpu_model: str
    cpu_cores: int
    memory_total: int


class SSHConnectionError(Exception):
    """SSH 连接错误"""
    pass


class RemoteSSHDetector:
    """
    SSH 远程检测器

    通过 SSH 与远程设备通信，执行诊断检测。
    优化了命令执行性能，减少 SSH 连接次数。
    """

    def __init__(self, host: str, port: int = 22, username: str = "admin",
                 password: Optional[str] = None, timeout: int = 30,
                 retry_config: Optional[RetryConfig] = None,
                 command_timeout: int = 10):
        """
        初始化远程检测器

        Args:
            host: 目标主机 IP 地址
            port: SSH 端口
            username: SSH 用户名
            password: SSH 密码
            timeout: 连接超时（秒）
            retry_config: 重试配置（可选，默认使用 DEFAULT_RETRY_CONFIG）
            command_timeout: 命令执行超时（秒）
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.command_timeout = command_timeout
        self.retry_config = retry_config or DEFAULT_RETRY_CONFIG
        self._client: Optional[paramiko.SSHClient] = None
        self._transport: Optional[paramiko.Transport] = None
        self._connected = False
        self._device_info: Optional[RemoteDeviceInfo] = None
        self._last_command_time: float = 0
        self._connection_idle_timeout: int = 300

    def _get_ssh_client(self) -> paramiko.SSHClient:
        """获取或创建 SSH 客户端"""
        if self._client is None:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self._client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                banner_timeout=15,
                auth_timeout=15,
                allow_agent=False,
                look_for_keys=False
            )

            transport = self._client.get_transport()
            if transport:
                transport.set_keepalive(30)
                transport.window_size = 4 * 1024 * 1024

        return self._client

    def _execute_command(self, command: str, use_retry: bool = True) -> Optional[str]:
        """
        执行 SSH 命令

        Args:
            command: 要执行的命令
            use_retry: 是否使用重试机制

        Returns:
            命令输出或 None
        """
        if use_retry and self.retry_config.enable:
            return self._execute_command_with_retry(command)
        else:
            return self._execute_command_no_retry(command)

    def _execute_command_with_retry(self, command: str) -> Optional[str]:
        """执行 SSH 命令（带重试机制）"""
        max_retries = self.retry_config.max_retries
        delay = self.retry_config.delay
        backoff = self.retry_config.backoff
        current_delay = delay

        for attempt in range(max_retries + 1):
            try:
                return self._execute_single_command(command)
            except (ConnectionError, TimeoutError, OSError) as e:
                if attempt < max_retries:
                    print(f"[RETRY] SSH 命令执行失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    print(f"[RETRY] {current_delay:.1f} 秒后重试...")
                    time.sleep(current_delay)
                    current_delay *= backoff
                else:
                    print(f"[FAIL] SSH 命令执行在 {max_retries + 1} 次尝试后仍然失败: {e}")
                    return None
            except Exception as e:
                print(f"[ERROR] 执行命令失败: {e}")
                return None

        return None

    def _execute_command_no_retry(self, command: str) -> Optional[str]:
        """执行 SSH 命令（无重试）"""
        try:
            return self._execute_single_command(command)
        except Exception as e:
            print(f"[ERROR] 执行命令失败: {e}")
            return None

    def _execute_single_command(self, command: str) -> Optional[str]:
        """执行单个 SSH 命令"""
        client = self._get_ssh_client()
        self._last_command_time = time.time()

        stdin, stdout, stderr = client.exec_command(
            command,
            timeout=self.command_timeout,
            get_pty=False
        )

        exit_status = stdout.channel.recv_exit_status()

        output = stdout.read().decode('utf-8', errors='ignore').strip()
        error = stderr.read().decode('utf-8', errors='ignore').strip()

        if exit_status != 0 and error:
            print(f"[WARN] 命令退出码 {exit_status}: {error}")
            if not output:
                return None

        return output

    def execute_batch(self, commands: List[str]) -> List[Tuple[str, Optional[str]]]:
        """
        批量执行多个命令（在一次 SSH 会话中）

        Args:
            commands: 命令列表

        Returns:
            [(命令, 输出), ...] 的列表
        """
        if not self._connected:
            return [(cmd, None) for cmd in commands]

        results = []
        client = self._get_ssh_client()
        self._last_command_time = time.time()

        for command in commands:
            try:
                stdin, stdout, stderr = client.exec_command(
                    command,
                    timeout=self.command_timeout,
                    get_pty=False
                )

                exit_status = stdout.channel.recv_exit_status()
                output = stdout.read().decode('utf-8', errors='ignore').strip()
                error = stderr.read().decode('utf-8', errors='ignore').strip()

                if exit_status != 0 and error and not output:
                    results.append((command, None))
                else:
                    results.append((command, output))

            except Exception as e:
                print(f"[ERROR] 执行批量命令失败: {e}")
                results.append((command, None))

        return results

    def connect_with_retry(self) -> bool:
        """
        连接到远程设备（带重试机制）

        Returns:
            连接是否成功
        """
        max_retries = self.retry_config.max_retries
        delay = self.retry_config.delay
        backoff = self.retry_config.backoff
        current_delay = delay

        for attempt in range(max_retries + 1):
            try:
                return self._connect_single()
            except (ConnectionError, TimeoutError, OSError) as e:
                if attempt < max_retries:
                    print(f"[RETRY] SSH 连接失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    print(f"[RETRY] {current_delay:.1f} 秒后重试...")
                    time.sleep(current_delay)
                    current_delay *= backoff
                else:
                    print(f"[FAIL] SSH 连接在 {max_retries + 1} 次尝试后仍然失败: {e}")
                    return False
            except Exception as e:
                print(f"[ERROR] 连接异常: {e}")
                return False

        return False

    def _connect_single(self) -> bool:
        """执行单次 SSH 连接"""
        import socket

        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self._client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                banner_timeout=15,
                auth_timeout=15,
                allow_agent=False,
                look_for_keys=False
            )

            transport = self._client.get_transport()
            if transport:
                transport.set_keepalive(30)
                transport.window_size = 4 * 1024 * 1024

            self._connected = True
            print(f"[OK] 已连接到 {self.host}:{self.port}")
            return True
        except paramiko.AuthenticationException as e:
            print(f"[X] SSH 认证失败 {self.host}:{self.port}: {e}")
            raise SSHConnectionError(f"认证失败: {e}") from e
        except paramiko.SSHException as e:
            print(f"[X] SSH 连接错误 {self.host}:{self.port}: {e}")
            raise SSHConnectionError(f"SSH 连接错误: {e}") from e
        except socket.timeout:
            print(f"[X] SSH 连接超时 {self.host}:{self.port}")
            raise TimeoutError(f"连接超时") from None
        except Exception as e:
            print(f"[X] 无法连接到 {self.host}:{self.port}: {e}")
            raise ConnectionError(f"连接失败: {e}") from e

    def connect(self, use_retry: bool = True) -> bool:
        """
        连接到远程设备

        Args:
            use_retry: 是否使用重试机制

        Returns:
            连接是否成功
        """
        if use_retry and self.retry_config.enable:
            return self.connect_with_retry()
        else:
            return self._connect_single()

    def disconnect(self):
        """断开连接"""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._connected = False

    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self._connected:
            return False

        if self._client:
            transport = self._client.get_transport()
            if transport and not transport.is_active():
                self._connected = False
                return False

        return self._connected

    def get_device_info(self, use_batch: bool = True) -> Optional[RemoteDeviceInfo]:
        """
        获取远程设备信息

        Args:
            use_batch: 是否使用批量命令执行（性能优化）
        """
        if not self._connected:
            print("请先调用 connect()")
            return None

        if use_batch:
            commands = [
                "hostname",
                "cat /proc/cpuinfo | grep 'model name' | head -1",
                "nproc",
                "free -m | grep 'Mem:'",
                "uname -a",
            ]

            results = self.execute_batch(commands)

            hostname = results[0][1] or "" if len(results) > 0 else ""
            cpu_info = results[1][1] or "" if len(results) > 1 else ""
            cpu_model = cpu_info.replace("model name\t: ", "") if cpu_info else "Unknown"
            cpu_cores = results[2][1] or "1" if len(results) > 2 else "1"
            memory_info = results[3][1] or "" if len(results) > 3 else ""
            os_info = results[4][1] or "" if len(results) > 4 else ""

            memory_total = "0"
            if memory_info:
                parts = memory_info.split()
                if len(parts) >= 2:
                    memory_total = parts[1]

            backend_type = "linux"
            backend_version = os_info.split()[2] if os_info else "Unknown"

            self._device_info = RemoteDeviceInfo(
                device_id=f"{self.host}:{self.port}",
                device_name=hostname,
                hostname=hostname,
                ip_address=self.host,
                backend_type=backend_type,
                backend_version=backend_version,
                cpu_model=cpu_model,
                cpu_cores=int(cpu_cores),
                memory_total=int(memory_total)
            )
        else:
            hostname = self._execute_command("hostname") or ""
            ip_address = self.host
            cpu_info = self._execute_command("cat /proc/cpuinfo | grep 'model name' | head -1") or ""
            cpu_model = cpu_info.replace("model name\t: ", "") if cpu_info else "Unknown"
            cpu_cores = self._execute_command("nproc") or "1"
            memory_info = self._execute_command("free -m | grep 'Mem:'") or ""
            memory_total = "0"
            if memory_info:
                parts = memory_info.split()
                if len(parts) >= 2:
                    memory_total = parts[1]
            os_info = self._execute_command("uname -a") or ""
            backend_type = "linux"
            backend_version = os_info.split()[2] if os_info else "Unknown"

            self._device_info = RemoteDeviceInfo(
                device_id=f"{self.host}:{self.port}",
                device_name=hostname,
                hostname=hostname,
                ip_address=ip_address,
                backend_type=backend_type,
                backend_version=backend_version,
                cpu_model=cpu_model,
                cpu_cores=int(cpu_cores),
                memory_total=int(memory_total)
            )

        return self._device_info

    def run_diagnosis(self, full_mode: bool = False, use_batch: bool = True) -> List[CheckResult]:
        """
        运行远程诊断

        Args:
            full_mode: 是否运行完整诊断（含基准测试）
            use_batch: 是否使用批量命令执行（性能优化）

        Returns:
            检测结果列表
        """
        if not self._connected:
            print("请先调用 connect()")
            return []

        if use_batch:
            results = self._run_diagnosis_batch(full_mode)
        else:
            results = self._run_diagnosis_single(full_mode)

        return results

    def _run_diagnosis_batch(self, full_mode: bool) -> List[CheckResult]:
        """使用批量命令执行进行诊断（性能优化）"""
        batch_commands = {
            "uptime": "uptime",
            "uptime_pretty": "uptime -p",
            "load_avg": "cat /proc/loadavg",
            "ip_addr": "ip addr show",
            "df_h": "df -h",
            "ps_count": "ps aux | wc -l",
            "top_cpu": "top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'",
        }

        if full_mode:
            batch_commands.update({
                "free_m": "free -m",
                "meminfo": "cat /proc/meminfo | head -5",
            })

        results_list = self.execute_batch(list(batch_commands.values()))
        results_map = dict(zip(batch_commands.keys(), [r[1] for r in results_list]))

        results = []

        load_avg = results_map.get("load_avg") or ""
        if load_avg:
            parts = load_avg.split()
            if len(parts) >= 3:
                load_1, load_5, load_15 = parts[0], parts[1], parts[2]
                results.append(CheckResult(
                    check_id="system_load",
                    title="系统负载",
                    category=CheckCategory.SYSTEM,
                    severity=CheckSeverity.INFO,
                    passed=True,
                    current=f"{load_1} (1m), {load_5} (5m), {load_15} (15m)",
                    expected="< 1.0 (理想状态)",
                    message=f"系统负载: {load_1}, {load_5}, {load_15}"
                ))

        uptime_pretty = results_map.get("uptime_pretty") or ""
        if uptime_pretty:
            results.append(CheckResult(
                check_id="system_uptime",
                title="系统运行时间",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.INFO,
                passed=True,
                current=uptime_pretty,
                expected="正常运行",
                message=f"系统运行时间: {uptime_pretty}"
            ))

        ip_addr = results_map.get("ip_addr") or ""
        if ip_addr:
            active_interfaces = sum(1 for line in ip_addr.split('\n') if 'inet ' in line)
            results.append(CheckResult(
                check_id="network_interfaces",
                title="网络接口",
                category=CheckCategory.NETWORK,
                severity=CheckSeverity.INFO,
                passed=True,
                current=f"{active_interfaces} 个活跃接口",
                expected="至少 1 个活跃接口",
                message=f"检测到 {active_interfaces} 个活跃网络接口"
            ))

        dns_check = self._execute_command("ping -c 1 -W 2 google.com") or ""
        dns_ok = "64 bytes" in dns_check
        results.append(CheckResult(
            check_id="network_dns",
            title="DNS 解析",
            category=CheckCategory.NETWORK,
            severity=CheckSeverity.CRITICAL if not dns_ok else CheckSeverity.INFO,
            passed=dns_ok,
            current="正常" if dns_ok else "失败",
            expected="正常",
            message="DNS 解析正常" if dns_ok else "DNS 解析失败"
        ))

        df_h = results_map.get("df_h") or ""
        if df_h:
            lines = df_h.split('\n')[1:]
            for line in lines:
                if line:
                    parts = line.split()
                    if len(parts) >= 6:
                        filesystem = parts[0]
                        use_percent = parts[4]
                        available = parts[3]
                        mount_point = parts[5]

                        if use_percent.endswith('%'):
                            percent = int(use_percent.rstrip('%'))
                            severity = CheckSeverity.CRITICAL if percent > 90 else CheckSeverity.WARNING if percent > 70 else CheckSeverity.INFO

                            results.append(CheckResult(
                                check_id=f"storage_{filesystem.replace('/', '_').replace('.', '_')}",
                                title=f"磁盘使用 - {mount_point}",
                                category=CheckCategory.STORAGE,
                                severity=severity,
                                passed=percent < 90,
                                current=f"{use_percent} (可用: {available})",
                                expected="< 90%",
                                message=f"{filesystem} 挂载在 {mount_point}，使用 {use_percent}"
                            ))

        process_count = results_map.get("ps_count") or "0"
        try:
            count = int(process_count)
            results.append(CheckResult(
                check_id="process_count",
                title="运行进程数",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.INFO,
                passed=count < 1000,
                current=str(count),
                expected="< 1000",
                message=f"当前运行 {count} 个进程"
            ))
        except ValueError:
            pass

        cpu_usage_str = results_map.get("top_cpu") or "0"
        try:
            cpu_usage = float(cpu_usage_str)
            severity = CheckSeverity.CRITICAL if cpu_usage > 90 else CheckSeverity.WARNING if cpu_usage > 70 else CheckSeverity.INFO
            results.append(CheckResult(
                check_id="cpu_usage",
                title="CPU 使用率",
                category=CheckCategory.SYSTEM,
                severity=severity,
                passed=cpu_usage < 90,
                current=f"{cpu_usage:.1f}%",
                expected="< 90%",
                message=f"CPU 使用率: {cpu_usage:.1f}%"
            ))
        except ValueError:
            pass

        if full_mode:
            free_m = results_map.get("free_m") or ""
            if free_m:
                lines = free_m.split('\n')
                if len(lines) > 1:
                    mem_line = lines[1]
                    parts = mem_line.split()
                    if len(parts) >= 4:
                        try:
                            total = int(parts[1])
                            used = int(parts[2])
                            free = int(parts[3])
                            if total > 0:
                                used_percent = (used / total) * 100
                                severity = CheckSeverity.CRITICAL if used_percent > 90 else CheckSeverity.WARNING if used_percent > 70 else CheckSeverity.INFO
                                results.append(CheckResult(
                                    check_id="memory_usage",
                                    title="内存使用率",
                                    category=CheckCategory.SYSTEM,
                                    severity=severity,
                                    passed=used_percent < 90,
                                    current=f"{used_percent:.1f}% (可用: {free}MB)",
                                    expected="< 90%",
                                    message=f"内存使用: {used}MB / {total}MB"
                                ))
                        except (ValueError, IndexError):
                            pass

            log_errors = self._execute_command("grep -i error /var/log/syslog 2>/dev/null | tail -10") or ""
            has_errors = len(log_errors) > 0
            results.append(CheckResult(
                check_id="system_logs",
                title="系统日志错误",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.WARNING if has_errors else CheckSeverity.INFO,
                passed=not has_errors,
                current="有错误" if has_errors else "无错误",
                expected="无错误",
                message="系统日志中存在错误" if has_errors else "系统日志正常"
            ))

        return results

    def _run_diagnosis_single(self, full_mode: bool) -> List[CheckResult]:
        """使用单独命令执行进行诊断（传统方式）"""
        results = []

        results.extend(self._check_system_info())
        results.extend(self._check_network())
        results.extend(self._check_storage())
        results.extend(self._check_processes())

        if full_mode:
            results.extend(self._check_additional())

        return results

    def _check_system_info(self) -> List[CheckResult]:
        """检查系统信息"""
        results = []

        load_avg = self._execute_command("uptime") or ""
        if load_avg:
            parts = load_avg.split("load average:")
            if len(parts) > 1:
                load = parts[1].strip()
                results.append(CheckResult(
                    check_id="system_load",
                    title="系统负载",
                    category=CheckCategory.SYSTEM,
                    severity=CheckSeverity.INFO,
                    passed=True,
                    current=load,
                    expected="< 1.0 (理想状态)",
                    message=f"系统负载: {load}"
                ))

        uptime = self._execute_command("uptime -p") or ""
        if uptime:
            results.append(CheckResult(
                check_id="system_uptime",
                title="系统运行时间",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.INFO,
                passed=True,
                current=uptime,
                expected="正常运行",
                message=f"系统运行时间: {uptime}"
            ))

        return results

    def _check_network(self) -> List[CheckResult]:
        """检查网络状态"""
        results = []

        interfaces = self._execute_command("ip addr show") or ""
        if interfaces:
            active_interfaces = sum(1 for line in interfaces.split('\n') if 'inet ' in line)
            results.append(CheckResult(
                check_id="network_interfaces",
                title="网络接口",
                category=CheckCategory.NETWORK,
                severity=CheckSeverity.INFO,
                passed=True,
                current=f"{active_interfaces} 个活跃接口",
                expected="至少 1 个活跃接口",
                message=f"检测到 {active_interfaces} 个活跃网络接口"
            ))

        dns_check = self._execute_command("ping -c 1 -W 2 google.com") or ""
        dns_ok = "64 bytes" in dns_check
        results.append(CheckResult(
            check_id="network_dns",
            title="DNS 解析",
            category=CheckCategory.NETWORK,
            severity=CheckSeverity.CRITICAL if not dns_ok else CheckSeverity.INFO,
            passed=dns_ok,
            current="正常" if dns_ok else "失败",
            expected="正常",
            message="DNS 解析正常" if dns_ok else "DNS 解析失败"
        ))

        return results

    def _check_storage(self) -> List[CheckResult]:
        """检查存储状态"""
        results = []

        df_output = self._execute_command("df -h") or ""
        if df_output:
            lines = df_output.split('\n')[1:]
            for line in lines:
                if line:
                    parts = line.split()
                    if len(parts) >= 6:
                        filesystem = parts[0]
                        use_percent = parts[4]
                        available = parts[3]
                        mount_point = parts[5]

                        if use_percent.endswith('%'):
                            percent = int(use_percent.rstrip('%'))
                            severity = CheckSeverity.CRITICAL if percent > 90 else CheckSeverity.WARNING if percent > 70 else CheckSeverity.INFO

                            results.append(CheckResult(
                                check_id=f"storage_{filesystem.replace('/', '_').replace('.', '_')}",
                                title=f"磁盘使用 - {mount_point}",
                                category=CheckCategory.STORAGE,
                                severity=severity,
                                passed=percent < 90,
                                current=f"{use_percent} (可用: {available})",
                                expected="< 90%",
                                message=f"{filesystem} 挂载在 {mount_point}，使用 {use_percent}"
                            ))

        return results

    def _check_processes(self) -> List[CheckResult]:
        """检查进程状态"""
        results = []

        process_count = self._execute_command("ps aux | wc -l") or "0"
        try:
            count = int(process_count)
            results.append(CheckResult(
                check_id="process_count",
                title="运行进程数",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.INFO,
                passed=count < 1000,
                current=str(count),
                expected="< 1000",
                message=f"当前运行 {count} 个进程"
            ))
        except ValueError:
            pass

        cpu_usage = self._execute_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'") or "0"
        try:
            usage = float(cpu_usage)
            severity = CheckSeverity.CRITICAL if usage > 90 else CheckSeverity.WARNING if usage > 70 else CheckSeverity.INFO
            results.append(CheckResult(
                check_id="cpu_usage",
                title="CPU 使用率",
                category=CheckCategory.SYSTEM,
                severity=severity,
                passed=usage < 90,
                current=f"{usage:.1f}%",
                expected="< 90%",
                message=f"CPU 使用率: {usage:.1f}%"
            ))
        except ValueError:
            pass

        return results

    def _check_additional(self) -> List[CheckResult]:
        """额外检测（完整模式）"""
        results = []

        mem_info = self._execute_command("free -m") or ""
        if mem_info:
            lines = mem_info.split('\n')
            if len(lines) > 1:
                mem_line = lines[1]
                parts = mem_line.split()
                if len(parts) >= 4:
                    try:
                        total = int(parts[1])
                        used = int(parts[2])
                        free = int(parts[3])
                        if total > 0:
                            used_percent = (used / total) * 100
                            severity = CheckSeverity.CRITICAL if used_percent > 90 else CheckSeverity.WARNING if used_percent > 70 else CheckSeverity.INFO
                            results.append(CheckResult(
                                check_id="memory_usage",
                                title="内存使用率",
                                category=CheckCategory.SYSTEM,
                                severity=severity,
                                passed=used_percent < 90,
                                current=f"{used_percent:.1f}% (可用: {free}MB)",
                                expected="< 90%",
                                message=f"内存使用: {used}MB / {total}MB"
                            ))
                    except (ValueError, IndexError):
                        pass

        log_errors = self._execute_command("grep -i error /var/log/syslog 2>/dev/null | tail -10") or ""
        has_errors = len(log_errors) > 0
        results.append(CheckResult(
            check_id="system_logs",
            title="系统日志错误",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.WARNING if has_errors else CheckSeverity.INFO,
            passed=not has_errors,
            current="有错误" if has_errors else "无错误",
            expected="无错误",
            message="系统日志中存在错误" if has_errors else "系统日志正常"
        ))

        return results

    def run_checks(self, categories: Optional[List[str]] = None, use_batch: bool = True) -> List[CheckResult]:
        """
        运行特定类别的检测

        Args:
            categories: 检测类别列表
            use_batch: 是否使用批量命令执行（性能优化）

        Returns:
            检测结果列表
        """
        if not self._connected:
            print("请先调用 connect()")
            return []

        if use_batch:
            return self._run_checks_batch(categories)
        else:
            return self._run_checks_single(categories)

    def _run_checks_batch(self, categories: Optional[List[str]]) -> List[CheckResult]:
        """使用批量命令执行进行检测（性能优化）"""
        results = []

        batch_commands = {}

        if not categories or "system" in categories:
            batch_commands.update({
                "uptime": "uptime",
                "uptime_pretty": "uptime -p",
                "load_avg": "cat /proc/loadavg",
                "ps_count": "ps aux | wc -l",
                "top_cpu": "top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'",
            })

        if not categories or "network" in categories:
            batch_commands["ip_addr"] = "ip addr show"

        if not categories or "storage" in categories:
            batch_commands["df_h"] = "df -h"

        if batch_commands:
            results_list = self.execute_batch(list(batch_commands.values()))
            results_map = dict(zip(batch_commands.keys(), [r[1] for r in results_list]))

            if not categories or "system" in categories:
                load_avg = results_map.get("load_avg") or ""
                if load_avg:
                    parts = load_avg.split()
                    if len(parts) >= 3:
                        results.append(CheckResult(
                            check_id="system_load",
                            title="系统负载",
                            category=CheckCategory.SYSTEM,
                            severity=CheckSeverity.INFO,
                            passed=True,
                            current=f"{parts[0]} (1m), {parts[1]} (5m), {parts[2]} (15m)",
                            expected="< 1.0 (理想状态)",
                            message=f"系统负载: {parts[0]}, {parts[1]}, {parts[2]}"
                        ))

                process_count = results_map.get("ps_count") or "0"
                try:
                    count = int(process_count)
                    results.append(CheckResult(
                        check_id="process_count",
                        title="运行进程数",
                        category=CheckCategory.SYSTEM,
                        severity=CheckSeverity.INFO,
                        passed=count < 1000,
                        current=str(count),
                        expected="< 1000",
                        message=f"当前运行 {count} 个进程"
                    ))
                except ValueError:
                    pass

                cpu_usage_str = results_map.get("top_cpu") or "0"
                try:
                    cpu_usage = float(cpu_usage_str)
                    severity = CheckSeverity.CRITICAL if cpu_usage > 90 else CheckSeverity.WARNING if cpu_usage > 70 else CheckSeverity.INFO
                    results.append(CheckResult(
                        check_id="cpu_usage",
                        title="CPU 使用率",
                        category=CheckCategory.SYSTEM,
                        severity=severity,
                        passed=cpu_usage < 90,
                        current=f"{cpu_usage:.1f}%",
                        expected="< 90%",
                        message=f"CPU 使用率: {cpu_usage:.1f}%"
                    ))
                except ValueError:
                    pass

            if not categories or "network" in categories:
                ip_addr = results_map.get("ip_addr") or ""
                if ip_addr:
                    active_interfaces = sum(1 for line in ip_addr.split('\n') if 'inet ' in line)
                    results.append(CheckResult(
                        check_id="network_interfaces",
                        title="网络接口",
                        category=CheckCategory.NETWORK,
                        severity=CheckSeverity.INFO,
                        passed=True,
                        current=f"{active_interfaces} 个活跃接口",
                        expected="至少 1 个活跃接口",
                        message=f"检测到 {active_interfaces} 个活跃网络接口"
                    ))

            if not categories or "storage" in categories:
                df_h = results_map.get("df_h") or ""
                if df_h:
                    lines = df_h.split('\n')[1:]
                    for line in lines:
                        if line:
                            parts = line.split()
                            if len(parts) >= 6:
                                filesystem = parts[0]
                                use_percent = parts[4]
                                available = parts[3]
                                mount_point = parts[5]

                                if use_percent.endswith('%'):
                                    percent = int(use_percent.rstrip('%'))
                                    severity = CheckSeverity.CRITICAL if percent > 90 else CheckSeverity.WARNING if percent > 70 else CheckSeverity.INFO

                                    results.append(CheckResult(
                                        check_id=f"storage_{filesystem.replace('/', '_').replace('.', '_')}",
                                        title=f"磁盘使用 - {mount_point}",
                                        category=CheckCategory.STORAGE,
                                        severity=severity,
                                        passed=percent < 90,
                                        current=f"{use_percent} (可用: {available})",
                                        expected="< 90%",
                                        message=f"{filesystem} 挂载在 {mount_point}，使用 {use_percent}"
                                    ))

        return results

    def _run_checks_single(self, categories: Optional[List[str]]) -> List[CheckResult]:
        """使用单独命令执行进行检测（传统方式）"""
        results = []

        if not categories or "system" in categories:
            results.extend(self._check_system_info())
            results.extend(self._check_processes())

        if not categories or "network" in categories:
            results.extend(self._check_network())

        if not categories or "storage" in categories:
            results.extend(self._check_storage())

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

        start_time = time.time()
        self._execute_command("python3 -c 'sum(i*i for i in range(1000000))'")
        end_time = time.time()

        return {
            "cpu_benchmark": {
                "execution_time": end_time - start_time,
                "model": model,
                "timestamp": time.time()
            }
        }

    def quick_diagnosis(self, use_retry: bool = True, use_batch: bool = True) -> Dict[str, Any]:
        """
        快速诊断（连接 + 设备信息 + 诊断）

        Args:
            use_retry: 是否使用重试机制
            use_batch: 是否使用批量命令执行（性能优化）

        Returns:
            诊断结果字典
        """
        if not self.connect(use_retry=use_retry):
            return {"error": "连接失败"}

        device_info = self.get_device_info(use_batch=use_batch)
        results = self.run_diagnosis(full_mode=False, use_batch=use_batch)

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

    def close(self):
        """关闭连接"""
        self.disconnect()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


def detect_remote_target(target: str, retry_config: Optional[RetryConfig] = None) -> RemoteSSHDetector:
    """
    自动检测目标类型并返回对应的 SSH 检测器

    Args:
        target: 目标地址
        retry_config: 重试配置（可选）

    Returns:
        对应的检测器实例
    """
    if "@" in target:
        user_host = target.split("@")
        username = user_host[0]
        host_port = user_host[1]

        if ":" in host_port:
            host, port = host_port.split(":")
            return RemoteSSHDetector(host, port=int(port), username=username, retry_config=retry_config)
        else:
            return RemoteSSHDetector(host_port, username=username, retry_config=retry_config)
    else:
        if ":" in target:
            host, port = target.split(":")
            return RemoteSSHDetector(host, port=int(port), retry_config=retry_config)
        else:
            return RemoteSSHDetector(target, retry_config=retry_config)
