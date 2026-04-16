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

# Network checks
from .network.internet_access import InternetAccessCheck
from .network.dns_resolve import DNSResolveCheck
from .network.nas_backend import NASBackendCheck
from .network.port_conflict import PortConflictCheck
from .network.nic_speed import NICSpeedCheck
from .network.dns_coverage import DNSCoverageCheck

# Storage checks
from .storage.storage_disk import DiskSpaceCheck
from .storage.write_speed import WriteSpeedCheck
from .storage.path_exists import PathExistsCheck
from .storage.smart_health import SMARTHealthCheck
from .storage.hdd_temp import HDDTempCheck
from .storage.raid_status import RAIDStatusCheck
from .storage.docker_images import DockerImagesCheck
from .storage.storage_trend import StorageTrendCheck

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

# Security checks
from .security.firewall import FirewallCheck
from .security.selinux import SELinuxCheck
from .security.ssh_root import SSHRootCheck
from .security.login_failures import LoginFailuresCheck
from .security.ssl_cert import SSLCertCheck

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


def run_all_checks(skip_categories=None):
    """Run all registered checks and return summary"""
    skip_categories = skip_categories or []

    results = []
    for check_id, check_info in list_checks().items():
        check = get_check(check_id)
        if check.category in skip_categories:
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


def run_mock_checks(profile: str = "healthy") -> CheckSummary:
    """Run all checks with mock data (no real system access required).

    Profiles:
        healthy  — all checks pass, ideal device
        degraded — some warnings, needs attention
        critical — multiple failures, immediate action needed
        mixed    — random distribution for demo
    """
    from data.mock_results import get_mock_result, PROFILES, PROFILE_DESCRIPTIONS

    if profile not in PROFILES:
        profile = "healthy"

    results = []
    for check_id, check_info in list_checks().items():
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
        total_score = sum(sev_score.get(r.severity, 0) for r in results)
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
