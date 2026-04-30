"""
fixes/registry.py - Fix registry for dynamic discovery
"""

from typing import Dict, List, Type, Optional
from .base import Fix, FixResult


# Global registry
_FIXES: Dict[str, Type[Fix]] = {}


def register_fix(fix_class: Type[Fix]) -> Type[Fix]:
    """Decorator to register a fix class"""
    instance = fix_class()
    _FIXES[instance.fix_id] = fix_class
    return fix_class


def get_fix(fix_id: str) -> Optional[Type[Fix]]:
    """Get a fix class by ID"""
    return _FIXES.get(fix_id)


def get_all_fixes() -> List[Type[Fix]]:
    """Get all registered fix classes"""
    return list(_FIXES.values())


def run_fix(fix_id: str, confirm: bool = True) -> FixResult:
    """
    Run a fix by ID.

    Args:
        fix_id: Fix identifier
        confirm: Ask for confirmation before running

    Returns:
        FixResult with execution details
    """
    fix_class = _FIXES.get(fix_id)
    if not fix_class:
        return FixResult(
            fix_id=fix_id,
            success=False,
            message=f"Fix '{fix_id}' not found",
        )

    instance = fix_class()

    # Check if applicable
    if not instance.is_applicable():
        return FixResult(
            fix_id=fix_id,
            success=False,
            message="Fix is not applicable to this system",
        )

    # Check root requirement
    if instance.requires_root and not instance._check_root():
        return FixResult(
            fix_id=fix_id,
            success=False,
            message="This fix requires root privileges. Run with sudo.",
        )

    # Ask for confirmation
    if confirm:
        print(f"\n📋 Fix: {instance.title}")
        print(f"   Description: {instance.description}")
        print(f"   Risk: {instance.risk}")

        if not instance._confirm("Proceed with this fix?"):
            return FixResult(
                fix_id=fix_id,
                success=False,
                message="Fix cancelled by user",
            )

    # Execute fix
    return instance.run()


def list_available_fixes() -> Dict[str, dict]:
    """List all available fixes with metadata"""
    result = {}
    for fix_class in _FIXES.values():
        instance = fix_class()
        result[instance.fix_id] = {
            "id": instance.fix_id,
            "title": instance.title,
            "description": instance.description,
            "risk": instance.risk,
            "requires_root": instance.requires_root,
            "applicable": instance.is_applicable(),
        }
    return result
