# Storage checks module
# After @check() decoration: function name IS the class.
from . import storage_disk, inode_check, io_wait, path_exists, write_speed, zfs_health

DiskSpaceCheck   = storage_disk
InodeCheck      = inode_check
IOWaitCheck     = io_wait
PathExistsCheck = path_exists
WriteSpeedCheck = write_speed
ZFSHealthCheck  = zfs_health

# Complex checks preserved as classes
from .smart_health import SMARTHealthCheck
from .hdd_temp import HDDTempCheck
from .raid_status import RAIDStatusCheck
from .docker_images import DockerImagesCheck
from .storage_trend import StorageTrendCheck

__all__ = [
    "DiskSpaceCheck", "InodeCheck", "IOWaitCheck",
    "PathExistsCheck", "WriteSpeedCheck", "ZFSHealthCheck",
    "SMARTHealthCheck", "HDDTempCheck", "RAIDStatusCheck",
    "DockerImagesCheck", "StorageTrendCheck",
]
