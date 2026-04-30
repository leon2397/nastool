# nastool v2.0 - Checks module
from .base import Check, CheckResult, CheckSeverity, CheckCategory, CheckSummary
from .registry import register_check, get_check, list_checks, run_check

# Import all check classes for auto-registration
# System checks (from module __init__ for backward compat aliases)
# System checks (from sub-package __init__ for backward compat aliases)
from .system import (
    PythonVersionCheck, PipInstalledCheck, SystemLibsCheck,
    MemoryCheck, CronJobsCheck, SystemLogsCheck,
    ProcessCountCheck, PackageUpdatesCheck, SystemDiskSpaceCheck,
    CPUTempCheck, UptimeCheck, DockerContainersCheck,
)

# Network checks (from sub-package __init__ for backward compat aliases)
from .network import (
    InternetAccessCheck, DNSCacheCheck, DNSResolveCheck,
    DNSCoverageCheck, MTUCheck, ProxyCheck, WiFiCheck,
    BandwidthCheck, LatencyCheck, RouteCheck, PortConflictCheck,
    NASBackendCheck, NICSpeedCheck, NetworkLatencyCheck,
)

# Storage checks (from sub-package __init__)
from .storage import (
    DiskSpaceCheck, InodeCheck, IOWaitCheck,
    PathExistsCheck, WriteSpeedCheck, ZFSHealthCheck,
    SMARTHealthCheck, HDDTempCheck, RAIDStatusCheck,
    DockerImagesCheck, StorageTrendCheck,
)

# AI checks
from .ai.gpu_detected import GPUDetectedCheck
from .ai.version_checker import nvidia_driver_version as VersionCheckerCheck
# New AI Framework Checks
from .ai.tensorflow_checker import TensorFlowVersionCheck
from .ai.keras_checker import KerasVersionCheck
from .ai.cudnn_checker import CUDNNVersionCheck
from .ai.openvino_checker import OpenVINOVersionCheck
from .ai.paddlepaddle_checker import PaddlePaddleCheck
from .ai.triton_checker import TritonServerCheck
from .ai.mlflow_checker import MLflowCheck
from .ai.gpu_memory_checker import GPUMemoryCheck
from .ai.gpu_utilization_checker import GPUUtilizationCheck
from .ai.nvidia_container_checker import NVIDIAContainerToolkitCheck
from .ai.onnx_model_checker import ONNXModelCheck
from .ai.onednn_checker import OneDNNVersionCheck
from .ai.torchserve_checker import TorchServeCheck
from .ai.tensorflow_serving_checker import TensorFlowServingCheck
from .ai.kubeflow_checker import KubeflowCheck
from .ai.model_format_checker import ModelFormatCheck

# Security checks (from sub-package __init__)
from .security import (
    OpenSSLVersionCheck, FirewallCheck, SSHRootCheck,
    SSHConfigCheck, Fail2banCheck, ClamAVCheck,
    PortScanCheck, SELinuxCheck,
    SSLCertCheck, SSLCertCheckDays, LoginFailuresCheck,
)

# NAS system checks (v4.0.2)
from .nas.dsm_version import DSMVersionCheck
from .nas.user_stats import UserStatsCheck
from .nas.shared_perms import SharedPermsCheck
from .nas.ups_status import UPSStatusCheck
from .nas.log_disk import LogDiskCheck
from .nas.cron_conflicts import CronConflictsCheck

# USB checks (v5.0.3)
from .usb.usb_devices import USBDevicesCheck
from .usb.usb_storage import USBStorageCheck
from .usb.usb_permissions import USBPermissionsCheck
from .usb.usb_power import USBPowerCheck


# Benchmark checks that are skipped in quick mode
BENCHMARK_CHECKS = {
    'write_speed',    # Disk write speed test
    'nic_speed',      # Network interface speed test
    'bandwidth',      # Network bandwidth test
    'latency',        # Network latency benchmark
}


def run_all_checks(skip_categories=None, full_mode=False):
    """Run all registered checks and return summary
    
    Args:
        skip_categories: List of category names to skip
        full_mode: If True, run all checks including benchmarks.
                  If False (quick mode), skip benchmark checks.
    """
    skip_categories = skip_categories or []

    results = []
    for check_id, check_info in list_checks().items():
        check = get_check(check_id)
        if check.category in skip_categories:
            continue
        
        # In quick mode (full_mode=False), skip benchmark checks
        if not full_mode and check_id in BENCHMARK_CHECKS:
            continue
            
        result = get_check(check_id)().run()
        results.append(result)

    return CheckSummary(
        total=len(results),
        passed=sum(1 for r in results if r.passed),
        warnings=sum(1 for r in results if not r.passed and r.severity == CheckSeverity.WARNING),
        critical=sum(1 for r in results if not r.passed and r.severity == CheckSeverity.CRITICAL),
        results=results,
    )


