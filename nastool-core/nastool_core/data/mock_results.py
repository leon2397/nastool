"""
data/mock_profiles.py - Mock device profiles for v5.0.1

All 82 check IDs organized by category.
Each check returns a realistic mock result based on the profile.

Usage:
    python arm_diagnose.py --mock healthy
    python arm_diagnose.py --mock degraded
    python arm_diagnose.py --mock critical
    python arm_diagnose.py --mock mixed
"""

from nastool_core.checks.base import CheckResult, CheckCategory, CheckSeverity

# ══════════════════════════════════════════════════════
# AI (24 checks)
# ══════════════════════════════════════════════════════
AI_MOCK = {
    # AI Accelerators
    "nvidia_driver_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="535.54.03", expected="535+",
        message="NVIDIA driver 535.54.03 installed",
    ),
    "cuda_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="12.6", expected="11.8+",
        message="CUDA 12.6 available",
    ),
    "tensorrt_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="10.3.0.26", expected="8.6+",
        message="TensorRT 10.3.0.26 installed",
    ),
    "jetpack_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="6.1", expected="5.0+",
        message="JetPack 6.1 GA installed",
    ),
    "rknn_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="2.5.0", expected="2.0+",
        message="RKNN Toolkit 2.5.0 installed",
    ),
    "pytorch_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="2.4.0+cu124", expected="2.0+",
        message="PyTorch 2.4.0 with CUDA 12.4 support",
    ),
    "onnxruntime_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="1.19.0", expected="1.15+",
        message="ONNXRuntime 1.19.0 available",
    ),
    # AI Frameworks
    "gpu_detected": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="1 GPU (NVIDIA)", expected="GPU detected",
        message="NVIDIA GPU detected: Orin",
    ),
    "tensorflow_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="2.18.0", expected="2.15+",
        message="TensorFlow 2.18.0 (GPU: 1 device)",
    ),
    "keras_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="3.8.0", expected="3.0+",
        message="Keras 3.8.0 (backend: tensorflow)",
    ),
    "paddlepaddle_version": dict(
        severity=CheckSeverity.WARNING, passed=False,
        current="2.6.1", expected="3.0+",
        message="PaddlePaddle 2.6.1 installed, consider upgrading to 3.0",
        fix_available=True,
    ),
    "openvino_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="2024.5.0", expected="2024+",
        message="OpenVINO 2024.5.0 (devices: CPU, GPU.0)",
    ),
    # Acceleration Libraries
    "cudnn_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="9.5.1", expected="8.9+",
        message="cuDNN 9.5.1 (enabled: True)",
    ),
    "onednn_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="available via PyTorch", expected="installed",
        message="OneDNN (MKL) via PyTorch available",
    ),
    # Inference Servers
    "triton_server": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="running", expected="running",
        message="Triton Server running (models: 3)",
    ),
    "torchserve": dict(
        severity=CheckSeverity.WARNING, passed=False,
        current="installed", expected="running",
        message="TorchServe installed but not running",
        fix_available=True,
    ),
    "tensorflow_serving": dict(
        severity=CheckSeverity.INFO, passed=True,
        current="not installed", expected="optional",
        message="TensorFlow Serving not installed (optional)",
    ),
    # MLOps
    "mlflow": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="v2.16.1", expected="installed",
        message="MLflow 2.16.1 running (experiments: 12)",
    ),
    "kubeflow": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="12/15 pods running", expected="deployed",
        message="Kubeflow running (pods: 12/15)",
    ),
    # Models
    "onnx_model": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="8 models", expected="models available",
        message="Found 8 ONNX models: resnet50-v2.onnx, yolov8n.onnx, ...",
    ),
    "model_format": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="15 models", expected="models available",
        message="PyTorch (.pt): 8; ONNX (.onnx): 8; Keras (.h5): 2",
    ),
    # Hardware Monitoring
    "gpu_memory": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="6144MB / 32768MB (18.7%, 26724MB free)", expected="<90% usage",
        message="GPU0: 6144MB / 32768MB (18.7%, 26724MB free)",
    ),
    "gpu_utilization": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="GPU0: GPU 35%, Memory 18%", expected="<90%",
        message="GPU0: GPU 35%, Memory 18%",
    ),
    "nvidia_container_toolkit": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="v1.16.2", expected="installed",
        message="nvidia-container-toolkit 1.16.2 installed",
    ),
}


