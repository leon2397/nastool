"""
Jetson Xavier NX 真机测试脚本
连接 192.168.1.123 / nvidia/nvidia
目的：全面测试 nastool v4.0.0 在真实 Jetson 设备上的表现
原则：只记录 BUG，不修复
"""
import paramiko
import sys
import time

HOST = "192.168.1.123"
USER = "nvidia"
PASS = "nvidia"
PORT = 22

bugs = []
next_id = 8  # 已有 BUG 001-007

def record_bug(title, bug_type, priority, phenomenon, expected, actual, steps, reason, fix):
    global next_id
    bug_id = f"BUG-{next_id:03d}"
    next_id += 1
    bugs.append({
        "id": bug_id, "title": title, "type": bug_type, "priority": priority,
        "phenomenon": phenomenon, "expected": expected, "actual": actual,
        "steps": steps, "reason": reason, "fix": fix
    })
    print(f"\n[BUG RECORDED] {bug_id}: {title}")
    print(f"   Type={bug_type} Priority={priority}")
    print(f"   Phenomenon: {phenomenon[:100]}")
    return bug_id

def ssh_run(client, cmd, timeout=15):
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        return out, err
    except Exception as e:
        return "", f"SSH_ERR: {e}"

def section(title):
    print("\n" + ("=" * 60))
    print(title)
    print("=" * 60)

