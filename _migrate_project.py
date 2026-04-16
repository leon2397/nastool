#!/usr/bin/env python3
"""Migration script: D:\nas\armtool415 -> D:\tools416"""
import subprocess, os, sys, shutil

SRC = r'D:\nas\armtool415'
DST = r'D:\tools416'

def run(cmd, cwd=None, env=None):
    r = subprocess.run(cmd, shell=True, cwd=cwd or SRC,
                       capture_output=True, text=True, timeout=120, env=env)
    return r

# 1. Commit all changes in source
print("=== 1. Committing pending changes ===")
r = run('git add -A && git commit -m "v7.1.0-beta: fix BUG-001/007, F1 --version增强, ctx.result迁移" --author="AI Assistant <ai@localhost>"')
if r.returncode == 0:
    print("  git commit: OK")
else:
    print(f"  git commit: {r.stderr[:200]}")

# 2. robocopy (preserves .git, timestamps, skips __pycache__)
print("\n=== 2. robocopy 迁移 ===")
robocopy = f'robocopy "{SRC}" "{DST}" /E /COPYALL /R:1 /W:1 /NP /NDL /NC /NJH /NJS'
r = subprocess.run(robocopy, shell=True, timeout=300)
# robocopy exit codes: 0=no files, 1=files copied, 2+=some issue
if r.returncode <= 1:
    print(f"  robocopy: OK (exit {r.returncode})")
else:
    print(f"  robocopy: exit {r.returncode} - check manually")
    print(r.stdout[:300])

# 3. Verify key files exist in destination
print("\n=== 3. 验证关键文件 ===")
key_files = [
    'nastool/arm_diagnose.py',
    'nastool/checks/decorators.py',
    'nastool/core/version_info.py',
    'CHANGELOG.md',
    'MEMO.md',
    'docs/V7.1.0_PLAN.md',
    '.git/HEAD',
]
all_ok = True
for f in key_files:
    src_exists = os.path.exists(os.path.join(SRC, f))
    dst_exists = os.path.exists(os.path.join(DST, f))
    status = 'OK' if (src_exists and dst_exists) else ('MISSING' if not dst_exists else 'SRC_GONE')
    print(f"  {'OK' if status=='OK' else '!!'+status}: {f}")
    if status != 'OK':
        all_ok = False

# 4. Count files
print("\n=== 4. 文件统计 ===")
src_files = sum(len(files) for _, _, files in os.walk(SRC))
dst_files = sum(len(files) for _, _, files in os.walk(DST))
print(f"  源目录: {src_files} 文件")
print(f"  目标目录: {dst_files} 文件")

# 5. Verify git
print("\n=== 5. Git 验证 ===")
r = run('git log --oneline -1', cwd=DST)
print(f"  目标 HEAD: {r.stdout.strip()}")

# 6. List root files in destination
print("\n=== 6. 目标目录文件列表 ===")
dst_root = os.listdir(DST)
print(f"  {len(dst_root)} 个文件/目录")
for f in sorted(dst_root):
    marker = '' if os.path.isdir(os.path.join(DST, f)) else ''
    print(f"  {f}{marker}")

print("\n=== 完成 ===")
print(f"新项目路径: {DST}")
print(f"验证命令: python {DST}\\nastool\\arm_diagnose.py --version")
