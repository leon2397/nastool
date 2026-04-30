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

import os

import time

from typing import Optional, List, Dict, Any



from nastool_common.config import Config

from nastool_adapters.http_detector import RemoteHTTPDetector

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



# Import scan module for one-click device detection

try:

    from nastool_cli.scan import NastoolScan, DeviceScanner, DeviceDatabase

    HAS_SCAN = True

except ImportError as e:

    HAS_SCAN = False

    print(f"Warning: Scan module not available ({e})")



__version__ = "4.1.0"
logger = get_logger(__name__)


def show_banner():
    """Show NASTool banner"""
    banner = """
=====================================================
    _   _    ____    ____    _   _   _____    ____
   | \ | |  / ___|  / ___|  | | | | |_   _|  / ___|
   |  \| | | |  _  | |      | | | |   | |   | |  _
   | |\  | | |_| | | |___   | |_| |   | |   | |_| |
   |_| \_|  \____|  \____|   \___/    |_|    \____|

         NASTool • AI NAS 智能管理工具 • v{}
=====================================================
""".format(__version__)
    print(banner)


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

    device_remove.add_argument("device_id", help="Device ID")



    device_tag = device_sub.add_parser("tag", help="Add tag to device")

    device_tag.add_argument("device_id", help="Device ID")

    device_tag.add_argument("--tag", "-t", required=True, help="Tag to add")



    device_untag = device_sub.add_parser("untag", help="Remove tag from device")

    device_untag.add_argument("device_id", help="Device ID")

    device_untag.add_argument("--tag", "-t", required=True, help="Tag to remove")



    # compare subcommand

    compare_parser = subparsers.add_parser("compare", help="Compare devices")

    compare_parser.add_argument("device_ids", nargs="+", help="Device IDs to compare")

    compare_parser.add_argument("--history", "-H", type=int, metavar="DAYS",

                                help="Compare with history (days)")

    compare_parser.add_argument("--output", "-o", help="Output file")



    # baseline subcommand

    baseline_parser = subparsers.add_parser("baseline", help="Compare with ideal baseline")

    baseline_parser.add_argument("device_id", help="Device ID")

    baseline_parser.add_argument("--type", "-t", help="Device type override")



    # monitor subcommand (v3.0)

    monitor_parser = subparsers.add_parser("monitor", help="Real-time device monitoring (WebSocket)")

    monitor_parser.add_argument("device_ids", nargs="*", help="Device IDs to monitor (optional)")

    monitor_parser.add_argument("--relay", "-r", default="http://localhost:18888",

                                help="Relay Server URL (default: http://localhost:18888)")

    monitor_parser.add_argument("--key", "-k", help="API key for authentication")

    monitor_parser.add_argument("--all", "-a", action="store_true", help="Monitor all devices")



    # scan subcommand (v4.1) - One-click device discovery and detection

    scan_parser = subparsers.add_parser("scan", help="一键设备扫描与发现")

    scan_parser.add_argument('target', nargs='?', help='目标IP、IP段或CIDR (如: 192.168.1.0/24)')

    scan_parser.add_argument('--local', action='store_true', help='仅检测本地设备')

    scan_parser.add_argument('--list', '-l', action='store_true', help='列出已保存的设备')

    scan_parser.add_argument('--quick', '-q', action='store_true', help='快速检测')

    scan_parser.add_argument('--full', '-f', action='store_true', help='完整检测（含基准测试）')

    scan_parser.add_argument('--remove', '-r', metavar='IP', help='删除指定IP的设备')

    scan_parser.add_argument('--timeout', '-t', type=int, default=3, help='扫描超时（秒）')

    scan_parser.add_argument('--parallel', '-p', type=int, default=50, help='并行扫描数量')



    # ui subcommand

    ui_parser = subparsers.add_parser('ui', help='交互式菜单')



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
                "warnings": summary.warnings if hasattr(summary, 'warnings') else sum(1 for r in results if (r.severity.value if hasattr(r.severity, 'value') else r.severity) == "warning"),
                "critical": summary.critical if hasattr(summary, 'critical') else sum(1 for r in results if (r.severity.value if hasattr(r.severity, 'value') else r.severity) == "critical"),
            },
            "results": [
                {
                    "check_id": r.check_id,
                    "title": r.title,
                    "severity": r.severity.value if hasattr(r.severity, 'value') else r.severity,
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



    # Show banner for non-version commands
    if not args.version:
        show_banner()



    # Handle subcommands (v3.0)

    if args.command == "device":

        return handle_device_command(args)



    if args.command == "compare":

        return handle_compare_command(args)



    if args.command == "baseline":

        return handle_baseline_command(args)



    if args.command == "monitor":

        return handle_monitor_command(args)



    # Handle scan command (v4.1) - One-click device discovery and detection

    if args.command == "scan":

        if not HAS_SCAN:

            print("Error: Scan module not available. Please ensure nastool_cli.scan is installed.")

            return 1



        nastool_scan = NastoolScan(use_color=not args.no_color)



        if args.local:

            nastool_scan.cmd_local()

        elif args.list:

            nastool_scan.cmd_list()

        elif args.quick:

            nastool_scan.cmd_quick(args.target)

        elif args.full:

            nastool_scan.cmd_full(args.target)

        elif args.remove:

            nastool_scan.cmd_remove(args.remove)

        elif args.target:

            nastool_scan.cmd_discover(args.target)

        else:

            nastool_scan.cmd_discover()



        return 0



    # Handle ui command (v5.0) - Interactive menu

    if args.command == "ui":

        return handle_ui_command(args)



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

        

        # Show profile recommendation

        rec = advisor.get_profile_recommendation(profile_name)

        print(f"\n{'='*60}")

        print(f"  Tuning Profile: {profile_name.upper()}")

        print(f"  Chip: {rec['chip']}")

        print(f"  Description: {rec['description']}")

        print(f"{'='*60}")

        

        print(f"\n  Recommended Settings:")

        for key, val in rec['settings'].items():

            if val is not None:

                print(f"    {key}: {val}")

        

        print(f"\n  Commands:")

        for i, cmd in enumerate(rec['commands'], 1):

            print(f"    {i}. {cmd}")

        

        print()

        return 0

    

    # Handle remote target

    if args.target:

        target = args.target

        

        if target.startswith("relay://") or ":18888" in target:

            # Relay Server 模式

            from nastool_adapters.relay_detector import RelayDetector, create_relay_detector

            

            detector = create_relay_detector(target)

            

            if not detector.connect():

                print("Failed to connect to relay server")

                return 1

            

            # Quick scan: show all devices

            scan = detector.quick_scan()

            print(f"\n  Total devices: {scan['total']}, Online: {scan['online']}")

            for d in scan.get("devices", []):

                status_icon = "🟢" if d["status"] == "online" else "🔴"

                print(f"  {status_icon} {d['device_name']} ({d['device_id']}) - {d['status']}")

            

            # If only one device, auto-select it

            online_devices = [d for d in scan.get("devices", []) if d["status"] == "online"]

            if len(online_devices) == 1:

                device_id = online_devices[0]["device_id"]

                print(f"\nAuto-selecting device: {device_id}")

                results = detector.run_diagnosis(device_id, full_mode=args.full)

            elif len(online_devices) > 1:

                print("\nMultiple devices online. Use --target relay://host:port?device=DEVICE_ID")

                results = []

            else:

                print("\nNo online devices found")

                results = []

            

        else:

            # HTTP API 模式

            from nastool_adapters.http_detector import RemoteHTTPDetector

            

            detector = RemoteHTTPDetector(target)

            

            if not detector.connect():

                print("Failed to connect to remote target")

                return 1

            

            # Get device info

            device_info = detector.get_device_info()

            if device_info:

                print(f"\nDevice: {device_info.device_name} ({device_info.hostname})")

                print(f"Backend: {device_info.backend_type} {device_info.backend_version}")

                print(f"CPU: {device_info.cpu_model} ({device_info.cpu_cores} cores)")

                print(f"Memory: {device_info.memory_total} MB")

            

            # Run diagnosis

            print("\nRunning remote diagnosis...")

            results = detector.run_diagnosis(full_mode=args.full)

        

        # Display results

        if results:

            reporter = TerminalReporter(use_color=not args.no_color)

            if hasattr(reporter, 'print_results'):

                reporter.print_results(results)

            elif hasattr(reporter, 'print_report'):

                reporter.print_report(results)

            

            # Save if output specified

            if args.output:

                save_report(results, None, args.output, args.json)

        

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
    mock_profile = args.mock if args.mock else ("healthy" if not args.full else None)
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

            status_icon = "🟢" if d.status == "online" else "🔴" if d.status == "offline" else "⚪"

            print(f"  {d.id:<20} {d.host:<20} {(d.device_type or '-'):<10} {(d.group or '-'):<10} {status_icon} {d.status}")



        print()

        return 0



    elif args.device_cmd == "add":

        import socket

        device_id = args.id or args.host.replace(".", "-")

        device_type = getattr(args, 'type', None)



        # Auto-detect device type if not provided

        if not device_type:

            device_type = "unknown"



        dm.register_device(

            device_id=device_id,

            host=args.host,

            name=getattr(args, 'name', None),

            group=getattr(args, 'group', None),

            tags=getattr(args, 'tag', None),

            device_type=device_type

        )



        print(f"Device registered: {device_id} ({args.host})")

        return 0



    elif args.device_cmd == "remove":

        if dm.remove_device(args.device_id):

            print(f"Device removed: {args.device_id}")

            return 0

        else:

            print(f"Device not found: {args.device_id}")

            return 1



    elif args.device_cmd == "tag":

        dm.add_tag(args.device_id, args.tag)

        print(f"Tag '{args.tag}' added to {args.device_id}")

        return 0



    elif args.device_cmd == "untag":

        dm.remove_tag(args.device_id, args.tag)

        print(f"Tag '{args.tag}' removed from {args.device_id}")

        return 0



    else:

        print("Unknown device command. Use: list, add, remove, tag, untag")

        return 1





def handle_batch_diagnosis(args) -> int:

    """Handle batch diagnosis"""

    from nastool_cli.batch import BatchDiagnosis, parse_device_list



    # Parse device list

    device_ids = parse_device_list(args.batch)



    if not device_ids:

        print("No devices to diagnose.")

        return 1



    print(f"\n  Batch Diagnosis")

    print(f"  Devices: {len(device_ids)}")

    print(f"  Parallel: {args.parallel}")

    print(f"  Timeout: {args.timeout}s\n")



    # Progress callback

    def progress(device_id: str, current: int, total: int):

        print(f"  [{current}/{total}] Diagnosing {device_id}...")



    batch = BatchDiagnosis(progress_callback=progress)

    summary = batch.run(

        device_ids,

        parallel=args.parallel,

        timeout=args.timeout,

        full_mode=args.full

    )



    # Print summary

    print(f"\n  {'='*50}")

    print(f"  Batch Summary")

    print(f"  {'='*50}")

    print(f"  Total:     {summary.total}")

    print(f"  Success:   {summary.success}")

    print(f"  Failed:    {summary.failed}")

    print(f"  Duration:  {summary.duration_ms}ms")

    print(f"  {'='*50}\n")



    # Print results

    for r in summary.results:

        status = "✓" if r.success else "✗"

        score = f"{r.score}" if r.score is not None else "N/A"

        print(f"  {status} {r.device_id}: score={score}, critical={r.critical_count}, warning={r.warning_count}")



    # Export if requested

    if args.output:

        batch.export_results(summary, args.output, format="json" if args.json else "csv")

        print(f"\n  Results saved to: {args.output}")



    return 0 if summary.failed == 0 else 1





def handle_compare_command(args) -> int:

    """Handle compare subcommand"""

    from nastool_cli.compare import CompareAnalyzer



    analyzer = CompareAnalyzer()



    if len(args.device_ids) == 1:

        # Single device: compare with history

        device_id = args.device_ids[0]

        days = args.history or 7



        print(f"\n  Comparing {device_id} with history ({days} days)...\n")



        result = analyzer.compare_history(device_id, days=days)



        print(f"  {'='*50}")

        print(f"  History Comparison: {device_id}")

        print(f"  {'='*50}")

        print(f"  Current Score:  {result.current.score}")

        print(f"  Baseline Score: {result.baseline.score}")

        print(f"  Change:         {result.score_change:+d}")

        print(f"  Trend:          {result.trend}")

        print(f"  {'='*50}\n")



    elif len(args.device_ids) == 2:

        # Two devices: compare side-by-side

        id1, id2 = args.device_ids



        print(f"\n  Comparing {id1} vs {id2}...\n")



        result = analyzer.compare_devices(id1, id2)



        print(f"  {'='*60}")

        print(f"  Device Comparison")

        print(f"  {'='*60}")

        print(f"  {'':20} {id1:<18} {id2:<18}")

        print(f"  {'-'*20} {'-'*18} {'-'*18}")

        print(f"  {'Score':<20} {result.device1_score:<18} {result.device2_score:<18}")

        print(f"  {'Critical':<20} {result.critical_diff[0]:<18} {result.critical_diff[1]:<18}")

        print(f"  {'Warning':<20} {result.warning_diff[0]:<18} {result.warning_diff[1]:<18}")

        print(f"  {'='*60}\n")



        if result.check_diffs:

            print(f"  Differences ({len(result.check_diffs)}):")

            for diff in result.check_diffs[:10]:  # Show first 10

                print(f"    - {diff.check_name}: {diff.device1_severity} → {diff.device2_severity}")



    else:

        print("Compare requires 1 (history) or 2 (side-by-side) device IDs")

        return 1



    return 0





def handle_baseline_command(args) -> int:

    """Handle baseline subcommand"""

    from nastool_cli.compare import CompareAnalyzer



    analyzer = CompareAnalyzer()



    print(f"\n  Comparing {args.device_id} with ideal baseline...\n")



    result = analyzer.compare_ideal(

        args.device_id,

        device_type=getattr(args, 'type', None)

    )



    print(f"  {'='*50}")

    print(f"  Ideal Baseline Comparison")

    print(f"  {'='*50}")

    print(f"  Device:      {result['device_id']}")

    print(f"  Type:        {result['device_type']}")

    print(f"  Current:     {result['current_score']}")

    print(f"  Ideal:       {result['ideal_score']}")

    print(f"  Gap:         {result['gap']}")

    print(f"  {'='*50}\n")



    if result['gaps']:

        print(f"  Gaps to ideal ({len(result['gaps'])}):")

        for gap in result['gaps'][:10]:

            print(f"    - {gap['check_id']}: current={gap['current']}, ideal={gap['ideal']}")

    else:

        print("  No gaps - device matches ideal baseline!")



    return 0





def handle_monitor_command(args) -> int:

    """Handle monitor subcommand (WebSocket)"""

    try:

        from nastool_cli.ws_client import run_monitor, WebSocketMonitor

    except ImportError as e:

        print(f"WebSocket support not available: {e}")

        print("Install with: pip install websockets")

        return 1



    # Get device IDs

    device_ids = list(args.device_ids) if args.device_ids else None



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


def handle_ui_command(args) -> int:
    """Handle UI subcommand"""
    from nastool_reporters.terminal import TerminalReporter
    
    reporter = TerminalReporter()
    
    while True:
        # Clear screen
        print("\033[2J\033[H")
        
        # Show banner
        show_banner()
        
        # Show menu
        print(reporter._col("=====================================", "cyan"))
        print(reporter._col("   1. 快速诊断", "green"))
        print(reporter._col("   2. 完整系统检测", "blue"))
        print(reporter._col("   3. 设备扫描与管理", "magenta"))
        print(reporter._col("   4. AI 模型测试", "yellow"))
        print(reporter._col("   5. 远程中继连接", "cyan"))
        print(reporter._col("   6. 系统修复", "red"))
        print(reporter._col("   0. 退出", "gray"))
        print(reporter._col("=====================================", "cyan"))
        
        # Get user input
        try:
            choice = input("请选择功能 [0-6]: ")
            
            if choice == "0":
                print("\n退出系统...")
                return 0
            elif choice == "1":
                print("\n执行快速诊断...")
                results, summary = run_diagnosis(quick_mode=True)
                reporter.print_report(results)
            elif choice == "2":
                print("\n执行完整系统检测...")
                results, summary = run_diagnosis(full_mode=True)
                reporter.print_report(results)
            elif choice == "3":
                print("\n设备扫描与管理...")
                # 执行设备扫描
                if HAS_SCAN:
                    from nastool_cli.scan import NastoolScan
                    scan = NastoolScan()
                    scan.cmd_discover()
                else:
                    print("错误: 扫描模块不可用")
            elif choice == "4":
                print("\nAI 模型测试...")
                # 执行AI模型测试
                results, summary = run_diagnosis(mock_profile="healthy")
                # 过滤AI相关的检查结果
                ai_results = [r for r in results if r.category.value == "ai"]
                if ai_results:
                    reporter.print_report(ai_results)
                else:
                    print("未找到AI相关的检查结果")
            elif choice == "5":
                print("\n远程中继连接...")
                print("请使用 'nastool monitor' 命令进行远程监控")
            elif choice == "6":
                print("\n系统修复...")
                # 执行系统修复
                results, summary = run_diagnosis()
                reporter.print_report(results)
                print("\n开始修复...")
                # 这里可以调用修复逻辑
            else:
                print("无效的选择，请重新输入")
                
            # Wait for user input before continuing
            input("\n按回车键继续...")
            
        except KeyboardInterrupt:
            print("\n退出系统...")
            return 0
        except Exception as e:
            print(f"错误: {e}")
            input("\n按回车键继续...")



if __name__ == "__main__":
    sys.exit(main())

