# nastool v2.0 - Fixes module
from .base import Fix, FixResult
from .registry import register_fix, get_fix, get_all_fixes, run_fix

# ── System fixes ──────────────────────────────────────────────
from .system.install_python import InstallPythonFix
from .system.install_docker import DockerFix
from .system.setup_logrotate import SetupLogrotateFix

# ── Network fixes ─────────────────────────────────────────────
from .network.config_dns import ConfigDNSFix

# ── Storage fixes ─────────────────────────────────────────────
from .storage.create_paths import CreatePathsFix
from .storage.cleanup_logs import CleanupLogsFix
from .storage.cleanup_docker_images import CleanupDockerImagesFix
from .storage.cleanup_tmp_space import CleanupTmpSpaceFix
from .storage.config_raid_recovery import RAIDRecoveryFix

# ── AI fixes ──────────────────────────────────────────────────
from .ai.install_cuda import InstallCUDAFix

# ── Security fixes ────────────────────────────────────────────
from .security.disable_root_login import DisableRootLoginFix
from .security.enable_fail2ban import EnableFail2banFix
from .security.enforce_password_policy import EnforcePasswordPolicyFix
from .security.renew_ssl_cert import RenewSSLCertFix

# ── NAS fixes ─────────────────────────────────────────────────
from .nas.config_ups_shutdown import ConfigUPSShutdownFix


def list_available_fixes():
    """List all available fixes with their info"""
    fixes = {}
    for fix_cls in get_all_fixes():
        instance = fix_cls()
        fixes[instance.fix_id] = {
            "id": instance.fix_id,
            "title": instance.title,
            "description": instance.description,
            "risk": getattr(instance, "risk", "unknown"),
            "requires_root": getattr(instance, "requires_root", True),
            "command": getattr(instance, "command", ""),
            "applicable": instance.is_applicable(),
        }
    return fixes


__all__ = [
    "Fix",
    "FixResult",
    "register_fix",
    "get_fix",
    "get_all_fixes",
    "run_fix",
    "list_available_fixes",
    # System
    "InstallPythonFix",
    "DockerFix",
    "SetupLogrotateFix",
    # Network
    "ConfigDNSFix",
    # Storage
    "CreatePathsFix",
    "CleanupLogsFix",
    "CleanupDockerImagesFix",
    "CleanupTmpSpaceFix",
    "RAIDRecoveryFix",
    # AI
    "InstallCUDAFix",
    # Security
    "DisableRootLoginFix",
    "EnableFail2banFix",
    "EnforcePasswordPolicyFix",
    "RenewSSLCertFix",
    # NAS
    "ConfigUPSShutdownFix",
]
