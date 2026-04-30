# -*- coding: utf-8 -*-
"""
schemas/ - Pydantic models for configuration validation

Validates checks.yaml and health_weights.yaml at load time.
Provides type hints, auto-completion, and early error detection.
"""

from .check_config import (
    CheckConfig,
    SystemCheckConfig,
    MemoryConfig,
    CPUConfig,
    DiskConfig,
    StorageCheckConfig,
    SMARTAttributeConfig,
    NetworkCheckConfig,
    DNSConfig,
    SecurityCheckConfig,
    LoginFailureConfig,
    SSHConfig,
    SSLConfig,
    NASCheckConfig,
    UPSConfig,
    AICheckConfig,
    GPUConfig,
    ScoringConfig,
    PenaltyConfig,
    TimeoutConfig,
    ReportConfig,
)
from .health_weights import (
    HealthWeightsConfig,
    WeightEntry,
    ScoreLevel,
    DefaultWeightConfig,
)

__all__ = [
    "CheckConfig",
    "SystemCheckConfig",
    "MemoryConfig",
    "CPUConfig",
    "DiskConfig",
    "StorageCheckConfig",
    "SMARTAttributeConfig",
    "NetworkCheckConfig",
    "DNSConfig",
    "SecurityCheckConfig",
    "LoginFailureConfig",
    "SSHConfig",
    "SSLConfig",
    "NASCheckConfig",
    "UPSConfig",
    "AICheckConfig",
    "GPUConfig",
    "ScoringConfig",
    "PenaltyConfig",
    "TimeoutConfig",
    "ReportConfig",
    "HealthWeightsConfig",
    "WeightEntry",
    "ScoreLevel",
    "DefaultWeightConfig",
]
