#!/usr/bin/env python3
import subprocess

print("Testing memory detection...")

# Test free -m command
print("\n1. Running 'free -m':")
r = subprocess.run("free -m", shell=True, capture_output=True, text=True, errors="replace", timeout=5)
print("Output:")
print(r.stdout)
print("Stderr:")
print(r.stderr)

# Parse output
lines = r.stdout.strip().split("\n")
print("\n2. Parsing output:")
if len(lines) > 1:
    print(f"Line 1: {lines[1]}")
    parts = lines[1].split()
    print(f"Parts: {parts}")
    if len(parts) >= 2:
        total_mb = float(parts[1])
        total_gb = total_mb / 1024
        print(f"Total memory: {total_mb} MB = {total_gb:.1f} GB")
else:
    print("No memory info found")
