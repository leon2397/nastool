"""p1_bug_deep_scan.py - P1 BUG deep scan across ALL nastool directories"""
import os
import re
from pathlib import Path

# Scan both source dirs and versioned dirs
BASES = [
    Path(r"C:\tools416\nastool-adapters"),
    Path(r"C:\tools416\nastool-core"),
    Path(r"C:\tools416\nastool-fixes"),
    Path(r"C:\tools416\nastool-cli"),
    Path(r"C:\tools416\nastool-reporters"),
    Path(r"C:\tools416\nastool-common"),
]
SKIP = {"__pycache__", ".egg-info", "node_modules", ".git", "dist", "build"}

print("=" * 80)
print("P1 BUG Deep Scan - All Modules")
print("=" * 80)

all_py = []
for base in BASES:
    if base.exists():
        for f in base.rglob("*.py"):
            if not any(s in str(f) for s in SKIP):
                all_py.append(f)

# ─── BUG-001: AdapterReport import ─────────────────────
print("\n### BUG-001: AdapterReport references ###\n")
for f in all_py:
    try:
        with open(f, "r", encoding="utf-8", errors="replace") as fp:
            for i, line in enumerate(fp, 1):
                if "AdapterReport" in line and not line.strip().startswith("#"):
                    rel = str(f.relative_to(f.parents[2]))
                    print(f"  {rel}:L{i}: {line.strip()}")
    except:
        pass

# ─── BUG-007: NASBackend/NASConfig/NASBackendType ───────
print("\n### BUG-007: NASBackend/NASConfig/NASBackendType references ###\n")
for f in all_py:
    try:
        with open(f, "r", encoding="utf-8", errors="replace") as fp:
            for i, line in enumerate(fp, 1):
                if ("NASBackend" in line or "NASConfig" in line or "NASBackendType" in line) and not line.strip().startswith("#"):
                    rel = str(f.relative_to(f.parents[2]))
                    print(f"  {rel}:L{i}: {line.strip()}")
    except:
        pass

# ─── BUG-002: health_check signatures ──────────────────
print("\n### BUG-002: All health_check definitions ###\n")
for f in all_py:
    try:
        with open(f, "r", encoding="utf-8", errors="replace") as fp:
            for i, line in enumerate(fp, 1):
                if "def health_check" in line:
                    rel = str(f.relative_to(f.parents[2]))
                    print(f"  {rel}:L{i}: {line.strip()}")
    except:
        pass

# ─── Extra: AdapterResult usage (correct replacement) ──
print("\n### Extra: AdapterResult usage (should replace AdapterReport) ###\n")
for f in all_py:
    try:
        with open(f, "r", encoding="utf-8", errors="replace") as fp:
            for i, line in enumerate(fp, 1):
                if "AdapterResult" in line and "import" in line:
                    rel = str(f.relative_to(f.parents[2]))
                    print(f"  {rel}:L{i}: {line.strip()}")
    except:
        pass

# ─── Extra: Other non-existent imports from base.py ────
print("\n### Extra: All imports from base.py across adapters ###\n")
base_exports = set()
base_file = Path(r"C:\tools416\nastool-adapters\nastool_adapters\base.py")
if base_file.exists():
    with open(base_file, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            m = re.match(r"^class\s+(\w+)", line)
            if m:
                base_exports.add(m.group(1))
    print(f"  base.py exports: {sorted(base_exports)}")
    print()

for f in all_py:
    if "base.py" in str(f):
        continue
    try:
        with open(f, "r", encoding="utf-8", errors="replace") as fp:
            for i, line in enumerate(fp, 1):
                m = re.match(r"from\s+\.base\s+import\s+(.*)", line.strip())
                if m:
                    imports = [x.strip() for x in m.group(1).split(",")]
                    missing = [x for x in imports if x not in base_exports and x not in ("",)]
                    if missing:
                        rel = str(f.relative_to(f.parents[2]))
                        print(f"  {rel}:L{i}: MISSING {missing}")
    except:
        pass

print("\n" + "=" * 80)
print("Scan Complete")
print("=" * 80)
