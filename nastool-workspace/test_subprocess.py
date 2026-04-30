#!/usr/bin/env python3
import subprocess
result = subprocess.run(["python3", "--version"], capture_output=True, text=True)
print("stdout:", repr(result.stdout))
print("stderr:", repr(result.stderr))
version_str = result.stdout.strip() or result.stderr.strip()
print("version_str:", repr(version_str))

import re
match = re.search(r'Python (\d+)\.(\d+)\.(\d+)', version_str)
if match:
    print("matched:", match.group(1), match.group(2), match.group(3))