def list_available_checks():
    """List all available checks with their info"""
    return list_checks()


def run_mock_checks(profile: str = "healthy", full_mode: bool = False) -> CheckSummary:
    """Run all checks with mock data (no real system access required).

    Profiles:
        healthy  -- all checks pass, ideal device
        degraded -- some warnings, needs attention
        critical -- multiple failures, immediate action needed
        mixed    -- random distribution for demo
    
    Args:
        profile: Mock data profile name
        full_mode: If True, include benchmark checks
    """
    from nastool_core.data import get_mock_result, PROFILES, PROFILE_DESCRIPTIONS

    if profile not in PROFILES:
        profile = "healthy"

    results = []
    for check_id, check_info in list_checks().items():
        # In quick mode, skip benchmark checks
        if not full_mode and check_id in BENCHMARK_CHECKS:
            continue
            
        check_class = get_check(check_id)
        result = get_mock_result(check_id, profile)
        result.category = check_class.category  # Use real category
        results.append(result)

    passed = sum(1 for r in results if r.passed)
    warnings = sum(1 for r in results if not r.passed and r.severity == CheckSeverity.WARNING)
    critical = sum(1 for r in results if not r.passed and r.severity == CheckSeverity.CRITICAL)
    info = sum(1 for r in results if r.severity == CheckSeverity.INFO)
    total = len(results)

    # Weighted score: passed=100, warning=70, critical=0, info=100
    score = 0
    if total > 0:
        sev_score = {CheckSeverity.PASSED: 100, CheckSeverity.WARNING: 70, CheckSeverity.CRITICAL: 0, CheckSeverity.INFO: 100}
        # Handle both CheckSeverity enum and string values
        total_score = 0
        for r in results:
            severity = r.severity
            # Convert string severity to CheckSeverity enum if needed
            if isinstance(severity, str):
                try:
                    severity = CheckSeverity(severity)
                except ValueError:
                    # If string is not a valid CheckSeverity, use 0
                    severity = None
            total_score += sev_score.get(severity, 0)
        score = int(total_score / total)

    summary = CheckSummary(
        total=total,
        passed=passed,
        warnings=warnings,
        critical=critical,
        info=info,
        score=score,
        results=results,
    )
    return summary


__all__ = [
    "Check",
    "CheckResult",
    "CheckSeverity",
    "CheckCategory",
    "CheckSummary",
    "register_check",
    "get_check",
    "list_checks",
    "run_check",
    "run_all_checks",
    "run_mock_checks",
    "list_available_checks",
    # System
    "PythonVersionCheck",
    "PipInstalledCheck",
    "SystemLibsCheck",
    "MemoryCheck",
    "SystemDiskSpaceCheck",
    "CPUTempCheck",
    "UptimeCheck",
    "DockerContainersCheck",
    # Network
    "InternetAccessCheck",
    "DNSResolveCheck",
    "NASBackendCheck",
    "PortConflictCheck",
    "NICSpeedCheck",
    "DNSCoverageCheck",
    # Storage
    "DiskSpaceCheck",
    "WriteSpeedCheck",
    "PathExistsCheck",
    "SMARTHealthCheck",
    "HDDTempCheck",
    "RAIDStatusCheck",
    "DockerImagesCheck",
    "StorageTrendCheck",
    # AI
    "GPUDetectedCheck",
    "VersionCheckerCheck",
    # New AI Framework Checks
    "TensorFlowVersionCheck",
    "KerasVersionCheck",
    "CUDNNVersionCheck",
    "OpenVINOVersionCheck",
    "PaddlePaddleCheck",
    "TritonServerCheck",
    "MLflowCheck",
    "GPUMemoryCheck",
    "GPUUtilizationCheck",
    "NVIDIAContainerToolkitCheck",
    "ONNXModelCheck",
    "OneDNNVersionCheck",
    "TorchServeCheck",
    "TensorFlowServingCheck",
    "KubeflowCheck",
    "ModelFormatCheck",
    # Security
    "FirewallCheck",
    "SELinuxCheck",
    "SSHRootCheck",
    "LoginFailuresCheck",
    "SSLCertCheck",
    # NAS
    "DSMVersionCheck",
    "UserStatsCheck",
    "SharedPermsCheck",
    "UPSStatusCheck",
    "LogDiskCheck",
    "CronConflictsCheck",
]
