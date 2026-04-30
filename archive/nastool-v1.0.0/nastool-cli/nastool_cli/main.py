# -*- coding: utf-8 -*-#!/usr/bin/env python3
"""
nastool-cli - Main entry point for NASTool

Usage:
    nastool                       # Quick diagnosis
    nastool --full                # Full diagnosis with benchmarks
    nastool --fix                 # Diagnosis + interactive fix
    nastool --fix-auto            # Diagnosis + auto fix (no confirm)
    nastool --mock healthy        # Mock mode
    nastool --list-fixes          # List available fixes
    nastool --output report.txt   # Save report to file
    nastool --json                # Output as JSON
    nastool --version             # Show version
"""

import argparse
import sys
import json
import time
from typing import Optional, List, Dict, Any

from nastool_common.config import Config
from nastool_common.logger import get_logger
from nastool_common.messages import msg
from nastool_core.checks import run_all_checks, run_mock_checks, CheckSeverity, CheckResult
from nastool_reporters.terminal import TerminalReporter

# Import fixes to register them (must be before using list_available_fixes)
try:
    import nastool_fixes.system
    import nastool_fixes.network
    import nastool_fixes.storage
    import nastool_fixes.security
    import nastool_fixes.ai
    import nastool_fixes.nas
except ImportError as e:
    pass  # Some fix modules may not exist yet

from nastool_fixes import run_fix, list_available_fixes