def main():
    print("nastool v4.0.0 Jetson Real Device Test")
    print(f"Target: {USER}@{HOST}")

    print("\n>> Connecting to Jetson...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=10)
        print("OK: SSH connected")
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    # ---- T1: System Info ----
    section("T1: System Info")
    out, err = ssh_run(client, "uname -a; cat /etc/os-release | head -5; hostname; uptime")
    print(out)
    if err: print(f"[ERR] {err[:200]}")

    # ---- T2: Python Environment ----
    section("T2: Python Environment")
    out, err = ssh_run(client, "python3 --version; which python3; pip3 list 2>/dev/null | grep -i nastool || echo 'nastool_not_in_pip'")
    print(out)

    # ---- T3: nastool Installation ----
    section("T3: nastool Installation Location")
    out, err = ssh_run(client, "ls ~/nastool 2>/dev/null || echo 'NOT_IN_HOME'; find /home /opt /usr/local -name 'arm_diagnose.py' 2>/dev/null | head -5")
    print(out)
    out, err = ssh_run(client, "which nastool 2>/dev/null || echo 'NOT_IN_PATH'")
    print(out)

    # ---- T4: Module Import Tests ----
    section("T4: nastool Module Imports")
    test_imports = [
        "import nastool_core",
        "import nastool_cli",
        "import nastool_adapters",
        "import nastool_reporters",
        "import nastool_fixes",
        "import nastool_common",
        "from nastool_core.checks import check_registry",
    ]
    for imp in test_imports:
        out, err = ssh_run(client, f'python3 -c "{imp}; print(\'OK\')" 2>&1')
        status = "[PASS]" if "OK" in out else "[FAIL]"
        print(f"{status} {imp}")
        if "[FAIL]" in status:
            print(f"   {out[:300]}")
            record_bug(
                f"Module import failed: {imp}", "T-C", "P1",
                f"python3 -c \"{imp}\" failed",
                f"Should import {imp} successfully",
                out[:300], f"python3 -c \"{imp}\"",
                "Module not installed or missing dependency on Jetson",
                "Install nastool-v4.0.0 modules on Jetson"
            )

    # ---- T5: check_registry Stats ----
    section("T5: check_registry Stats")
    out, err = ssh_run(client,
        'python3 -c "from nastool_core.checks import check_registry; '
        'checks = check_registry.get_all_checks(); '
        'print(\'Total:\', len(checks)); '
        'cats = {}\''.encode() + b" + b'; "
        b'for c in checks: cats[c.category.value] = cats.get(c.category.value, 0) + 1; '
        b'for k,v in sorted(cats.items()): print(k, v)" 2>&1',
        timeout=30)
    print(out[:2000] if out else "(no output)")

    # ---- T6: --version ----
    section("T6: nastool --version")
    for cmd in ["nastool --version", "python3 -m nastool_cli --version"]:
        out, err = ssh_run(client, cmd)
        print(f"$ {cmd} -> {out if out else '(no output)'}")

    # ---- T7: --mock healthy ----
    section("T7: nastool --mock healthy")
    out, err = ssh_run(client, "nastool --mock healthy 2>&1", timeout=60)
    print(out[:3000] if out else "(no output)")
    if err: print(f"[ERR] {err[:300]}")
    if ("error" in out.lower() and "Error" not in out) or "Traceback" in out:
        record_bug(
            "nastool --mock healthy execution failed", "T-A", "P1",
            "--mock healthy exited with error",
            "mock healthy should pass",
            (out + err)[:500], "nastool --mock healthy",
            "Mock mode fails on Jetson",
            "Check nastool_cli/main.py mock logic"
        )

    # ---- T8: --full (30s timeout) ----
    section("T8: nastool --full (30s timeout)")
    out, err = ssh_run(client, "timeout 30 nastool --full 2>&1", timeout=35)
    print(out[:3000] if out else "(no output)")
    if err: print(f"[ERR] {err[:300]}")

    # ---- T9: GPU Detection (Jetson-specific) ----
    section("T9: GPU Detection (Jetson-specific)")
    out, err = ssh_run(client,
        "ls /dev/nvhost* 2>/dev/null | head -10; "
        "nvidia-smi 2>&1 | head -20; "
        "ls /proc/driver/nvidia/ 2>/dev/null; "
        "cat /proc/driver/nvidia/params 2>/dev/null | head -3")
    print(out if out else "(no GPU paths found)")
    if not out or "No such" in out or "not found" in out:
        record_bug(
            "Jetson GPU detection path missing", "T-C", "P1",
            "/dev/nvhost* and nvidia-smi both missing on Jetson",
            "Should detect Jetson GPU (CUDA 11.4)",
            out[:300], "ls /dev/nvhost*; nvidia-smi",
            "Jetson uses special GPU paths not covered by nvidia-smi",
            "Add Jetson-specific GPU detection in gpu_detected check"
        )

    # ---- T10: CUDA Detection ----
    section("T10: CUDA Detection")
    out, err = ssh_run(client,
        "nvcc --version 2>&1; "
        "echo PATH_CUDA; echo $PATH | tr ':' '\\n' | grep -i cuda; "
        "ls /usr/local/cuda*/bin/nvcc 2>/dev/null | head -3")
    print(out if out else "(no CUDA)")

    # ---- T11: Storage Detection ----
    section("T11: Storage Detection")
    out, err = ssh_run(client,
        "df -h; echo '---BLOCK---'; lsblk -o NAME,SIZE,TYPE 2>/dev/null | head -15; "
        "echo '---MOUNT---'; mount 2>/dev/null | grep -E 'mmc|nvme|sd' | head -10")
    print(out[:2000] if out else "(no output)")

    # ---- T12: Network Detection ----
    section("T12: Network Detection")
    out, err = ssh_run(client,
        "ip addr | grep -E 'inet |state' | head -10; "
        "ethtool eth0 2>/dev/null | head -5; "
        "ping -c 1 -W 2 8.8.8.8 2>&1 | head -3")
    print(out[:1000] if out else "(no output)")

    # ---- T13: Memory/Temperature ----
    section("T13: Memory/Temperature")
    out, err = ssh_run(client,
        "free -h; echo '---TEMP---'; "
        "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -5; "
        "sensors 2>/dev/null | head -10")
    print(out[:1500] if out else "(no output)")

    # ---- T14: JetPack/L4T Version ----
    section("T14: JetPack/L4T Version")
    out, err = ssh_run(client,
        "cat /etc/nv_tegra_release 2>/dev/null || echo 'NOT_FOUND'; "
        "head -5 /etc/nv_tegra_release 2>/dev/null; "
        "cat /etc/os-release | grep -i 'tegra\\|l4t' | head -5")
    print(out if out else "(no JetPack info)")
    if not out or "NOT_FOUND" in out:
        record_bug(
            "JetPack version detection file missing", "T-C", "P2",
            "/etc/nv_tegra_release not found on Jetson",
            "Jetson should have JetPack version info",
            out[:200], "cat /etc/nv_tegra_release",
            "Jetson-specific file, version detection not covered",
            "Add JetPack detection adapter"
        )

    # ---- T15: SSH Adapter Self-test ----
    section("T15: SSH Adapter Self-test")
    out, err = ssh_run(client,
        'python3 -c "from nastool_adapters import SSHAdapter; print(\'SSHAdapter OK\'); s = SSHAdapter(\'localhost\', \'nvidia\', \'nvidia\'); print(\'Created\')" 2>&1')
    print(out if out else "(no output)")
    if err and "Error" in err: print(f"[ERR] {err[:200]}")

    # ---- T16: Report Format ----
    section("T16: Report Format Test (--format json)")
    out, err = ssh_run(client, "nastool --mock healthy --format json 2>&1 | head -30", timeout=30)
    print(out[:2000] if out else "(no output)")

    # ---- T17: Parallel Detection ----
    section("T17: Parallel Detection --parallel 4")
    out, err = ssh_run(client, "timeout 20 nastool --mock healthy --parallel 4 2>&1", timeout=25)
    print(out[:2000] if out else "(no output)")

    # ---- T18: Error Handling ----
    section("T18: Error Handling (invalid target)")
    out, err = ssh_run(client, "nastool --target ssh://invalid:9999 2>&1 | head -20", timeout=15)
    print(out[:1000] if out else "(no output)")

    # ---- T19: nastool version consistency ----
    section("T19: Version Consistency Check")
    out, err = ssh_run(client,
        'python3 -c "from nastool_core import __version__; print(__version__)" 2>&1; '
        'python3 -c "from nastool_cli import __version__; print(__version__)" 2>&1; '
        'python3 -c "from nastool_common import __version__; print(__version__)" 2>&1')
    print(out if out else "(no output)")

    # ---- Summary ----
    section("Test Summary")
    print(f"Total new bugs found: {len(bugs)}")
    print(f"Total tests: 19")

    if bugs:
        print("\n--- BUG List ---")
        for b in bugs:
            bid = b["id"]
            title = b["title"]
            ptype = b["priority"]
            phen = b["phenomenon"][:100]
            fix = b["fix"]
            print(f"\n[{bid}] {title}")
            print(f"  Priority={ptype}")
            print(f"  Phenomenon: {phen}")
            print(f"  Fix: {fix}")

    # Save to local file
    report = f"""# Jetson Xavier NX 真机测试报告 - {time.strftime('%Y-%m-%d %H:%M')}

## 测试概要
- 设备: Jetson Xavier NX (192.168.1.123)
- 用户: nvidia
- 版本: nastool v4.0.0
- 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
- 测试项目: 19 项
- 新发现 BUG: {len(bugs)} 个

## BUG 汇总

"""
    for b in bugs:
        bid = b["id"]
        title = b["title"]
        btype = b["type"]
        prio = b["priority"]
        phen = b["phenomenon"]
        exp = b["expected"]
        act = b["actual"]
        steps = b["steps"]
        reason = b["reason"]
        fix = b["fix"]
        report += f"""### {bid}: {title}
- **Type:** {btype}
- **Priority:** {prio}
- **现象:** {phen}
- **预期行为:** {exp}
- **实际行为:** {act}
- **复现步骤:** {steps}
- **判定理由:** {reason}
- **修复建议:** {fix}

"""
    # Write report locally
    try:
        with open(r"D:\project\nastool7\docs_archive\TEST_BUGS_Jetson_v4.md", "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport saved to D:\\project\\nastool7\\docs_archive\\TEST_BUGS_Jetson_v4.md")
    except Exception as e:
        print(f"\nFailed to save report: {e}")

    client.close()

if __name__ == "__main__":
    main()
