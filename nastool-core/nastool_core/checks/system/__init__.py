# System checks module
# After @check() decoration: the function name IS the class.
from . import (
    python_version, pip_installed, system_libs, memory_check,
    cron_jobs, system_logs, process_count, package_updates,
    system_disk, docker_service, docker_containers,
)

# @check() decorated classes (function = class after decoration)
PythonVersionCheck  = python_version
PipInstalledCheck   = pip_installed
SystemLibsCheck     = system_libs
MemoryCheck         = memory_check
CronJobsCheck       = cron_jobs
SystemLogsCheck     = system_logs
ProcessCountCheck   = process_count
PackageUpdatesCheck = package_updates
SystemDiskSpaceCheck = system_disk
DockerContainersCheck = docker_containers

# Legacy class-based checks (not yet migrated)
from .cpu_temp import CPUTempCheck
from .uptime import UptimeCheck

__all__ = [
    "PythonVersionCheck", "PipInstalledCheck", "SystemLibsCheck",
    "MemoryCheck", "CronJobsCheck", "SystemLogsCheck",
    "ProcessCountCheck", "PackageUpdatesCheck",
    "SystemDiskSpaceCheck", "DockerContainersCheck",
    "CPUTempCheck", "UptimeCheck",
]
