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
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

from nastool_common import get_logger
from nastool_core.checks.base import CheckResult

# Import fix modules
try:
    import nastool_fixes.system
    import nastool_fixes.storage
    import nastool_fixes.network
    import nastool_fixes.security
    import nastool_fixes.ai
    import nastool_fixes.nas
except ImportError as e:
    pass  # Some fix modules may not exist yet

from nastool_fixes import run_fix, list_available_fixes

__version__ = "4.0.0"
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

Device Management (v3.0):
  nastool device list           List all registered devices
  nastool device add <host>     Register a new device
  nastool device tag <id> --tag rk3588  Add tag to device

Batch Diagnosis (v3.0):
  nastool --batch @devices.txt  Batch diagnose devices from file
  nastool --batch @prod         Batch diagnose devices in group
  nastool --batch @all          Batch diagnose all devices

Compare Analysis (v3.0):
  nastool compare <id1> <id2>   Compare two devices
  nastool compare <id> --history 7d  Compare with history
  nastool baseline <id>         Compare with ideal baseline
        """.strip(),
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # device subcommand
    device_parser = subparsers.add_parser("device", help="Device management")
    device_sub = device_parser.add_subparsers(dest="device_cmd", help="Device commands")

    device_list = device_sub.add_parser("list", help="List devices")
    device_list.add_argument("--group", "-g", help="Filter by group")
    device_list.add_argument("--type", "-t", help="Filter by device type")
    device_list.add_argument("--status", "-s", help="Filter by status")

    device_add = device_sub.add_parser("add", help="Add device")
    device_add.add_argument("host", help="Device host (IP or hostname)")
    device_add.add_argument("--id", help="Device ID (auto-generated if not provided)")
    device_add.add_argument("--name", "-n", help="Device name")
    device_add.add_argument("--group", "-g", help="Group name")
    device_add.add_argument("--type", "-t", help="Device type (rk3588/rk3568/jetson/nas)")
    device_add.add_argument("--tag", action="append", help="Tags (can use multiple)")

    device_remove = device_sub.add_parser("remove", help="Remove device")
    device_remove.add_argument("device_id", help="Device ID to remove")

    device_tag = device_sub.add_parser("tag", help="Tag device")
    device_tag.add_argument("device_id", help="Device ID")
    device_tag.add_argument("--tag", "-t", required=True, action="append", help="Tags to add")

    # compare subcommand
    compare_parser = subparsers.add_parser("compare", help="Compare devices")
    compare_parser.add_argument("device_id", nargs="?", help="Device ID (or two IDs for direct compare)")
    compare_parser.add_argument("device_id2", nargs="?", help="Second device ID for direct compare")
    compare_parser.add_argument("--history", "-H", type=str, help="Compare with history (e.g., 7d, 30d)")
    compare_parser.add_argument("--full", action="store_true", help="Full diagnosis for comparison")

    # baseline subcommand
    baseline_parser = subparsers.add_parser("baseline", help="Compare with ideal baseline")
    baseline_parser.add_argument("device_id", help="Device ID")
    baseline_parser.add_argument("--full", action="store_true", help="Full diagnosis")

    # monitor subcommand
    monitor_parser = subparsers.add_parser("monitor", help="Monitor devices via WebSocket")
    monitor_parser.add_argument("device_ids", nargs="*", help="Device IDs to monitor")
    monitor_parser.add_argument("--relay", default="ws://localhost:18888", help="Relay WebSocket URL")
    monitor_parser.add_argument("--all", action="store_true", help="Monitor all devices")
    monitor_parser.add_argument("--key", help="API key for authentication")

    # Mode flags
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--version", "-v", action="store_true", help="Show version")
    mode_group.add_argument("--full", action="store_true", help="Full diagnosis with benchmarks")
    mode_group.add_argument("--fix", action="store_true", help="Diagnosis + interactive fix")
    mode_group.add_argument("--fix-auto", action="store_true", help="Diagnosis + auto fix (no confirm)")
    mode_group.add_argument("--list-fixes", action="store_true", help="List all available fixes")
    mode_group.add_argument("--setup", action="store_true", help="Run interactive setup wizard")

    # Options
    parser.add_argument("--mock", type=str, metavar="PROFILE",
                       help="Mock mode: healthy/degraded/critical/mixed")
    parser.add_argument("--output", "-o", type=str, metavar="FILE",
                       help="Output file for report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--category", type=str, metavar="CAT",
                       help="Run checks for specific category only")
    parser.add_argument("--target", type=str, metavar="TARGET",
                       help="Remote target: http://host:port or relay://host:port")
    parser.add_argument("--tune", type=str, metavar="PROFILE",
                       help="Show tuning recommendations: performance/balanced/powersave")
    parser.add_argument("--chip", type=str, metavar="CHIP", default="RK3588",
                       help="Chip model for tuning: RK3588/RK3568/RK3566 (default: RK3588)")
    parser.add_argument("--rk-report", type=str, metavar="FORMAT",
                       help="Generate RK-specific report: text/markdown/json")

    # Batch options (v3.0)
    parser.add_argument("--batch", type=str, metavar="SOURCE",
                       help="Batch diagnosis: @file.txt, @group, @all, or id1,id2,id3")
    parser.add_argument("--parallel", type=int, default=4, metavar="N",
                       help="Parallel workers for batch (default: 4)")
    parser.add_argument("--timeout", type=int, default=300, metavar="SEC",
                       help="Timeout per device in seconds (default: 300)")

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
            # BUG-005: --full 真实模式禁止静默降级 mock
            # 如果用户明确指定 --full 且未指定 --mock，则直接报错退出
            if full_mode and "--mock" not in sys.argv:
                print("\n" + "="*60)
                print("  ERROR: Real device diagnosis failed in --full mode!")
                print("="*60)
                print(f"  Error: {e}")
                print("  This may be due to:")
                print("    - Device not reachable")
                print("    - Missing system tools (npu-smi, tegrastats, etc.)")
                print("    - Permission denied")
                print("\n  --full mode prohibits automatic fallback to mock.")
                print("  Use --mock PROFILE explicitly if you want mock data.")
                print("="*60 + "\n")
                raise RuntimeError(f"Real diagnosis failed in --full mode: {e}") from e
            
            # 其他情况（quick mode 或用户未明确要求真实检测）允许降级
            print("\n" + "="*60)
            print("  WARNING: Real device checks failed!")
            print("="*60)
            print(f"  Error: {e}")
            print("  This may be due to:")
            print("    - Device not reachable")
            print("    - Missing system tools (npu-smi, tegrastats, etc.)")
            print("    - Permission denied")
            print("\n  Falling back to mock mode for demonstration.")
            print("  Use --mock PROFILE for reliable testing.")
            print("="*60 + "\n")

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
    
    print(f"\n{len(fixable)} issues can be fixed automatically:")
    for check, fix_id in fixable:
        print(f"  - {check.title}: {fix_id}")
    
    if not auto:
        response = input("\nApply fixes? [y/N]: ")
        if response.lower() != 'y':
            print("Fixes cancelled.")
            return fix_results
    
    # Run fixes
    for check, fix_id in fixable:
        print(f"\nApplying {fix_id}...")
        result = run_fix(fix_id)
        fix_results.append(result)
        
        if result['success']:
            print(f"  [OK] Fixed: {result['message']}")
        else:
            print(f"  [FAIL] Failed: {result['message']}")
    
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
    
    # Handle setup wizard
    if args.setup:
        from nastool_common.utils.interactive_wizard import run_setup_wizard
        run_setup_wizard()
        return 0

    # Handle subcommands (v3.0)
    if args.command == "device":
        return handle_device_command(args)

    if args.command == "compare":
        return handle_compare_command(args)

    if args.command == "baseline":
        return handle_baseline_command(args)

    if args.command == "monitor":
        return handle_monitor_command(args)

    # Handle batch diagnosis (v3.0)
    if args.batch:
        return handle_batch_diagnosis(args)
    
    # Handle tuning recommendations
    if args.tune:
        from nastool_core.tuning_advisor import TuningAdvisor
        
        advisor = TuningAdvisor(chip_model=args.chip)
        profile_name = args.tune
        
        if profile_name not in advisor.PROFILES:
            print(f"Unknown profile: {profile_name}")
            print(f"Available: {', '.join(advisor.PROFILES.keys())}")
            return 1
        
        # Run quick diagnosis to get current state
        summary, results = run_diagnosis(quick_mode=True)
        
        # Analyze and show recommendations
        recommendations = advisor.analyze(results)
        
        print(f"\n{'='*60}")
        print(f"  Tuning Recommendations ({len(recommendations)})")
        print(f"  Profile: {profile_name} | Chip: {args.chip}")
        print(f"{'='*60}")
        
        for rec in recommendations:
            print(f"\n{rec}")
        
        # Profile commands
        profile_rec = advisor.get_profile_recommendation(profile_name)
        if profile_rec.get('commands'):
            print(f"\n{'='*60}")
            print(f"  Quick Apply ({profile_name} profile)")
            print(f"{'='*60}")
            for i, cmd in enumerate(profile_rec['commands'], 1):
                print(f"  {i}. {cmd}")
        
        return 0

    # Handle list-fixes
    if args.list_fixes:
        fixes = list_available_fixes()
        print(f"\n  Available Fixes ({len(fixes)} total):\n")
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
        from nastool_reporters.terminal import TerminalReporter
        reporter = TerminalReporter(use_color=not args.no_color)
        if hasattr(reporter, 'print_report'):
            reporter.print_report(results)
    
    # Show timing
    print(f"\nCompleted in {diag_time:.1f}s")
    
    # Show tuning recommendations if requested
    if args.tune:
        from nastool_core.tuning_advisor import TuningAdvisor
        
        advisor = TuningAdvisor(chip_model=args.chip)
        recommendations = advisor.analyze(results)
        
        if recommendations:
            print(f"\n{'='*60}")
            print(f"  Tuning Recommendations ({len(recommendations)})")
            print(f"  Profile: {args.tune} | Chip: {args.chip}")
            print(f"{'='*60}")
            
            for rec in recommendations:
                print(f"\n{rec}")
            
            # Profile commands
            profile_rec = advisor.get_profile_recommendation(args.tune)
            if profile_rec.get('commands'):
                print(f"\n{'='*60}")
                print(f"  Quick Apply ({args.tune} profile)")
                print(f"{'='*60}")
                for i, cmd in enumerate(profile_rec['commands'], 1):
                    print(f"  {i}. {cmd}")
        else:
            print("\n  No tuning recommendations - system looks good!")
    
    # Generate RK-specific report if requested
    if args.rk_report:
        from nastool_reporters.rk_reporter import RKReporter
        
        fmt = args.rk_report
        if fmt not in ("text", "markdown", "json"):
            print(f"Unknown report format: {fmt}. Use: text/markdown/json")
            fmt = "text"
        
        rk_out = None
        if args.output:
            # Derive RK report path from output path
            base, ext = os.path.splitext(args.output)
            ext_map = {"json": ".json", "markdown": ".md", "text": ".txt"}
            rk_out = f"{base}_rk{ext_map.get(fmt, ext)}"
        
        reporter = RKReporter(chip_model=args.chip)
        reporter.generate(
            results,
            output_format=fmt,
            output_path=rk_out,
            tune_profile=args.tune,
        )
    
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


# ==================== v3.0 Subcommand Handlers ====================

def handle_device_command(args) -> int:
    """Handle device subcommand"""
    from nastool_core.device_manager import DeviceManager

    dm = DeviceManager()

    if args.device_cmd == "list":
        devices = dm.list_devices(
            group=getattr(args, 'group', None),
            device_type=getattr(args, 'type', None),
            status=getattr(args, 'status', None)
        )

        if not devices:
            print("No devices found.")
            return 0

        print(f"\n  Total: {len(devices)} devices\n")
        print(f"  {'ID':<20} {'Host':<20} {'Type':<10} {'Group':<10} {'Status':<8}")
        print(f"  {'-'*20} {'-'*20} {'-'*10} {'-'*10} {'-'*8}")

        for d in devices:
            status_icon = "🟢" if d.status == "online" else "🔴"
            print(f"  {d.id:<20} {d.host:<20} {d.device_type:<10} {d.group or '-':<10} {status_icon} {d.status}")
        return 0

    elif args.device_cmd == "add":
        device = dm.add_device(
            host=args.host,
            device_id=getattr(args, 'id', None),
            name=getattr(args, 'name', None),
            device_type=getattr(args, 'type', None),
            group=getattr(args, 'group', None),
            tags=args.tag if args.tag else []
        )
        print(f"\n  Added device: {device.id}")
        print(f"    Host: {device.host}")
        print(f"    Type: {device.device_type or 'unknown'}")
        return 0

    elif args.device_cmd == "remove":
        if dm.remove_device(args.device_id):
            print(f"\n  Removed device: {args.device_id}")
            return 0
        else:
            print(f"\n  Device not found: {args.device_id}")
            return 1

    elif args.device_cmd == "tag":
        device = dm.get_device(args.device_id)
        if not device:
            print(f"\n  Device not found: {args.device_id}")
            return 1
        
        for tag in args.tag:
            device.add_tag(tag)
        dm._save_devices()
        
        print(f"\n  Updated tags for {args.device_id}:")
        for tag in device.tags:
            print(f"    - {tag}")
        return 0

    else:
        print("Usage: nastool device {list|add|remove|tag}")
        return 1


def handle_compare_command(args) -> int:
    """Handle compare subcommand"""
    from nastool_core.device_manager import DeviceManager
    from nastool_adapters.relay_detector import RelayDetector
    
    dm = DeviceManager()
    
    # Two device IDs provided directly
    if args.device_id2:
        device1 = dm.get_device(args.device_id)
        device2 = dm.get_device(args.device_id2)
        
        if not device1 or not device2:
            print("Device not found")
            return 1
        
        print(f"\n  Comparing {device1.id} vs {device2.id}...")
        # TODO: Run diagnosis on both and compare
        return 0
    
    # Single device with --history
    if args.history:
        device = dm.get_device(args.device_id)
        if not device:
            print(f"Device not found: {args.device_id}")
            return 1
        
        print(f"\n  Comparing {device.id} with history ({args.history})...")
        # TODO: Load historical data and compare
        return 0
    
    print("Usage: nastool compare <id1> <id2> OR nastool compare <id> --history <period>")
    return 1


def handle_baseline_command(args) -> int:
    """Handle baseline subcommand"""
    from nastool_core.device_manager import DeviceManager
    
    dm = DeviceManager()
    device = dm.get_device(args.device_id)
    
    if not device:
        print(f"Device not found: {args.device_id}")
        return 1
    
    print(f"\n  Comparing {device.id} with ideal baseline...")
    # TODO: Generate baseline comparison
    return 0


def handle_batch_diagnosis(args) -> int:
    """Handle batch diagnosis"""
    from nastool_core.device_manager import DeviceManager
    from nastool_adapters.batch import BatchDiagnosis
    
    batch_source = args.batch
    dm = DeviceManager()
    
    # Parse device IDs from source
    if batch_source.startswith("@"):
        source = batch_source[1:]
        if source == "all":
            device_ids = [d.id for d in dm.list_devices()]
        else:
            # Try as group name
            devices = dm.list_devices(group=source)
            if devices:
                device_ids = [d.id for d in devices]
            else:
                # Try as file
                try:
                    with open(source, 'r') as f:
                        device_ids = [line.strip() for line in f if line.strip()]
                except FileNotFoundError:
                    print(f"Source not found: {source}")
                    return 1
    else:
        # Comma-separated IDs
        device_ids = batch_source.split(",")
    
    if not device_ids:
        print("No devices to diagnose")
        return 1
    
    print(f"\n  Batch diagnosis: {len(device_ids)} devices")
    print(f"  Parallel: {args.parallel}, Timeout: {args.timeout}s\n")
    
    # Run batch diagnosis
    batch = BatchDiagnosis(max_workers=args.parallel, timeout=args.timeout)
    results = batch.run(device_ids, full_mode=args.full)
    
    # Display results
    for device_id, result in results.items():
        if result['success']:
            summary = result['summary']
            score = summary.get('score', 0)
            status = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
            print(f"  {status} {device_id}: {score}/100")
        else:
            print(f"  🔴 {device_id}: Failed - {result.get('error', 'Unknown')}")
    
    return 0


def handle_monitor_command(args) -> int:
    """Handle monitor subcommand (WebSocket real-time monitoring)"""
    from nastool_adapters.ws_client import run_monitor
    
    device_ids = args.device_ids
    
    if args.all:
        # Get all devices from DeviceManager
        from nastool_core.device_manager import DeviceManager
        dm = DeviceManager()
        device_ids = [d.id for d in dm.list_devices()]

    print(f"\n  WebSocket Monitor")
    print(f"  Relay: {args.relay}")
    print(f"  Devices: {device_ids or 'all'}")
    print(f"\n  Press Ctrl+C to stop...\n")

    # Callback for device updates
    def on_device_update(payload: dict):
        device_id = payload.get("device_id", "unknown")
        status = payload.get("status", "unknown")
        stats = payload.get("stats", {})

        status_icon = "🟢" if status == "online" else "🔴" if status == "offline" else "⚪"
        cpu = stats.get("cpu_percent", "N/A")
        mem = stats.get("memory_percent", "N/A")

        print(f"  {status_icon} {device_id}: status={status}, cpu={cpu}%, mem={mem}%")

    try:
        run_monitor(
            relay_url=args.relay,
            device_ids=device_ids,
            api_key=getattr(args, 'key', None),
            on_update=on_device_update
        )
    except KeyboardInterrupt:
        print("\n  Monitor stopped.")
        return 0
    except ConnectionError as e:
        print(f"\n  Connection failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
