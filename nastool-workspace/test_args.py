#!/usr/bin/env python3
import argparse

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
""")

# Main modes
mode_group = parser.add_mutually_exclusive_group()
mode_group.add_argument("--version", action="store_true", help="Show version")
mode_group.add_argument("--full", action="store_true", help="Full diagnosis with benchmarks")
mode_group.add_argument("--fix", action="store_true", help="Diagnosis + interactive fix")
mode_group.add_argument("--fix-auto", action="store_true", help="Diagnosis + auto fix (no confirm)")
mode_group.add_argument("--list-fixes", action="store_true", help="List all available fixes")
mode_group.add_argument("--mock", metavar="PROFILE", help="Use mock data with specified profile")

args = parser.parse_args()
print(f"args.full: {args.full}")
print(f"args.mock: {args.mock}")

# Default to mock healthy if no mode specified
mock_profile = args.mock if args.mock else ("healthy" if not args.full else None)
print(f"mock_profile: {mock_profile}")
