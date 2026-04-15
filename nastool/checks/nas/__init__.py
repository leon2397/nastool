"""
checks/nas/__init__.py - NAS system checks
"""
from .dsm_version import DSMVersionCheck
from .user_stats import UserStatsCheck
from .shared_perms import SharedPermsCheck
from .ups_status import UPSStatusCheck
from .log_disk import LogDiskCheck
from .cron_conflicts import CronConflictsCheck

from .snmp_service import SNMPServiceCheck
from .afp_service import AFPServiceCheck
from .ftp_service import FTPServiceCheck
from .sftp_service import SFTPServiceCheck
from .backup_status import BackupStatusCheck
from .media_scanner import MediaScannerCheck
from .nas_temp import NASTemperatureCheck
__all__ = [
    "DSMVersionCheck",
    "UserStatsCheck",
    "SharedPermsCheck",
    "UPSStatusCheck",
    "LogDiskCheck",
    "CronConflictsCheck",
    "SNMPServiceCheck",
    "AFPServiceCheck",
    "FTPServiceCheck",
    "SFTPServiceCheck",
    "BackupStatusCheck",
    "MediaScannerCheck",
    "NASTemperatureCheck",
]
