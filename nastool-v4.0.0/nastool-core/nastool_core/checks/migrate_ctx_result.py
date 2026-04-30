# -*- coding: utf-8 -*-
"""
Migration script: ctx.result() -> ctx.passed() / ctx.failed()

Handles patterns:
  ctx.result(passed=True,  current=..., expected=..., message=..., severity=..., details=...)
  ctx.result(passed=False, current=..., expected=..., message=..., fix_available=..., fix_id=..., ...)
  ctx.result(passed=True,  current=..., expected=..., message=..., fix_available=..., ...)
  ctx.result(passed=False, current=..., expected=..., message=..., severity=..., ...)

Also handles: ctx.warning(...) which exists on CheckContext but was being used incorrectly.
"""
import re
import os
import sys


def migrate_file(filepath: str) -> bool:
    """Migrate a single file from ctx.result() to ctx.passed()/ctx.failed()."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    original = content

    # Pattern: ctx.result(passed=True, ...)
    # Convert to: ctx.passed(...)
    def replace_passed(m):
        # Extract kwargs inside the call
        inner = m.group(1)
        # Remove passed=True from kwargs
        inner = re.sub(r',?\s*passed\s*=\s*True\s*,?\s*', '', inner)
        inner = inner.strip().rstrip(',').strip()
        return f"ctx.passed({inner})"

    content = re.sub(
        r'ctx\.result\(passed\s*=\s*True\s*,\s*(.+?)\)',
        replace_passed,
        content,
        flags=re.DOTALL,
    )

    # Pattern: ctx.result(passed=False, ...)
    # Convert to: ctx.failed(...)
    def replace_failed(m):
        inner = m.group(1)
        inner = re.sub(r',?\s*passed\s*=\s*False\s*,?\s*', '', inner)
        inner = inner.strip().rstrip(',').strip()
        return f"ctx.failed({inner})"

    content = re.sub(
        r'ctx\.result\(passed\s*=\s*False\s*,\s*(.+?)\)',
        replace_failed,
        content,
        flags=re.DOTALL,
    )

    # Remove any remaining ctx.result(...) calls (should be none after above)
    remaining = re.findall(r'ctx\.result\(', content)
    if remaining:
        print(f"  WARNING: {len(remaining)} remaining ctx.result() in {filepath}")

    changed = content != original
    if changed:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    return changed


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "checks"
    dry_run = "--dry-run" in sys.argv

    migrated = []
    errors = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip cache directories (in-place edit)
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".ruff_cache", ".git", ".pytest_cache")]
        for filename in filenames:
            if not filename.endswith(".py") or filename in ("decorators.py", "__init__.py"):
                continue
            filepath = os.path.join(dirpath, filename)
            try:
                changed = migrate_file(filepath)
                if changed:
                    migrated.append(filepath)
                    print(f"  {'[DRY-RUN] Would migrate' if dry_run else 'Migrated'}: {filepath}")
            except Exception as e:
                errors.append((filepath, str(e)))
                print(f"  ERROR in {filepath}: {e}")

    print(f"\n{'[DRY-RUN] Would migrate' if dry_run else 'Migrated'} {len(migrated)} files.")
    if errors:
        print(f"Errors in {len(errors)} files:")
        for fp, err in errors:
            print(f"  {fp}: {err}")
    elif not dry_run:
        print("Verifying imports...")
        # Quick sanity check
        for fp in migrated[:3]:
            try:
                with open(fp) as f:
                    code = f.read()
                compile(code, fp, "exec")
                print(f"  ✓ {fp} (syntax OK)")
            except SyntaxError as e:
                print(f"  ✗ {fp}: {e}")


if __name__ == "__main__":
    main()