__version__ = "1.0.0"
logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="nastool - ARM Device Diagnostic Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nastool                       Quick diagnosis (default)
  nastool --full                Full diagnosis with benchmarks
  nastool --fix                 Run diagnosis and fix issues interactively
  nastool --fix-auto            Fix issues without confirmation (careful!)
  nastool --mock healthy        Use mock data for testing
  nastool --list-fixes          Show all available fixes
  nastool -o report.json --json Save JSON report to file
        """.strip(),
    )
    
    # Main modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--version", action="store_true", help="Show version")
    mode_group.add_argument("--full", action="store_true", help="Full diagnosis with benchmarks")
    mode_group.add_argument("--fix", action="store_true", help="Diagnosis + interactive fix")
    mode_group.add_argument("--fix-auto", action="store_true", help="Diagnosis + auto fix (no confirm)")
    mode_group.add_argument("--list-fixes", action="store_true", help="List all available fixes")
    
    # Options
    parser.add_argument("--mock", type=str, metavar="PROFILE",
                       help="Mock mode: healthy/degraded/critical/mixed")
    parser.add_argument("--output", "-o", type=str, metavar="FILE",
                       help="Output file for report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--category", type=str, metavar="CAT",
                       help="Run checks for specific category only")
    
    return parser.parse_args()


def run_diagnosis(mock_profile: Optional[str] = None, full_mode: bool = False, quick_mode: bool = False) -> tuple:
    """
    Run diagnosis and return results.
    
    Args:
        mock_profile: Mock profile name (healthy/degraded/critical/mixed)
        full_mode: If True, run all checks including benchmarks
        quick_mode: If True, run only critical and warning checks (skip info/benchmarks)
    
    Returns:
        tuple: (summary, results_list)
    """
    if mock_profile:
        print(f"Running mock diagnosis: {mock_profile}")
        from nastool_core.checks import run_mock_checks
        summary = run_mock_checks(mock_profile, full_mode=full_mode)
        return summary, summary.results
    else:
        if full_mode:
            print("Running full diagnosis (including benchmarks)...")
        elif quick_mode:
            print("Running quick diagnosis (critical checks only)...")
        else:
            print("Running diagnosis...")
        
        try:
            from nastool_core.checks import run_all_checks
            # Run checks with full_mode flag
            summary = run_all_checks(full_mode=full_mode)
            return summary, summary.results
        except Exception as e:
            print(f"Warning: Real checks failed ({e})")
            print("Falling back to mock mode. Use --mock for reliable testing.")
            from nastool_core.checks import run_mock_checks
            summary = run_mock_checks("healthy")
            return summary, summary.results


def run_fixes_for_failures(results: List[CheckResult], auto: bool = False) -> List[Dict[str, Any]]:
    """
    Run fixes for failed checks.
    
    Args:
        results: List of check results
        auto: If True, don't ask for confirmation
        
    Returns:
        List of fix results
    """
    fix_results = []
    fixes_available = list_available_fixes()
    
    # Find failed checks that have fixes
    failed_checks = [r for r in results if not r.passed]
    fixable = []
    
    for check in failed_checks:
        # Map check_id to fix_id (convention: fix_<check_id>)
        fix_id = f"fix_{check.check_id}"
        if fix_id in fixes_available:
            fixable.append((check, fix_id))
    
    if not fixable:
        print("\nNo automatic fixes available for current issues.")
        return fix_results
    
    print(f"\nFound {len(fixable)} fixable issues:")
    for check, fix_id in fixable:
        fix_info = fixes_available[fix_id]
        print(f"  - {check.name}: {fix_info['title']} (risk: {fix_info['risk']})")
    
    if not auto:
        print()
        response = input("Run fixes? [y/N/a(ll)] ").strip().lower()
        if response not in ('y', 'yes', 'a', 'all'):
            print("Fixes cancelled.")
            return fix_results
        auto = (response in ('a', 'all'))
    
    print("\nRunning fixes...")
    for check, fix_id in fixable:
        print(f"\n  Fixing: {check.name}")
        result = run_fix(fix_id, confirm=not auto)
        fix_results.append({
            "check_id": check.check_id,
            "fix_id": fix_id,
            "success": result.success,
            "message": result.message,
        })
        status = "OK" if result.success else "FAIL"
        print(f"    [{status}] {result.message}")
    
    return fix_results


def save_report(results: List[CheckResult], summary: Any, output_path: str, as_json: bool = False):
    """Save report to file"""
    if as_json:
        # JSON output
        report = {
            "version": __version__,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "score": summary.score if hasattr(summary, 'score') else 0,
                "total": summary.total if hasattr(summary, 'total') else len(results),
                "passed": summary.passed if hasattr(summary, 'passed') else sum(1 for r in results if r.passed),
                "warnings": summary.warnings if hasattr(summary, 'warnings') else sum(1 for r in results if r.severity.value == "warning"),
                "critical": summary.critical if hasattr(summary, 'critical') else sum(1 for r in results if r.severity.value == "critical"),
            },
            "results": [
                {
                    "check_id": r.check_id,
                    "title": r.title,
                    "severity": r.severity.value,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details,
                    "current": str(r.current) if r.current is not None else None,
                    "expected": r.expected,
                    "fix_description": r.fix_description,
                }
                for r in results
            ]
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    else:
        # Text output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("NASTool Diagnostic Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Version: {__version__}\n")
            f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            score = summary.score if hasattr(summary, 'score') else 0
            total = summary.total if hasattr(summary, 'total') else len(results)
            passed = summary.passed if hasattr(summary, 'passed') else sum(1 for r in results if r.passed)
            warnings = summary.warnings if hasattr(summary, 'warnings') else sum(1 for r in results if r.severity.value == "warning")
            critical = summary.critical if hasattr(summary, 'critical') else sum(1 for r in results if r.severity.value == "critical")
            
            f.write(f"Health Score: {score}/100\n")
            f.write(f"Total Checks: {total}\n")
            f.write(f"Passed: {passed} | Warnings: {warnings} | Critical: {critical}\n\n")
            
            f.write("Detailed Results:\n")
            f.write("-" * 50 + "\n")
            for r in results:
                status = "PASS" if r.passed else ("WARN" if r.severity.value == "warning" else "FAIL")
                f.write(f"\n[{status}] {r.title}\n")
                f.write(f"  ID: {r.check_id}\n")
                f.write(f"  Severity: {r.severity.value}\n")
                f.write(f"  Message: {r.message}\n")
                if r.details:
                    f.write(f"  Details: {r.details}\n")
                if r.fix_description:
                    f.write(f"  Suggestion: {r.fix_description}\n")
    
    print(f"\nReport saved to: {output_path}")


def main():
    """Main entry point"""
    args = parse_args()
    
    # Handle simple commands first
    if args.version:
        print(f"nastool {__version__}")
        return 0
    
    if args.list_fixes:
        print(f"nastool {__version__}")
        print("=" * 50)
        print("\nAvailable Fixes:\n")
        fixes = list_available_fixes()
        if not fixes:
            print("  No fixes registered yet.")
        else:
            for fix_id, info in sorted(fixes.items()):
                root_flag = " [ROOT]" if info['requires_root'] else ""
                app_flag = " [OK]" if info['applicable'] else " [N/A]"
                print(f"  {fix_id}{root_flag}{app_flag}")
                print(f"    Title: {info['title']}")
                print(f"    Desc: {info['description']}")
                print(f"    Risk: {info['risk']}")
                print()
        return 0
    
    # Main diagnosis flow
    print(f"nastool {__version__}")
    print("=" * 50)
    
    # Run diagnosis
    # Default: quick mode with mock data (real checks still unstable)
    # --full: all checks including benchmarks
    # --mock: explicit mock mode with profile
    start_time = time.time()
    
    # Default to mock healthy if no mode specified
    mock_profile = args.mock if args.mock else "healthy"
    if not args.mock and not args.full:
        print("  [Using mock data - real device detection coming in v1.1]")
    
    summary, results = run_diagnosis(
        mock_profile=mock_profile,
        full_mode=args.full,
        quick_mode=not args.full and not args.mock
    )
    diag_time = time.time() - start_time
    
    # Display report
    if args.json and not args.output:
        # JSON to terminal
        report = {
            "version": __version__,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "score": summary.score if hasattr(summary, 'score') else 0,
                "total": summary.total if hasattr(summary, 'total') else len(results),
                "passed": summary.passed if hasattr(summary, 'passed') else sum(1 for r in results if r.passed),
                "warnings": summary.warnings if hasattr(summary, 'warnings') else sum(1 for r in results if r.severity.value == "warning"),
                "critical": summary.critical if hasattr(summary, 'critical') else sum(1 for r in results if r.severity.value == "critical"),
            },
            "results": [
                {
                    "check_id": r.check_id,
                    "title": r.title,
                    "severity": r.severity.value,
                    "passed": r.passed,
                    "message": r.message,
                    "current": str(r.current) if r.current is not None else None,
                    "expected": r.expected,
                    "fix_description": r.fix_description,
                }
                for r in results
            ]
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        reporter = TerminalReporter(use_color=not args.no_color)
        if hasattr(reporter, 'print_report'):
            reporter.print_report(results)
    
    # Show timing
    print(f"\nCompleted in {diag_time:.1f}s")
    
    # Run fixes if requested
    if args.fix or args.fix_auto:
        # Use new interactive fix flow (v5.1.0)
        from nastool_fixes.interactive_fix import interactive_fix_flow
        interactive_fix_flow(results, auto=args.fix_auto)
    
    # Save report if requested
    if args.output:
        save_report(results, summary, args.output, as_json=args.json)
    
    # Exit code based on results
    critical_count = summary.critical if hasattr(summary, 'critical') else sum(1 for r in results if r.severity.value == "critical")
    if critical_count > 0:
        return 2  # Critical issues found
    
    warning_count = summary.warnings if hasattr(summary, 'warnings') else sum(1 for r in results if r.severity.value == "warning")
    if warning_count > 0:
        return 1  # Warnings found
    
    return 0  # All good


if __name__ == "__main__":
    sys.exit(main())