# ══════════════════════════════════════════════════════
# NAS Storage (13 checks)
# ══════════════════════════════════════════════════════
NAS_MOCK = {
    "nas_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="DSM 7.2.2-72806", expected="7.2+",
        message="Synology DSM 7.2.2-72806 Update 2",
    ),
    "nas_users": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="5 users", expected="<50",
        message="5 user accounts (admin, backup, media, guest, worker)",
    ),
    "shared_perms": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="6 shared folders", expected="configured",
        message="6 shared folders with proper permissions",
    ),
    "ups_status": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="connected, 85% battery", expected="connected",
        message="UPS connected: APC BR1500G, 85% battery, 45min runtime",
    ),
    "log_disk": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="2.1GB used (21%)", expected="<80%",
        message="Log disk: 2.1GB / 10GB (21%)",
    ),
    "cron_conflicts": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="no conflicts", expected="no conflicts",
        message="No scheduled task conflicts detected",
    ),
    # Service checks
    "nfs_service": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="running", expected="running",
        message="NFS service running (8 nfsd processes)",
    ),
    "smb_service": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="running", expected="running",
        message="SMB service running (12 smbd processes)",
    ),
    "ftp_service": dict(
        severity=CheckSeverity.WARNING, passed=False,
        current="not running", expected="running or disabled",
        message="FTP service not running",
        fix_available=True,
    ),
    "sftp_service": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="running", expected="running",
        message="SSH/SFTP service running (3 sshd processes)",
    ),
    "afp_service": dict(
        severity=CheckSeverity.INFO, passed=True,
        current="not running", expected="not used",
        message="AFP service not running (Mac users can use SMB/SFTP)",
    ),
    "webdav_service": dict(
        severity=CheckSeverity.WARNING, passed=False,
        current="not configured", expected="configured",
        message="WebDAV service not configured",
        fix_available=True,
    ),
    "snmp_service": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="running", expected="running",
        message="SNMP service running",
    ),
    # Media & Backup
    "backup_status": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="3 backup tasks", expected="configured",
        message="/backup: 245 files; 3 backup tasks configured",
    ),
    "media_indexer": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="running", expected="running",
        message="Media indexer service: jellyfin, sonarr, radarr",
    ),
    "nas_temperature": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="sda: 38C, hdd: 41C", expected="<50C",
        message="Temperature normal: sda=38C, hdd=41C",
    ),
}


# ══════════════════════════════════════════════════════
# Network (12 checks)
# ══════════════════════════════════════════════════════
NETWORK_MOCK = {
    "internet_access": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="connected", expected="connected",
        message="Internet connection: connected",
    ),
    "dns_resolve": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="working", expected="working",
        message="DNS resolution working: google.com -> 142.250.x.x",
    ),
    "nas_backend": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="120.77.249.3:8000", expected="reachable",
        message="NAS backend reachable: 120.77.249.3:8000",
    ),
    "port_conflict": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="2 available", expected="<80% used",
        message="2 available ports in 8000-9000 range",
    ),
    "nic_speed": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="1000Mbps full duplex", expected="100Mbps+",
        message="eth0: 1000Mbps full duplex",
    ),
    "dns_coverage": dict(
        severity=CheckSeverity.WARNING, passed=False,
        current="2 of 5 passed", expected="all passed",
        message="DNS 2/5: google.com and cloudflare DNS failed",
        fix_available=True,
    ),
    # New network checks
    "bandwidth": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="eth0, eth1, eth2", expected="1Gbps+",
        message="Active NICs: eth0, eth1, eth2",
    ),
    "network_latency": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="32ms", expected="<200ms",
        message="Network latency normal, average 32ms, best AliDNS 28ms",
    ),
    "mtu_size": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="eth0: 1500", expected="1400+",
        message="eth0: MTU 1500, eth1: MTU 9000 (Jumbo Frame)",
    ),
    "proxy_config": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="none", expected="none or configured",
        message="No proxy configured",
    ),
    "wifi_status": dict(
        severity=CheckSeverity.INFO, passed=True,
        current="not connected", expected="connected or not used",
        message="WiFi not connected or not available",
    ),
    "default_route": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="configured", expected="configured",
        message="Default route configured via eth0",
    ),
    "dns_cache": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="running", expected="running",
        message="DNS cache service: dnsmasq",
    ),
}


