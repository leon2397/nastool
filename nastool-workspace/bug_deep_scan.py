"""bug_deep_scan.py - Deep scan for 3 bugs across entire nastool project"""
import os
import re
from pathlib import Path

BASE = Path(r"C:\tools416")

# Skip dirs
SKIP = {"__pycache__", ".egg-info", "node_modules", ".git", "dist", "build"}

print("=" * 80)
print("BUG Deep Scan - Full Project")
print("=" * 80)

# ─── BUG-012: Bare except ─────────────────────────────
print("\n### BUG-012: Bare `except:` (静默吞异常) ###\n")

bare_excepts = []
for py_file in BASE.rglob("*.py"):
    if any(s in str(py_file) for s in SKIP):
        continue
    # Skip v4.0.0 backup copies
    rel = str(py_file.relative_to(BASE))
    try:
        with open(py_file, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                # Match bare except: but NOT "except Exception" or "except ValueError" etc.
                if re.match(r"^except\s*:\s*$", stripped):
                    bare_excepts.append((rel, i, stripped))
                # Also match "except: pass" on same line
                elif re.match(r"^except\s*:\s*pass\s*$", stripped):
                    bare_excepts.append((rel, i, stripped))
    except:
        pass

if bare_excepts:
    for rel, lineno, line in bare_excepts:
        print(f"  {rel}:L{lineno}: {line}")
    print(f"\n  Total: {len(bare_excepts)} bare except statements")
else:
    print("  None found")

# ─── BUG-009: Duplicate @classmethod ──────────────────
print("\n### BUG-009: Duplicate @classmethod ###\n")

dup_classmethods = []
for py_file in BASE.rglob("*.py"):
    if any(s in str(py_file) for s in SKIP):
        continue
    rel = str(py_file.relative_to(BASE))
    try:
        with open(py_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            for i in range(len(lines) - 1):
                if lines[i].strip() == "@classmethod" and lines[i+1].strip() == "@classmethod":
                    # Get the method name on line i+2
                    method = lines[i+2].strip() if i+2 < len(lines) else "?"
                    dup_classmethods.append((rel, i+1, method))
    except:
        pass

if dup_classmethods:
    for rel, lineno, method in dup_classmethods:
        print(f"  {rel}:L{lineno}: double @classmethod -> {method}")
    print(f"\n  Total: {len(dup_classmethods)} duplicate @classmethod")
else:
    print("  None found")

# ─── BUG-008: FixResult duplicate definitions ─────────
print("\n### BUG-008: FixResult duplicate definitions ###\n")

fixresult_defs = []
for py_file in BASE.rglob("*.py"):
    if any(s in str(py_file) for s in SKIP):
        continue
    rel = str(py_file.relative_to(BASE))
    try:
        with open(py_file, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                if re.match(r"^\s*class\s+FixResult\s*[:\(]", line):
                    fixresult_defs.append((rel, i, line.strip()))
    except:
        pass

if fixresult_defs:
    for rel, lineno, line in fixresult_defs:
        print(f"  {rel}:L{lineno}: {line}")
    print(f"\n  Total: {len(fixresult_defs)} FixResult definitions")
else:
    print("  None found")

# ─── Extra: Search for mock fallback patterns ─────────
print("\n### Extra: Mock fallback patterns (except 后直接 return mock) ###\n")

mock_patterns = []
for py_file in BASE.rglob("*.py"):
    if any(s in str(py_file) for s in SKIP):
        continue
    rel = str(py_file.relative_to(BASE))
    try:
        with open(py_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            # Pattern: except: ... return mock / return MockResults
            matches = re.finditer(r"except.*?:\s*\n(.*?)return\s+.*[Mm]ock", content, re.DOTALL)
            for m in matches:
                start_line = content[:m.start()].count('\n') + 1
                mock_patterns.append((rel, start_line, m.group()[:100]))
    except:
        pass

if mock_patterns:
    for rel, lineno, snippet in mock_patterns[:10]:
        print(f"  {rel}:L{lineno}: {snippet}...")
    print(f"\n  Total: {len(mock_patterns)} mock-fallback patterns")
else:
    print("  None found")

# ─── Extra: Search for "mock" in except blocks ───────
print("\n### Extra: except blocks containing 'mock' ###\n")

except_mock = []
for py_file in BASE.rglob("*.py"):
    if any(s in str(py_file) for s in SKIP):
        continue
    rel = str(py_file.relative_to(BASE))
    try:
        with open(py_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            in_except = False
            except_start = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if re.match(r"except\s", stripped):
                    in_except = True
                    except_start = i + 1
                elif in_except:
                    if 'mock' in stripped.lower() or 'Mock' in stripped:
                        except_mock.append((rel, except_start, stripped[:80]))
                    if not stripped.startswith((' ', '\t')) and stripped and not stripped.startswith('#'):
                        in_except = False
    except:
        pass

if except_mock:
    for rel, lineno, line in except_mock[:15]:
        print(f"  {rel}:L{lineno}: {line}")
    print(f"\n  Total: {len(except_mock)} except->mock patterns")
else:
    print("  None found")

print("\n" + "=" * 80)
print("Scan Complete")
print("=" * 80)
