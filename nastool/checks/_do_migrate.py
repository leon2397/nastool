#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch migrate ctx.result(passed=X, ...) → ctx.passed/failed"""
import re, os, sys

SCRIPT_NAME = '_do_migrate.py'
SKIP_FILES = {'decorators.py', '__init__.py', SCRIPT_NAME, '_check_ctx_result.py',
              'migrate_ctx.py', 'migrate_ctx_result.py'}

def do_migrate(fp):
    with open(fp, encoding='utf-8') as f:
        content = f.read()
    orig = content

    def rp(m):
        inner = m.group(1)
        inner = re.sub(r'passed\s*=\s*True\s*,\s*', '', inner).rstrip(',').strip()
        return f'ctx.passed({inner})'

    def rf(m):
        inner = m.group(1)
        inner = re.sub(r'passed\s*=\s*False\s*,\s*', '', inner).rstrip(',').strip()
        return f'ctx.failed({inner})'

    content = re.sub(r'ctx\.result\(passed\s*=\s*True\s*,\s*(.+?)\)', rp, content, flags=re.DOTALL)
    content = re.sub(r'ctx\.result\(passed\s*=\s*False\s*,\s*(.+?)\)', rf, content, flags=re.DOTALL)

    rem = re.findall(r'ctx\.result\(', content)
    if rem:
        print(f'  !! {len(rem)} remaining in {fp}')

    if content != orig:
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    dry = '--dry' in sys.argv

    migrated = []
    errors = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in ('__pycache__', '.ruff_cache', '.git', '.pytest_cache')]
        for fn in fns:
            if not fn.endswith('.py') or fn in SKIP_FILES:
                continue
            fp = os.path.join(dp, fn)
            try:
                with open(fp, encoding='utf-8') as f:
                    raw = f.read()
                has = 'ctx.result(' in raw
                if dry:
                    if has:
                        print(f'[DRY] {fp}')
                else:
                    if has:
                        ok = do_migrate(fp)
                        if ok:
                            migrated.append(fp)
                            print(f'  migrate: {fp}')
            except Exception as e:
                errors.append((fp, e))

    print(f'\n{"[DRY] Would migrate" if dry else "Migrated"} {len(migrated)} files')
    if errors:
        for fp, e in errors:
            print(f'  ERROR {fp}: {e}')

if __name__ == '__main__':
    main()
