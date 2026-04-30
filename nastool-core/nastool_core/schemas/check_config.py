# -*- coding: utf-8 -*-
"""
schemas/check_config.py - Pydantic models for checks.yaml validation

Validates the entire checks.yaml structure at load time.
If any field is wrong type/missing/invalid, SystemExit(1) with clear error message.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Sub-configs ────────────────────────────────────────────────────

class MemoryConfig(BaseModel):
    warning_percent: float = Field(default=85.0, ge=0, le=100, description="内存使用率警告阈值(%)")
    critical_percent: float = Field(default=95.0, ge=0, le=100, description="内存使用率严重阈值(%)")


class CPUConfig(BaseModel):
    warning_temp: float = Field(default=70.0, ge=0, le=120, description="CPU温度警告阈值(°C)")
    critical_temp: float = Field(default=85.0, ge=0, le=120, description="CPU温度严重阈值(°C)")
    load_warning: float = Field(default=80.0, ge=0, le=100, description="CPU负载警告阈值(%)")


class DiskConfig(BaseModel):
    warning_percent: float = Field(default=85.0, ge=0, le=100)
    critical_percent: float = Field(default=95.0, ge=0, le=100)
    warning_temp: float = Field(default=45.0, ge=0, le=100)
    critical_temp: float = Field(default=55.0, ge=0, le=100)


class SMARTAttributeConfig(BaseModel):
    id: int = Field(ge=0, description="SMART attribute ID")
    name: str = Field(min_length=1, description="Attribute name")
    threshold: int = Field(default=0, ge=0, description="Failure threshold")
    critical: bool = Field(default=False, description="Whether failure is critical")


class StorageCheckConfig(BaseModel):
    disk: DiskConfig = Field(default_factory=DiskConfig)
    smart_attributes: List[SMARTAttributeConfig] = Field(default_factory=list)
    raid_check: bool = Field(default=True)
    zfs_check: bool = Field(default=True)
    io_wait_warning: float = Field(default=20.0, ge=0, le=100)
    io_wait_critical: float = Field(default=50.0, ge=0, le=100)


class DNSConfig(BaseModel):
    timeout: float = Field(default=5.0, ge=0.1, description="DNS查询超时(秒)")
    servers: List[str] = Field(default=["8.8.8.8", "1.1.1.1"], description="测试DNS服务器")


class NetworkCheckConfig(BaseModel):
    dns: DNSConfig = Field(default_factory=DNSConfig)
    ping_timeout: float = Field(default=5.0, ge=0.1)
    speed_test: bool = Field(default=False)
    bandwidth_warning_mbps: float = Field(default=100, ge=0)


class LoginFailureConfig(BaseModel):
    max_attempts: int = Field(default=10, ge=1)
    window_minutes: int = Field(default=10, ge=1)
    ban_minutes: int = Field(default=30, ge=1)


class SSHConfig(BaseModel):
    max_auth_tries: int = Field(default=4, ge=1)
    permit_root: str = Field(default="no")
    password_auth: bool = Field(default=False)


class SSLConfig(BaseModel):
    warning_days: int = Field(default=30, ge=1)
    critical_days: int = Field(default=7, ge=1)
    check_paths: List[str] = Field(default_factory=list)


class SecurityCheckConfig(BaseModel):
    login_failures: LoginFailureConfig = Field(default_factory=LoginFailureConfig)
    ssh: SSHConfig = Field(default_factory=SSHConfig)
    ssl: SSLConfig = Field(default_factory=SSLConfig)
    firewall_check: bool = Field(default=True)
    fail2ban_check: bool = Field(default=True)


class UPSConfig(BaseModel):
    check_nut: bool = Field(default=True)
    check_apcupsd: bool = Field(default=True)
    battery_warning_percent: float = Field(default=50.0, ge=0, le=100)
    battery_critical_percent: float = Field(default=20.0, ge=0, le=100)


class NASCheckConfig(BaseModel):
    ups: UPSConfig = Field(default_factory=UPSConfig)
    dsm_version_check: bool = Field(default=True)
    user_weak_password_check: bool = Field(default=True)
    shared_perms_check: bool = Field(default=True)


class GPUConfig(BaseModel):
    memory_warning_percent: float = Field(default=90.0, ge=0, le=100)
    memory_critical_percent: float = Field(default=95.0, ge=0, le=100)
    utilization_warning_percent: float = Field(default=95.0, ge=0, le=100)
    temp_warning: float = Field(default=80.0, ge=0, le=120)
    temp_critical: float = Field(default=90.0, ge=0, le=120)


class AICheckConfig(BaseModel):
    gpu: GPUConfig = Field(default_factory=GPUConfig)
    check_tensorflow: bool = Field(default=True)
    check_pytorch: bool = Field(default=True)
    check_onnx: bool = Field(default=True)
    check_tensorrt: bool = Field(default=True)
    check_cudnn: bool = Field(default=True)
    check_openvino: bool = Field(default=False)
    check_paddlepaddle: bool = Field(default=False)


class PenaltyConfig(BaseModel):
    warning_penalty: float = Field(default=5.0, ge=0, le=100)
    critical_penalty: float = Field(default=15.0, ge=0, le=100)
    info_penalty: float = Field(default=0.0, ge=0, le=100)


class ScoringConfig(BaseModel):
    enabled: bool = Field(default=True)
    base_score: float = Field(default=100.0, ge=0, le=100)
    penalties: PenaltyConfig = Field(default_factory=PenaltyConfig)
    weight_by_severity: bool = Field(default=True)
    min_score: float = Field(default=0.0, ge=0, le=100)
    max_score: float = Field(default=100.0, ge=0, le=100)


class TimeoutConfig(BaseModel):
    default: float = Field(default=30.0, ge=1, description="默认超时(秒)")
    network: float = Field(default=10.0, ge=1)
    storage: float = Field(default=60.0, ge=1)
    ai: float = Field(default=30.0, ge=1)


class ReportConfig(BaseModel):
    format: str = Field(default="terminal")
    output_dir: str = Field(default="./reports")
    include_passed: bool = Field(default=True)
    include_info: bool = Field(default=True)

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        allowed = {"terminal", "json", "html", "markdown", "pdf", "friendly"}
        if v.lower() not in allowed:
            raise ValueError(f"format must be one of {allowed}, got '{v}'")
        return v.lower()


# ── Top-level config ──────────────────────────────────────────────

class SystemCheckConfig(BaseModel):
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    cpu: CPUConfig = Field(default_factory=CPUConfig)
    uptime_warning_hours: float = Field(default=720.0, ge=0)
    docker_check: bool = Field(default=True)


class CheckConfig(BaseModel):
    """Root configuration model for checks.yaml"""
    version: str = Field(default="1.0")
    system: SystemCheckConfig = Field(default_factory=SystemCheckConfig)
    storage: StorageCheckConfig = Field(default_factory=StorageCheckConfig)
    network: NetworkCheckConfig = Field(default_factory=NetworkCheckConfig)
    security: SecurityCheckConfig = Field(default_factory=SecurityCheckConfig)
    nas: NASCheckConfig = Field(default_factory=NASCheckConfig)
    ai: AICheckConfig = Field(default_factory=AICheckConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
