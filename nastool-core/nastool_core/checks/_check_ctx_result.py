#!/usr/bin/env python3
"""Dry run - check which files have ctx.result("""
import os, re

count = 0
for dp, dns, fns in os.walk('.'):
    dns[:] = [d for d in dns if d not in ('__pycache__', '.ruff_cache', '.git', '.pytest_cache')]
    for fn in fns:
        if not fn.endswith('.py') or fn in ('decorators.py', '__init__.py'):
            continue
        fp = os.path.join(dp, fn)
        with open(fp, encoding='utf-8') as f:
            if 'ctx.result(' in f.read():
                print(f'HAS ctx.result: {fp}')
                count += 1
print(f'\nTotal: {count} files need migration')