# ══════════════════════════════════════════════════════
# Security (11 checks)
# ══════════════════════════════════════════════════════
SECURITY_MOCK = {
    "firewall": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="enabled (iptables)", expected="enabled",
        message="Firewall enabled (iptables, 12 rules active)",
    ),
    "selinux": dict(
        severity=CheckSeverity.INFO, passed=True,
        current="Not installed", expected="disabled or not installed",
        message="SELinux not installed (not applicable)",
    ),
    "ssh_root": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="disabled", expected="disabled",
        message="SSH root login disabled",
    ),
    "login_failures": dict(
        severity=CheckSeverity.WARNING, passed=False,
        current="3 failed logins (root, 192.168.1.50)", expected="<3",
        message="3 failed login attempts in last hour (root from 192.168.1.50)",
        fix_available=True,
    ),
    "ssl_cert": dict(
        severity=CheckSeverity.WARNING, passed=False,
        current="18 days", expected="30+ days",
        message="SSL certificate expires in 18 days (critical!)",
        fix_available=True,
    ),
    # New security checks
    "openssl_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="3.0.15", expected="1.1.1+",
        message="OpenSSL 3.0.15",
    ),
    "ssh_config": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="secure", expected="secure",
        message="SSH configuration secure",
    ),
    "fail2ban": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="running", expected="running",
        message="Fail2ban running",
    ),
    "clamav": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="installed", expected="installed",
        message="ClamAV: ClamAV 1.4.0/24872",
    ),
    "suspicious_ports": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="clean", expected="clean",
        message="No suspicious listening ports detected",
    ),
    "ssl_cert_days": dict(
        severity=CheckSeverity.WARNING, passed=False,
        current="18 days", expected="30+ days",
        message="Primary SSL cert expires in 18 days",
        fix_available=True,
    ),
}


# ══════════════════════════════════════════════════════
# Storage (11 checks)
# ══════════════════════════════════════════════════════
STORAGE_MOCK = {
    "disk_space": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="1.2TB / 8TB (15%)", expected="10GB+ free",
        message="Primary volume: 1.2TB / 8TB used (15%), 6.8TB free",
    ),
    "write_speed": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="908.9 MB/s", expected="100MB/s+",
        message="Write speed 908.9 MB/s (NVMe SSD)",
    ),
    "smart_health": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="PASSED", expected="PASSED",
        message="All SMART checks PASSED (8 drives)",
    ),
    "hdd_temperature": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="38C", expected="<50C",
        message="HDD temperature 38C (normal range)",
    ),
    "raid_status": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="healthy", expected="healthy",
        message="RAID 5 (4x8TB): all drives online, healthy",
    ),
    "docker_images": dict(
        severity=CheckSeverity.WARNING, passed=False,
        current="15.3GB", expected="<10GB",
        message="Docker images占用 15.3GB, 建议清理",
        fix_available=True,
    ),
    "path_exists": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="/data:/backup:/media configured", expected="paths configured",
        message="/data:/backup:/media configured",
    ),
    "storage_trend": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="stable", expected="stable",
        message="Storage growth trend: stable, +0.5GB/week",
    ),
    # New storage checks
    "io_wait": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="2.1%", expected="<20%",
        message="IO Wait 2.1% normal",
    ),
    "zfs_pool": dict(
        severity=CheckSeverity.INFO, passed=True,
        current="not ZFS", expected="ZFS healthy",
        message="Not using ZFS storage (ext4)",
    ),
    "inode_usage": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="/: 12% inode", expected="<80%",
        message="Inode usage normal: /: 12%",
    ),
}


