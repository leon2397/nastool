# -*- coding: utf-8 -*-
"""Fix relative imports in nastool-common/utils/*.py"""
import os
import re

BASE = r"C:\tools416\nastool-common\nastool_common\utils"

fixes = [
    (r'from \.config import', 'from nastool_common.config import'),
    (r'from \.logger import', 'from nastool_common.logger import'),
    (r'from \.messages import', 'from nastool_common.messages import'),
    (r'from \.exceptions import', 'from nastool_common.exceptions import'),
    (r'from \.progress import', 'from nastool_common.utils.progress import'),
]

count = 0
for f in os.listdir(BASE):
    if not f.endswith('.py'):
        continue
    path = os.path.join(BASE, f)
    try:
        with open(path, encoding='utf-8') as fp:
            content = fp.read()
    except:
        continue
    
    new_content = content
    changed = False
    for pattern, replacement in fixes:
        if re.search(pattern, new_content, re.MULTILINE):
            new_content = re.sub(pattern, replacement, new_content, flags=re.MULTILINE)
            changed = True
    
    if changed:
        with open(path, 'w', encoding='utf-8') as fp:
            fp.write(new_content)
        print(f"Fixed: {f}")
        count += 1

print(f"\nFixed {count} files")
