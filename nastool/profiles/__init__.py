"""
Device profiles for nastool v3.0

Usage:
    from profiles import detect_device, get_profile, list_profiles

    # Auto-detect device
    profile = detect_device()
    print(f"Device: {profile.name}")

    # Get specific profile
    profile = get_profile("jetson-xavier-nx")

    # List all profiles
    profiles = list_profiles()
"""

from .loader import (
    DeviceProfile,
    ProfileLoader,
    detect_device,
    get_profile,
    get_loader,
    list_profiles,
)

__all__ = [
    "DeviceProfile",
    "ProfileLoader",
    "detect_device",
    "get_profile",
    "get_loader",
    "list_profiles",
]
