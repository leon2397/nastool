"""
Jetson Xavier NX 真机测试 - 旧版 nastool (monolithic) 测试
使用 ~/nastool/arm_diagnose.py 进行真实设备测试
"""
import paramiko
import sys

HOST = "192.168.1.123"
USER = "nvidia"
PASS = "nvidia"

bugs = []
next_id = 15

def record_bug(title, bug_type, priority, phenomenon, expected, actual, steps, reason, fix):
    global next_id
    bug_id = f"BUG-{next_id:03d}"
    next_id += 1
    bugs.append({
        "id": bug_id, "title": title, "type": bug_type, "priority": priority,
        "phenomenon": phenomenon, "expected": expected, "actual": actual,
        "steps": steps, "reason": reason, "fix": fix
    })
    print(f"\n[BUG] {bug_id}: {title}")
    print(f"   Priority={priority} Type={bug_type}")
    print(f"   {phenomenon[:100]}")

def ssh_run(client, cmd, timeout=15):
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        return out, err
    except Exception as e:
        return "", f"SSH_ERR: {e}"

def section(t):
    print("\n" + ("=" * 60))
    print(t)
    print("=" * 60)

def main():
    print("nastool Jetson Real Test - Old Monolithic Version")
    print(f"Target: {USER}@{HOST}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, port=22, username=USER, password=PASS, timeout=10)
        print("SSH connected OK")
    except Exception as e:
        print(f"SSH FAIL: {e}")
        sys.exit(1)

    NASTOOL = "/home/nvidia/nastool"
    PY = "python3"

    # ---- Check old version info ----
    section("T20: Old Version Info")
    out, err = ssh_run(client, f"cd {NASTOOL} && {PY} arm_diagnose.py --version 2>&1")
    print(f"$ arm_diagnose.py --version: {out if out else '(no output)'}")
    if err: print(f"[ERR] {err[:200]}")

    # Check pyproject.toml version
    out, err = ssh_run(client, f"cat {NASTOOL}/pyproject.toml 2>/dev/null | head -10")
    print(out[:300] if out else "(no pyproject.toml)")
    out, err = ssh_run(client, f"cat {NASTOOL}/CHANGELOG.md 2>/dev/null | head -20")
    print(out[:500] if out else "(no CHANGELOG)")

    # ---- T21: --mock healthy ----
    section("T21: arm_diagnose.py --mock healthy")
    out, err = ssh_run(client, f"cd {NASTOOL} && {PY} arm_diagnose.py --mock healthy 2>&1", timeout=60)
    print(out[:3000] if out else "(no output)")
    if err: print(f"[ERR] {err[:500]}")
    if "Traceback" in out:
        record_bug(
            "arm_diagnose.py --mock healthy raises Traceback", "T-A", "P1",
            "Python Traceback when running mock healthy",
            "Should output mock health report",
            out[:500], f"cd {NASTOOL}; python3 arm_diagnose.py --mock healthy",
            "Code has an error that occurs on Jetson",
            "Debug and fix the Traceback"
        )

    # ---- T22: --quick ----
    section("T22: arm_diagnose.py --quick")
    out, err = ssh_run(client, f"cd {NASTOOL} && {PY} arm_diagnose.py --quick 2>&1", timeout=60)
    print(out[:3000] if out else "(no output)")
    if err: print(f"[ERR] {err[:300]}")

    # ---- T23: --full (real device) ----
    section("T23: arm_diagnose.py --full (real device)")
    out, err = ssh_run(client, f"cd {NASTOOL} && {PY} arm_diagnose.py --full 2>&1", timeout=120)
    print(out[:4000] if out else "(no output)")
    if err: print(f"[ERR] {err[:500]}")
    if "Traceback" in out:
        record_bug(
            "arm_diagnose.py --full raises Traceback", "T-A", "P1",
            "Python Traceback when running --full on Jetson",
            "Should complete full diagnosis",
            out[:500], f"cd {NASTOOL}; python3 arm_diagnose.py --full",
            "Code has an error on Jetson real device",
            "Debug and fix the Traceback"
        )

    # ---- T24: GPU check directly ----
    section("T24: GPU Check (Jetson-specific)")
    # Check if there's a GPU check module
    out, err = ssh_run(client, f"ls {NASTOOL}/checks/ai/ 2>/dev/null; ls {NASTOOL}/checks/ 2>/dev/null | head -20")
    print(out if out else "(no checks dir)")
    # Try to run gpu_detected directly
    out, err = ssh_run(client, f"cd {NASTOOL} && {PY} -c \"from checks.ai.gpu_detected import check; print(check())\" 2>&1")
    print(f"GPU check: {out if out else '(no output)'}")
    if err: print(f"[ERR] {err[:300]}")

    # ---- T25: Module import check ----
    section("T25: Module Import Check (old version)")
    imports_to_test = [
        "from checks.system.cpu_info import CpuInfoCheck",
        "from checks.system.memory import MemoryCheck",
        "from checks.storage.disk import DiskCheck",
        "from checks.network.eth0 import Eth0Check",
        "from checks.ai.gpu_detected import check as gpu_check",
    ]
    for imp in imports_to_test:
        out, err = ssh_run(client, f'cd {NASTOOL} && {PY} -c "{imp}; print(\'OK\')" 2>&1')
        status = "[PASS]" if "OK" in out else "[FAIL]"
        print(f"{status} {imp}")
        if "[FAIL]" in status:
            print(f"   {out[:200]}")
            record_bug(
                f"Import failed: {imp}", "T-C", "P2",
                f"Cannot import {imp} on Jetson",
                f"Should import {imp}",
                out[:300], f"cd {NASTOOL}; python3 -c \"{imp}\"",
                "Module may not exist on Jetson or import path differs",
                "Check if module exists and import path"
            )

    # ---- T26: Check registry count ----
    section("T26: check_registry count")
    out, err = ssh_run(client,
        f'cd {NASTOOL} && {PY} -c "from checks import CHECK_REGISTRY; print(\'Total:\', len(CHECK_REGISTRY))" 2>&1',
        timeout=30)
    print(out if out else "(no output)")

    # ---- T27: CUDA check ----
    section("T27: CUDA Version Check")
    out, err = ssh_run(client, f"cd {NASTOOL} && {PY} -c \"from checks.ai.cuda_version import CudaVersionCheck; c = CudaVersionCheck(); r = c.run(); print(r)\" 2>&1")
    print(f"CUDA check: {out if out else '(no output)'}")
    if err: print(f"[ERR] {err[:300]}")

    # ---- T28: Storage check ----
    section("T28: Storage Check")
    out, err = ssh_run(client, f"cd {NASTOOL} && {PY} -c \"from checks.storage.disk import DiskCheck; c = DiskCheck(); r = c.run(); print(r)\" 2>&1")
    print(f"Disk check: {out if out else '(no output)'}")
    if err: print(f"[ERR] {err[:300]}")

    # ---- T29: Report format ----
    section("T29: Report --format json")
    out, err = ssh_run(client, f"cd {NASTOOL} && {PY} arm_diagnose.py --mock healthy --format json 2>&1 | head -30", timeout=30)
    print(out[:2000] if out else "(no output)")

    # ---- T30: Fix check (dry run) ----
    section("T30: Fix capability check")
    out, err = ssh_run(client, f"ls {NASTOOL}/fixes/ 2>/dev/null | head -20; ls {NASTOOL}/fixes/ 2>/dev/null | wc -l")
    print(out if out else "(no fixes dir)")

    # ---- T31: Check Python version compatibility ----
    section("T31: Python 3.8 compatibility")
    out, err = ssh_run(client, f"cd {NASTOOL} && {PY} -c \"import sys; print(sys.version); import ast; print('ast OK')\" 2>&1")
    print(out if out else "(no output)")
    # Check for 3.8-specific issues
    out, err = ssh_run(client, f"cd {NASTOOL} && {PY} -c \"from typing import Literal; print('Literal OK')\" 2>&1")
    print(f"typing.Literal: {out if out else '(no output)'}")

    # ---- Summary ----
    section("Test Summary (Old Version)")
    print(f"Total new bugs found: {len(bugs)}")

    if bugs:
        print("\n--- BUG List ---")
        for b in bugs:
            print(f"\n[{b['id']}] {b['title']}")
            print(f"  Priority={b['priority']} Type={b['type']}")
            print(f"  Fix: {b['fix']}")

    client.close()
    return bugs

if __name__ == "__main__":
    main()