# ══════════════════════════════════════════════════════
# System (11 checks)
# ══════════════════════════════════════════════════════
SYSTEM_MOCK = {
    "python_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="3.12", expected="3.8+",
        message="Python 3.12 meets recommended version",
    ),
    "pip_installed": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="installed", expected="installed",
        message="pip installed: pip 24.3 from /usr/lib/python3.12",
    ),
    "memory_check": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="2.1GB / 32GB (6.6%)", expected="<95%",
        message="Memory: 2.1GB / 32GB used (6.6%), 29.9GB available",
    ),
    "disk_space": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="1.2TB / 8TB (15%)", expected="10GB+ free",
        message="Disk space: 6.8TB free",
    ),
    "system_libs": dict(
        severity=CheckSeverity.WARNING, passed=False,
        current="Missing: ffi, zlib", expected="all installed",
        message="System libraries missing: ffi, zlib",
        fix_available=True,
    ),
    "uptime": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="up 45 days", expected="<365 days",
        message="System uptime: 45 days",
    ),
    "docker_service": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="running", expected="running",
        message="Docker daemon running",
    ),
    "cpu_temperature": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="58C", expected="<80C",
        message="CPU temperature: 58C (normal)",
    ),
    # New system checks
    "kernel_version": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="5.15.0-107-generic", expected="latest",
        message="Kernel 5.15.0-107-generic (latest security patches applied)",
    ),
    "cron_jobs": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="8 jobs", expected="<30",
        message="Scheduled tasks 8, normal",
    ),
    "system_logs": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="clean", expected="clean",
        message="Last 200 lines of logs clean, no critical errors",
    ),
    "process_count": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="127 processes", expected="<300",
        message="Process count 127, normal",
    ),
    "package_updates": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="up to date", expected="up to date",
        message="System up to date",
    ),
    "docker_containers": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="12 containers (8 running, 4 stopped)", expected="containers healthy",
        message="Docker: 8/12 containers running",
    ),
    "system_disk": dict(
        severity=CheckSeverity.PASSED, passed=True,
        current="NVMe 500GB (250GB used, 50%)", expected="<95%",
        message="System disk: NVMe 500GB, 50% used",
    ),
}


# ══════════════════════════════════════════════════════
# Profile definitions -- each maps check_id -> result
# ══════════════════════════════════════════════════════

# Healthy: everything passes, score should be ~95-100
_HEALTHY = {}
for d in [AI_MOCK, NAS_MOCK, NETWORK_MOCK, SECURITY_MOCK, STORAGE_MOCK, SYSTEM_MOCK]:
    for k, v in d.items():
        if k not in _HEALTHY:
            _HEALTHY[k] = v


# Degraded: some warnings, score ~70-85
_DEGRADED = {}
for k, v in _HEALTHY.items():
    # Flip some PASSED -> WARNING/INFO
    import hashlib
    h = int(hashlib.md5(k.encode()).hexdigest()[:4], 16)
    if h % 7 == 0:  # ~14% of checks get degraded
        _DEGRADED[k] = dict(v)
        _DEGRADED[k]["severity"] = CheckSeverity.WARNING
        _DEGRADED[k]["passed"] = False
        _DEGRADED[k]["fix_available"] = True
    else:
        _DEGRADED[k] = v


