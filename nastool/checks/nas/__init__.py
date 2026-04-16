"""
checks/nas/__init__.py - NAS system checks

After @check() decoration:
  - function name = class name (use module import + alias pattern)
  - old class files: import directly
"""
from . import (
    afp_service, backup_status, cron_conflicts,
    dsm_version, ftp_service, log_disk,
    media_scanner, nfs_service, nas_temp,
    sftp_service, shared_perms, smb_service,
    snmp_service, ups_status, user_stats,
    webdav_service,
)

# @check() decorated files (function name = class name after decoration)
AFPServiceCheck      = afp_service
BackupStatusCheck   = backup_status
CronConflictsCheck  = cron_conflicts
DSMVersionCheck     = dsm_version
FTPServiceCheck     = ftp_service
LogDiskCheck        = log_disk
MediaScannerCheck   = media_scanner
NFSServiceCheck     = nfs_service
NASTemperatureCheck = nas_temp
SFTPServiceCheck    = sftp_service
SharedPermsCheck    = shared_perms
SMBServiceCheck     = smb_service
SNMPServiceCheck    = snmp_service
UPSStatusCheck      = ups_status
UserStatsCheck      = user_stats
WebDAVServiceCheck  = webdav_service

__all__ = [
    "DSMVersionCheck", "DSMBVersionCheck",
    "AFPServiceCheck", "FTPServiceCheck", "SFTPServiceCheck",
    "SMBServiceCheck", "SNMPServiceCheck", "WebDAVServiceCheck",
    "NFSServiceCheck", "MediaScannerCheck",
    "BackupStatusCheck", "CronConflictsCheck", "LogDiskCheck",
    "SharedPermsCheck", "UPSStatusCheck", "UserStatsCheck",
    "NASTemperatureCheck",
]
