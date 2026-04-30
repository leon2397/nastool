#!/usr/bin/env python3
"""
nastool v1.0.0 - Uninstallation Script
One-command uninstaller for NAS System Diagnostic Tool
"""

import subprocess
import sys

def uninstall():
    """Uninstall nastool and all components."""
    print("=" * 60)
    print("  NASTool v1.0.0 - Uninstallation")
    print("=" * 60)
    print()
    
    packages = [
        "nastool",
        "nastool-cli",
        "nastool-fixes",
        "nastool-reporters",
        "nastool-adapters",
        "nastool-core",
        "nastool-common",
    ]
    
    for pkg in packages:
        print(f"Uninstalling {pkg}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", pkg],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 or "not installed" in result.stderr:
            print(f"  [OK] {pkg} removed")
        else:
            print(f"  [-] {pkg} not installed (OK)")
    
    print()
    print("=" * 60)
    print("  Uninstallation Complete!")
    print("=" * 60)
    print()
    print("Note: If you want to reinstall, run install.py")
    print()

if __name__ == "__main__":
    uninstall()
