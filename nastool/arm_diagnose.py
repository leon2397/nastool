# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
arm_diagnose.py - Main entry point for nastool v4.2.0

Usage:
    python3 arm_diagnose.py                    # Quick diagnosis
    python3 arm_diagnose.py --full             # Full diagnosis with benchmarks
    python3 arm_diagnose.py --fix              # Diagnosis + interactive fix
    python3 arm_diagnose.py --output report.json   # Save report
    python3 arm_diagnose.py --monitor          # Start monitoring daemon
    python3 arm_diagnose.py --web              # Start web dashboard
    python3 arm_diagnose.py --register         # Register to NAS backend
    python3 arm_diagnose.py --profile PROFILE  # Use specific device profile
    python3 arm_diagnose.py --version          # Show version
"""

import argparse
import sys
import os
from typing import Optional, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from logger import get_logger
from messages import msg
from checks import run_all_checks, list_available_checks, run_mock_checks, CheckSeverity, CheckResult
from fixes import run_fix, list_available_fixes, FixResult
from fixes.interactive_fix import interactive_fix_flow
from core.version_check import VersionDB
from reporters.terminal import TerminalReporter
from reporters.summary import SummaryReporter
from reporters.health_dashboard import HealthDashboard
from reporters.file_reporter import FileReporter

# v3.0 imports
from profiles.loader import detect_device, get_profile, list_profiles, DeviceProfile

# v3.0.4 imports
from utils.progress import ProgressTracker, CheckStatus
from utils.config_validator import ConfigValidator
from utils.quick_diagnose import quick_diagnose, print_quick_report
from utils.history import HistoryTracker

__version__ = "5.0.4"
logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="nastool v3.0.7 - ARM Device Diagnostic Toolkit for AI-NAS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      Quick diagnosis (auto-detect device)
  %(prog)s --full               Full diagnosis with benchmarks
  %(prog)s --fix                Diagnosis + interactive fix
  %(prog)s --fix --auto         Diagnosis + auto fix (no confirmation)
  %(prog)s --quick              Fast diagnosis (essential checks only)
  %(prog)s --check-config       Validate configuration
  %(prog)s --history            Show health trend
  %(prog)s --monitor            Start real-time monitoring daemon
  %(prog)s --web                Start web dashboard
  %(prog)s --register           Register device to NAS backend
  %(prog)s --profile pi5        Use Raspberry Pi 5 profile
  %(prog)s --output report.json Save report to file
        """,
    )

    # Diagnosis options
    parser.add_argument(
        "--full", action="store_true", help="Run full diagnosis including benchmarks"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Quick diagnosis (essential checks only, ~5 seconds)"
    )
    parser.add_argument(
        "--skip",
        metavar="CATEGORIES",
        help="Skip categories (comma-separated: system,network,storage,ai,security)",
    )
    parser.add_argument(
        "--mock",
        type=str,
        default=None,
        choices=["healthy", "degraded", "critical", "mixed"],
        help="Run with mock data (no real system needed). Profiles: healthy/degraded/critical/mixed",
    )

    # Device profile (v3.0)
    parser.add_argument(
        "--profile",
        metavar="PROFILE_ID",
        help="Use specific device profile (e.g., jetson-xavier-nx, rk3588-orangepi5, pi5)",
    )

    # Fix options
    parser.add_argument(
        "--fix", action="store_true", help="Run fixes after diagnosis (interactive mode)"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-apply all fixes without confirmation (use with --fix)",
    )

    # Registration options
    parser.add_argument(
        "--register", action="store_true", help="Register device to NAS backend after diagnosis"
    )
    parser.add_argument(
        "--nas-host", default=Config.NAS_HOST, help=f"NAS backend host (default: {Config.NAS_HOST})"
    )
    parser.add_argument(
        "--nas-port",
        type=int,
        default=Config.NAS_PORT,
        help=f"NAS backend port (default: {Config.NAS_PORT})",
    )

    # v3.0 features
    parser.add_argument("--monitor", action="store_true", help="Start real-time monitoring daemon")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Monitoring interval in seconds (default: {Config.MONITOR_INTERVAL})",
    )
    parser.add_argument("--web", action="store_true", help="Start web dashboard")
    parser.add_argument(
        "--port", type=int, default=None, help=f"Web dashboard port (default: {Config.WEB_PORT})"
    )

    # Version database
    parser.add_argument(
        "--update-versions", action="store_true", help="Force update version database from online"
    )
    parser.add_argument(
        "--offline", action="store_true", help="Run in offline mode (skip version checks)"
    )

    # v3.0.4 P2 features
    parser.add_argument(
        "--check-config", action="store_true", help="Validate configuration and exit"
    )
    parser.add_argument("--history", action="store_true", help="Show health score trend")
    parser.add_argument(
        "--history-days", type=int, default=7, help="Days to show in history (default: 7)"
    )

    # Info options
    parser.add_argument("--list-checks", action="store_true", help="List all available checks")
    parser.add_argument("--list-fixes", action="store_true", help="List all available fixes")
    parser.add_argument(
        "--list-profiles", action="store_true", help="List all available device profiles"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--version", action="store_true", help="Show version")

    # Output options (v3.0.4)
    parser.add_argument(
        "--output", "-o", metavar="FILE", help="Save diagnostic report to file (JSON or HTML)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "html"],
        default="json",
        help="Output format for --output (default: json)",
    )
    parser.add_argument(
        "--no-progress", action="store_true", help="Disable progress bar (useful for scripts)"
    )

    # Parallel execution (v6.0)
    parser.add_argument(
        "--parallel",
        type=int,
        choices=[0, 1, 2],
        default=None,
        help="Parallel execution level: 0=serial, 1=category parallel, 2=DAG (default: auto)"
    )

    return parser.parse_args()


def print_banner() -> None:
    """Print nastool banner"""
    print()
    print("+=================================================================+")
    print(f"| [*] nastool v{__version__} - ARM NAS Diagnostic Toolkit    |")
    print("+=================================================================+")
    print()


def main() -> int:
    """Main entry point with type hints"""
    args = parse_args()

    # Version
    if args.version:
        print(f"nastool {__version__}")
        return 0

    # List profiles (v3.0)
    if args.list_profiles:
        print("Available Device Profiles:")
        print()
        profiles = list_profiles()
        for p in sorted(profiles):
            profile = get_profile(p)
            if profile:
                print(f"  {p}")
                print(f"    Name: {profile.name}")
                print(f"    Vendor: {profile.vendor}")
                print(f"    Category: {profile.category}")
                print()
        return 0

    # List checks
    if args.list_checks:
        print("Available Checks:")
        print()
        checks_dict = list_available_checks()
        # Convert dict to list
        checks = list(checks_dict.values())
        by_category: dict = {}
        for check in checks:
            cat = check.get("category", "other")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(check)

        for category in sorted(by_category.keys()):
            print(f"  [{category.upper()}]")
            for check in by_category[category]:
                print(f"    - {check['id']}: {check['description']}")
            print()
        return 0

    # List fixes
    if args.list_fixes:
        print("Available Fixes:")
        print()
        fixes = list_available_fixes()
        for fix in fixes.values():
            print(f"  - {fix['id']}")
            print(f"    Description: {fix['description']}")
            print(f"    Risk: {fix['risk']}")
            print()
        return 0

    # Check config (v3.0.4 P2)
    if args.check_config:
        print_banner()
        print("🔍 Validating configuration...")
        print()

        validator = ConfigValidator()
        validator.validate_all()
        validator.print_report()

        return 0 if validator.is_valid() else 1

    # Show history (v3.0.4 P2)
    if args.history:
        tracker = HistoryTracker()
        tracker.print_trend(args.history_days)
        return 0

    # Start monitoring daemon (v3.0)
    if args.monitor:
        print_banner()
        interval = args.interval or Config.MONITOR_INTERVAL
        logger.info(msg("monitor.start", interval=interval))
        print(f"  Press Ctrl+C to stop")
        print()

        from daemon import run_daemon

        run_daemon(interval=interval)
        return 0

    # Start web dashboard (v3.0)
    if args.web:
        print_banner()
        port = args.port or Config.WEB_PORT
        logger.info(msg("web.start", url=Config.web_url()))
        print(f"  API docs: http://{Config.WEB_HOST}:{port}/docs")
        print()

        import uvicorn
        from api import app

        uvicorn.run(app, host=Config.WEB_HOST, port=port)
        return 0

    # Update version database
    if args.update_versions:
        print_banner()
        logger.info("Updating version database...")
        db = VersionDB()
        db.update_from_online()
        logger.info("Version database updated successfully")
        return 0

    # Run diagnosis
    print_banner()

    # Load device profile (v3.0)
    profile: Optional[DeviceProfile] = None
    if args.profile:
        profile = get_profile(args.profile)
        if not profile:
            logger.error(msg("device.profile_not_found", profile=args.profile))
            print(f"   Available: {', '.join(list_profiles())}")
            return 1
        logger.info(msg("device.profile_loaded", profile=profile.id))
    else:
        profile = detect_device()
        logger.info(msg("device.detected", name=profile.name, profile=profile.id))
    print()

    # Quick diagnosis mode (v3.0.4 P2)
    if args.quick:
        print("🚀 Quick diagnosis mode...")
        print()

        quick_result = quick_diagnose(offline=args.offline)
        print_quick_report(quick_result)

        # Record to history
        history_tracker = HistoryTracker()
        history_tracker.record(
            score=quick_result.score,
            results=quick_result.details,
            status=quick_result.status,
            profile=profile.id if profile else None,
        )

        # Show comparison
        history_tracker.print_comparison(quick_result.score)

        return 0 if quick_result.status == "healthy" else 1

    # Run checks with progress tracking (v3.0.4)
    use_progress = not args.no_progress and sys.stdout.isatty()

    skip_cats = args.skip.split(",") if args.skip else []

    if use_progress:
        # Get total check count for progress bar
        checks_dict = list_available_checks()
        # Convert dict to list
        available_checks = list(checks_dict.values())
        if skip_cats:
            available_checks = [c for c in available_checks if c.get("category") not in skip_cats]
        total_checks = len(available_checks)

        tracker = ProgressTracker(total=total_checks, desc="Running diagnostics")
        tracker.start()

        # Run checks and update progress
        results: List[CheckResult] = []
        for check_info in available_checks:
            check_id = check_info["id"]
            category = check_info.get("category", "other")

            try:
                # Run single check
                from checks import run_check

                result = run_check(check_id, full=args.full, offline=args.offline)
                results.append(result)

                # Update progress
                status = {
                    CheckSeverity.PASSED: CheckStatus.OK,
                    CheckSeverity.WARNING: CheckStatus.WARNING,
                    CheckSeverity.CRITICAL: CheckStatus.CRITICAL,
                    CheckSeverity.INFO: CheckStatus.OK,
                }.get(result.severity, CheckStatus.OK)

                tracker.update(
                    check_id, status, result.message[:30] if result.message else "", category
                )
            except Exception as e:
                logger.error(f"Check {check_id} failed: {e}")
                results.append(
                    CheckResult(
                        id=check_id,
                        category=category,
                        severity=CheckSeverity.CRITICAL,
                        message=f"Check failed: {e}",
                    )
                )
                tracker.update(check_id, CheckStatus.CRITICAL, str(e)[:30], category)

        # Calculate score (v4.0.2 weighted system)
        from checks.base import CheckSummary
        _summary = CheckSummary()
        for r in results:
            _summary.add_result(r)
        report = _summary.get_health_report()
        score = report.overall_score
        tracker.finish(score=score)
    else:
        # Legacy mode without progress bar
        print("🔍 Running diagnostics...")
        print()

        # Mock mode — use pre-defined mock data (no real system required)
        if args.mock:
            from data.mock_results import PROFILE_DESCRIPTIONS
            profile_desc = PROFILE_DESCRIPTIONS.get(args.mock, args.mock)
            print(f"📦 Mock mode: {args.mock} — {profile_desc}")
            print()
            results = run_mock_checks(profile=args.mock)
            score = results.score
        elif args.parallel is not None:
            # Parallel execution mode (v6.0)
            from core.executor import CheckExecutor
            plevel = args.parallel
            plevel_names = {0: "serial", 1: "category parallel", 2: "DAG parallel"}
            print(f"⚡ Parallel mode: level {plevel} ({plevel_names.get(plevel, '?')})")
            print()
            executor = CheckExecutor(
                adapter=None, parallel_level=plevel, early_exit=False
            )
            summary_exec = executor.run_all()
            # Convert executor summary to legacy format
            results = summary_exec
            score = results.score

            # Show timing info in verbose mode
            if args.verbose:
                timings = executor.get_timings()
                slow = sorted(timings.items(), key=lambda x: x[1].duration_ms, reverse=True)
                print("⏱  Top 10 slowest checks:")
                for cid, t in slow[:10]:
                    print(f"   {cid}: {t.duration_ms:.0f}ms")
                print()
        else:
            results: List[CheckResult] = run_all_checks(
                skip_categories=skip_cats
            )
            score = results.score

        # Print results
        reporter = TerminalReporter()
        # Use CheckSummary to print results
        from checks.base import CheckSummary
        summary = CheckSummary(
            total=len(results.results),
            passed=sum(1 for r in results.results if r.passed),
            warnings=sum(1 for r in results.results if not r.passed and r.severity.value == "warning"),
            critical=sum(1 for r in results.results if not r.passed and r.severity.value == "critical"),
            results=results.results
        )
        reporter.print_summary(summary)

        # Summary with Health Dashboard (v4.0.2)
        # results is CheckSummary, use its results attribute
        results_list = results.results
        dashboard = HealthDashboard()
        dashboard.print_dashboard(results)
        score = results.score

    # Save report if requested (v3.0.4)
    if args.output:
        print()
        file_reporter = FileReporter(
            device_info={
                "profile": profile.id if profile else "unknown",
                "name": profile.name if profile else "Unknown Device",
            }
        )

        output_format = args.format
        if args.output.endswith(".html"):
            output_format = "html"
        elif args.output.endswith(".json"):
            output_format = "json"

        try:
            report_data = results.results if hasattr(results, 'results') else results
            saved_path = file_reporter.save_report(report_data, args.output, format=output_format)
            print(f"📄 Report saved to: {saved_path}")
            logger.info(f"Report saved to {saved_path}")
        except Exception as e:
            print(f"�?Failed to save report: {e}")
            logger.error(f"Failed to save report: {e}")

    # Record to history (v3.0.4 P2)
    history_tracker = HistoryTracker()

    # Determine status
    if score >= 90:
        status = "healthy"
    elif score >= 50:
        status = "degraded"
    else:
        status = "critical"

    history_tracker.record(
        score=score, results=results.results, status=status, profile=profile.id if profile else None
    )

    # Show comparison with last run
    history_tracker.print_comparison(score)

    # Print results if not using progress bar
    if not use_progress:
        reporter = TerminalReporter()
        reporter.print_summary(summary)

    # Run fixes if requested — 智能推议模式 (v5.1.0)
    if args.fix:
        interactive_fix_flow(results.results, auto=args.auto)

    # Register to NAS backend if requested
    if args.register:
        print()
        nas_host = args.nas_host or Config.NAS_HOST
        nas_port = args.nas_port or Config.NAS_PORT
        print(f"📡 Registering to NAS backend ({nas_host}:{nas_port})...")
        logger.info(f"Registering device to NAS backend at {nas_host}:{nas_port}")

        from nas_integration.client import NASClient

        client = NASClient(host=nas_host, port=nas_port)
        try:
            reg_result = client.register_device(
                device_info={"profile": profile.id, "checks": len(results.results), "score": score}
            )
            if reg_result.get("success"):
                print("�?Device registered successfully")
                logger.info("Device registered successfully")
            else:
                error_msg = reg_result.get("error", "Unknown error")
                print(f"�?Registration failed: {error_msg}")
                logger.error(f"Registration failed: {error_msg}")
        except Exception as e:
            print(f"�?Registration failed: {e}")
            logger.error(f"Registration failed: {e}", exc_info=True)

    # Return exit code based on score
    if score >= 90:
        return 0
    elif score >= 50:
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
