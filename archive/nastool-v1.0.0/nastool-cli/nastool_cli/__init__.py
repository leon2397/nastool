# nastool-cli - Command Line Interface for NASTool
"""
NASTool CLI Package

Provides the main command line interface:
- `nastool` command entry point
- diagnose: Run system diagnostics
- monitor: Start monitoring daemon
- web: Start web dashboard
- fix: Apply automated fixes

Usage:
    nastool --help
    nastool diagnose
    nastool --mock healthy
"""

from .main import main

__version__ = "1.0.0"
__all__ = ["main"]
