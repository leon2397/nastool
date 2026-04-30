#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch migrate: ctx.result(passed=X, ...) -> ctx.passed(...)/ctx.failed(...)"""
import re, os, sys

def migrate(filepath):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    orig = content

    # ctx.result(passed=True, ...) -> ctx.passed(...)
    def repl_passed(m):
        inner = m.group(1)
        inner = re.sub(r'passed\s*=\s*True\s*,\s*', '', inner)
        inner = inner.rstrip(',').strip()
        return f'ctx.passed({inner})'

    content = re.sub(r'ctx\.result\(passed\s*=\s*True\s*,\s*(.+?)\)',
                     repl_passed, content, flags=re.DOTALL)

    # ctx.result(passed=False, ...) -> ctx.failed(...)
    def repl_failed(m):
        inner = m.group(1)
        inner = re.sub(r'passed\s*=\s*False\s*,\s*', '', inner)
        inner = inner.rstrip(',').strip()
        return f'ctx.failed({inner})'

    content = re.sub(r'ctx\.result\(passed\s*=\s*False\s*,\s*(.+?)\)',
                     repl_failed, content, flags=re.DOTALL)

    # Any remaining ctx.result( -> report
    rem = re.findall(r'ctx\.result\(', content)
    if rem:
        print(f'  !! {len(rem)} remaining in {filepath}')

    if content != orig:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

root = sys.argv[1] if len(sys.argv) > 1 else '.'
dry = '--dry' in sys.argv

migrated = []
for dp, dns, fns in os.walk(root):
    dns[:] = [d for d in dns if d not in ('__pycache__', '.ruff_cache', '.git', '.pytest_cache')]
    for fn in fns:
        if not fn.endswith('.py') or fn in ('decorators.py', '__init__.py',
                                              os.path.basename(__file__)):
            continue
        fp = os.path.join(dp, fn)
        if dry:
            with open(fp, encoding='utf-8') as f:
                if 'ctx.result(' in f.read():
                    print(f'[DRY] {fp}')
        else:
            try:
                if migrate(fp):
                    migrated.append(fp)
                    print(f'  ✓ {fp}')
            except Exception as e:
                print(f'  ✗ {fp}: {e}')

print(f'\n{"[DRY] Would migrate" if dry else "Migrated"} {len(migrated)} files.')
