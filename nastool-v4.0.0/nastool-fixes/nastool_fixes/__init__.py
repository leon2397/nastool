# nastool-fixes - Automated fix scripts for NASTool
"""
NASTool Fixes Package

Provides automated fix scripts for detected issues:
- Fix base classes and registry
- System fixes (packages, services, logs)
- Network fixes (DNS, firewall, proxy)
- Storage fixes (disk cleanup, permissions)
- Security fixes (SSH, SSL, firewall)
- AI/ML fixes (CUDA, drivers, containers)

Usage:
    from nastool_fixes import list_available_fixes, run_fix
    
    fixes = list_available_fixes()
    result = run_fix("fix_id", check_result)
"""

from .base import Fix, FixResult
from .registry import (
    register_fix,
    get_fix,
    get_all_fixes,
    run_fix,
    list_available_fixes,
)

__version__ = "4.0.0"
__all__ = [
    "Fix",
    "FixResult",
    "register_fix",
    "get_fix",
    "get_all_fixes",
    "run_fix",
    "list_available_fixes",
]
