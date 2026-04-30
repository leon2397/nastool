# NASTool - NAS System Diagnostic Tool

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A comprehensive diagnostic tool for ARM-based NAS systems.

## Features

- **90+ Health Checks**: System, network, storage, AI acceleration, security
- **Interactive Repair**: Auto-fix common issues with `--fix`
- **Multiple Output Formats**: Terminal, text file, JSON
- **Mock Mode**: Test with simulated data (`--mock healthy`)

## Installation

```bash
pip install nastool
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
```

## Uninstallation

```bash
pip uninstall nastool
```

This will remove all nastool components cleanly.

## Documentation

See [GitHub Wiki](https://github.com/nastool/nastool/wiki) for detailed documentation.

## License

MIT License - see LICENSE file for details.
