#!/usr/bin/env python3
"""
nastool v1.0.0 - Installation Script
One-command installer for NAS System Diagnostic Tool
"""

import subprocess
import sys
import os

def get_base_dir():
    """Get the directory containing this script."""
    return os.path.dirname(os.path.abspath(__file__))

def install():
    """Install nastool from local source."""
    base = get_base_dir()
    
    # Change to base directory
    os.chdir(base)
    
    print("=" * 60)
    print("  NASTool v1.0.0 - Installation")
    print("=" * 60)
    print()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("[X] Error: Python 3.8+ required")
        sys.exit(1)
    
    print(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"Location: {base}")
    print()
    
    # Install packages in dependency order
    # Each tuple: (package_name, subdirectory)
    packages = [
        ("nastool-common", "nastool-common"),
        ("nastool-core", "nastool-core"),
        ("nastool-adapters", "nastool-adapters"),
        ("nastool-reporters", "nastool-reporters"),
        ("nastool-fixes", "nastool-fixes"),
        ("nastool-cli", "nastool-cli"),
        ("nastool-meta", "nastool-meta"),
    ]
    
    for name, subdir in packages:
        pkg_path = os.path.join(base, subdir)
        print(f"Installing {name} from {subdir}/ ...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", pkg_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print(f"  [OK] {name}")
        else:
            # Check if already installed
            check = subprocess.run(
                [sys.executable, "-m", "pip", "show", name],
                capture_output=True, text=True
            )
            if check.returncode == 0:
                print(f"  [OK] {name} (already installed)")
            else:
                print(f"  [X] Failed to install {name}")
                print(f"      Error: {result.stderr[:300]}")
                sys.exit(1)
    
    print()
    print("=" * 60)
    print("  Installation Complete!")
    print("=" * 60)
    print()
    print("Usage:")
    print("  nastool              # Quick diagnosis")
    print("  nastool --full       # Full diagnosis")
    print("  nastool --fix        # Interactive repair")
    print("  nastool --help       # Show all options")
    print()
    print("Uninstall:")
    print("  python uninstall.py")
    print()

if __name__ == "__main__":
    install()