# Critical: serious issues, score ~40-60
_CRITICAL = {}
for k, v in _HEALTHY.items():
    import hashlib
    h = int(hashlib.md5(k.encode()).hexdigest()[:4], 16)
    if h % 4 == 0:  # ~25% get critical
        _CRITICAL[k] = dict(v)
        _CRITICAL[k]["severity"] = CheckSeverity.CRITICAL
        _CRITICAL[k]["passed"] = False
        _CRITICAL[k]["fix_available"] = True
        _CRITICAL[k]["message"] = v.get("message", "").replace(
            "PASSED", "CRITICAL ISSUE"
        ).replace("installed", "CRITICAL: not installed").replace(
            "running", "CRITICAL: not running"
        )
    else:
        _CRITICAL[k] = v


# Mixed: random distribution across all states
_MIXED = {}
for k, v in _HEALTHY.items():
    import hashlib
    h = int(hashlib.md5(k.encode()).hexdigest()[:6], 16)
    states = [
        CheckSeverity.PASSED,
        CheckSeverity.WARNING,
        CheckSeverity.CRITICAL,
        CheckSeverity.INFO,
    ]
    _MIXED[k] = dict(v)
    state = states[h % len(states)]
    _MIXED[k]["severity"] = state
    _MIXED[k]["passed"] = (state == CheckSeverity.PASSED) or (state == CheckSeverity.INFO)


# ══════════════════════════════════════════════════════
# Public profile dict
# ══════════════════════════════════════════════════════

PROFILES = {
    "healthy": _HEALTHY,
    "degraded": _DEGRADED,
    "critical": _CRITICAL,
    "mixed": _MIXED,
}

PROFILE_DESCRIPTIONS = {
    "healthy": "Healthy Jetson AGX Orin -- all checks pass, AI pipeline ready",
    "degraded": "Degraded Synology NAS -- some warnings, needs attention",
    "critical": "Critical Raspberry Pi -- multiple failures, immediate action needed",
    "mixed": "Mixed scenario -- random healthy/warning/critical states for demo",
}


def _find_category(check_id: str) -> "CheckCategory":
    """Infer category from which MOCK dict contains this check_id."""
    from nastool_core.checks.base import CheckCategory
    for mock_dict in [AI_MOCK, NAS_MOCK, NETWORK_MOCK, SECURITY_MOCK, STORAGE_MOCK, SYSTEM_MOCK]:
        if check_id in mock_dict:
            # Infer category from the dict's variable name
            name = [k for k, v in list(globals().items()) if v is mock_dict][0]
            if "AI" in name:
                return CheckCategory.AI
            if "NAS" in name:
                return CheckCategory.NAS
            if "NETWORK" in name:
                return CheckCategory.NETWORK
            if "SECURITY" in name:
                return CheckCategory.SECURITY
            if "STORAGE" in name:
                return CheckCategory.STORAGE
            if "SYSTEM" in name:
                return CheckCategory.SYSTEM
    return CheckCategory.SYSTEM


def get_mock_result(check_id: str, profile: str = "healthy") -> CheckResult:
    """Get a mock CheckResult for a given check_id and profile."""
    from nastool_core.checks.base import CheckCategory

    data = PROFILES.get(profile, PROFILES["healthy"])
    result_data = data.get(check_id, {
        "severity": CheckSeverity.INFO,
        "passed": True,
        "current": "mock",
        "expected": "mock",
        "message": f"Mock result for {check_id}",
    })

    return CheckResult(
        check_id=check_id,
        category=result_data.get("category", _find_category(check_id)),
        severity=result_data.get("severity", CheckSeverity.INFO),
        passed=result_data.get("passed", True),
        title=check_id.replace("_", " ").title(),
        current=result_data.get("current", "mock"),
        expected=result_data.get("expected", "mock"),
        message=result_data.get("message", f"Mock: {check_id}"),
        fix_available=result_data.get("fix_available", False),
        fix_id=result_data.get("fix_id"),
        fix_command=result_data.get("fix_command"),
        fix_description=result_data.get("fix_description"),
        fix_risk=result_data.get("fix_risk", "low"),
    )
