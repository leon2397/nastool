# nastool-fixes - Automated fix scripts for NASTool
"""
NASTool Fixes Package (v4.0.0 - Security Enhanced)

安全准则：零破坏、零篡改、所有操作可撤销

Provides automated fix scripts for detected issues:
- Fix base classes and registry
- System fixes (packages, services, logs)
- Network fixes (DNS, firewall, proxy)
- Storage fixes (disk cleanup, permissions)
- Security fixes (SSH, SSL, firewall)
- AI/ML fixes (CUDA, drivers, containers)

Security Features (v4.0.0):
- FORBIDDEN_FIXES: Hard-coded block list for dangerous operations
- SecurityPolicy: Mandatory security checks before execution
- BackupManager: Automatic backup before modifications
- Rollback scripts: Auto-generated recovery scripts

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
# Import from security.py file, not security directory
import importlib.util
import os
import sys

# Add current directory to path for module discovery
sys.path.insert(0, os.path.dirname(__file__))

# Import security module from security.py
security_spec = importlib.util.spec_from_file_location("security", os.path.join(os.path.dirname(__file__), "security.py"))
security_module = importlib.util.module_from_spec(security_spec)
security_spec.loader.exec_module(security_module)

# Export FORBIDDEN_FIXES
FORBIDDEN_FIXES = security_module.FORBIDDEN_FIXES

__version__ = "4.0.0"
__all__ = [
    # Core
    "Fix",
    "FixResult",
    "register_fix",
    "get_fix",
    "get_all_fixes",
    "run_fix",
    "list_available_fixes",
    # Security (v4.0.0)
    "FORBIDDEN_FIXES",
]
