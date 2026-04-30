# NASTool v1.0.0 - Quick Start Guide

## Installation

### Windows
```cmd
install.bat
```

### Linux/macOS
```bash
./install.sh
```

### Manual (any OS)
```bash
python install.py
```

## Quick Start

```bash
# Quick diagnosis (90 checks, ~3 seconds)
nastool

# Full diagnosis with benchmarks (93 checks)
nastool --full

# Interactive repair mode
nastool --fix

# Auto-fix without confirmation
nastool --fix-auto

# Save report to file
nastool --output report.txt
nastool --json report.json

# Disable colors (Windows CMD friendly)
nastool --no-color

# Demo mode with mock data
nastool --mock healthy
```

## Uninstallation

```bash
pip uninstall nastool
```

This removes all components cleanly.

## Requirements

- Python 3.8 or higher
- pip

## Support

- GitHub: https://github.com/nastool/nastool
- Issues: https://github.com/nastool/nastool/issues

## License

MIT License
