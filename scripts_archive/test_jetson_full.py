#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive Jetson test - all check categories"""
import sys
import os
sys.path.insert(0, '/home/nvidia/nastool')

print("=" * 70)
print("Jetson nastool Comprehensive Test")
print("=" * 70)

# Check registry
try:
    from checks.registry import _CHECKS
    print(f"\n[Registry] Total checks: {len(_CHECKS)}")
    
    # Count by category
    from collections import Counter
    cats = Counter()
    for k, v in _CHECKS.items():
        cat = getattr(v, 'category', None)
        cv = cat.value if (cat and hasattr(cat, 'value')) else str(cat) if cat else 'unknown'
        cats[cv] += 1
    print("Categories:")
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")
except Exception as e:
    print(f"[Registry] ERROR: {e}")

# Test System checks
print("\n[System Checks]")
system_checks = ['uptime', 'cpu_usage', 'memory_usage', 'disk_usage', 'load_average']
for name in system_checks:
    try:
        module = __import__(f'checks.system.{name}', fromlist=[''])
        # Find the Check class
        for attr in dir(module):
            if 'Check' in attr and attr.endswith('Check'):
                cls = getattr(module, attr)
                c = cls()
                r = c.run()
                status = "PASS" if r.passed else "FAIL"
                print(f"  {name}: {status} - {r.message[:60] if r.message else 'N/A'}")
                break
    except Exception as e:
        print(f"  {name}: ERROR - {str(e)[:50]}")

# Test Network checks
print("\n[Network Checks]")
network_checks = ['network_interface', 'dns_resolution', 'gateway_reachable']
for name in network_checks:
    try:
        module = __import__(f'checks.network.{name}', fromlist=[''])
        for attr in dir(module):
            if 'Check' in attr and attr.endswith('Check'):
                cls = getattr(module, attr)
                c = cls()
                r = c.run()
                status = "PASS" if r.passed else "FAIL"
                print(f"  {name}: {status} - {r.message[:60] if r.message else 'N/A'}")
                break
    except Exception as e:
        print(f"  {name}: ERROR - {str(e)[:50]}")

# Test Storage checks
print("\n[Storage Checks]")
storage_checks = ['storage_disk', 'inode_check']
for name in storage_checks:
    try:
        module = __import__(f'checks.storage.{name}', fromlist=[''])
        for attr in dir(module):
            if 'Check' in attr and attr.endswith('Check'):
                cls = getattr(module, attr)
                c = cls()
                r = c.run()
                status = "PASS" if r.passed else "FAIL"
                print(f"  {name}: {status} - {r.message[:60] if r.message else 'N/A'}")
                break
    except Exception as e:
        print(f"  {name}: ERROR - {str(e)[:50]}")

# Test NAS checks
print("\n[NAS Checks]")
nas_checks = ['smb_service', 'nfs_service']
for name in nas_checks:
    try:
        module = __import__(f'checks.nas.{name}', fromlist=[''])
        for attr in dir(module):
            if 'Check' in attr and attr.endswith('Check'):
                cls = getattr(module, attr)
                c = cls()
                r = c.run()
                status = "PASS" if r.passed else "FAIL"
                print(f"  {name}: {status} - {r.message[:60] if r.message else 'N/A'}")
                break
    except Exception as e:
        print(f"  {name}: ERROR - {str(e)[:50]}")

# Test Security checks
print("\n[Security Checks]")
security_checks = ['ssh_config', 'firewall_status']
for name in security_checks:
    try:
        module = __import__(f'checks.security.{name}', fromlist=[''])
        for attr in dir(module):
            if 'Check' in attr and attr.endswith('Check'):
                cls = getattr(module, attr)
                c = cls()
                r = c.run()
                status = "PASS" if r.passed else "FAIL"
                print(f"  {name}: {status} - {r.message[:60] if r.message else 'N/A'}")
                break
    except Exception as e:
        print(f"  {name}: ERROR - {str(e)[:50]}")

# Test --list-checks
print("\n[--list-checks Output]")
import subprocess
result = subprocess.run(['python3', '/home/nvidia/nastool/arm_diagnose.py', '--list-checks'], 
                       capture_output=True, text=True, timeout=10)
print(result.stdout[:500] if result.stdout else "No output")
if result.stderr:
    print("ERROR:", result.stderr[:200])

print("\n" + "=" * 70)
print("Test Complete")
print("=" * 70)