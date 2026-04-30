#!/usr/bin/env python3
import os

bashrc = os.path.expanduser('~/.bashrc')
with open(bashrc, 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'nastool PATH' in line:
        skip = True
        continue
    if skip and line.startswith('export PATH=') and ('.local/bin' in line or 'cuda/bin' in line):
        continue
    if skip and line.strip() == '':
        continue
    skip = False
    new_lines.append(line)

with open(bashrc, 'w') as f:
    f.writelines(new_lines)

with open(bashrc, 'a') as f:
    f.write('\n# nastool PATH\n')
    f.write('export PATH=$HOME/.local/bin:$PATH\n')
    f.write('export PATH=/usr/local/cuda/bin:$PATH\n')

print('Done')
