"""Fix encoding issues in subprocess.run calls across all check files."""
import os, re

base = r'D:\project\nastool7\nastool-core\nastool_core\checks'
count = 0
fixed_files = []

for root, dirs, files in os.walk(base):
    for fn in files:
        if not fn.endswith('.py'):
            continue
        fp = os.path.join(root, fn)
        try:
            with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            print(f'ERROR reading {fp}: {e}')
            continue

        if 'subprocess.run' not in content:
            continue

        # Skip if already has errors= in subprocess.run calls
        if 'errors=' in content and re.search(r'subprocess\.run[^)]*errors\s*=', content):
            continue

        # Replace text=True with text=True, errors="replace" for subprocess.run
        # Use a more careful regex that handles multiline
        def fix_subprocess(match):
            stmt = match.group(0)
            if 'errors=' in stmt:
                return stmt
            # Add errors="replace" after text=True (or capture_output=True)
            stmt = re.sub(
                r'(text\s*=\s*True)',
                r'\1, errors="replace"',
                stmt
            )
            return stmt

        new_content = re.sub(
            r'subprocess\.run\([^)]+\)',
            fix_subprocess,
            content,
            flags=re.DOTALL
        )

        if new_content != content:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(new_content)
            # Count actual changes
            changes = len(re.findall(r'errors="replace"', new_content))
            fixed_files.append((os.path.relpath(fp, base), changes))
            count += changes

print(f'Total subprocess.run calls patched: {count} in {len(fixed_files)} files:')
for f, n in fixed_files:
    print(f'  [{n}x] {f}')
