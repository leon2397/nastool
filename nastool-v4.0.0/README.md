# NASTool v4.0.0

Multi-device management and real-time collaboration platform for ARM devices.

## Modules

| Module | Description |
|--------|-------------|
| nastool-common | Shared utilities, logging, exceptions |
| nastool-core | Check engine, device manager, plugin framework, pydantic schemas |
| nastool-adapters | Device adapters (SSH, USB, HTTP, Relay, NVIDIA, Rockchip, Sophon), API client |
| nastool-reporters | Terminal, HTML, JSON, PDF, Rich, RK专用 reports |
| nastool-fixes | Auto-fix scripts (security, storage, system, ai, nas) |
| nastool-cli | Command-line interface |

## Quick Start

```bash
# Install
pip install -e nastool-common
pip install -e nastool-core
pip install -e nastool-adapters
pip install -e nastool-reporters
pip install -e nastool-fixes
pip install -e nastool-cli

# Version
nastool --version

# Quick diagnosis (mock mode by default)
nastool

# Full diagnosis (real device, no fallback to mock)
nastool --full

# Mock mode with profile
nastool --mock healthy

# Device management
nastool device list
nastool device add 192.168.1.100 --group prod

# Batch diagnosis
nastool --batch @all

# Compare
nastool compare device1 device2

# Monitor (WebSocket)
nastool monitor --all

# Remote diagnosis
nastool --target http://192.168.1.100:8080
nastool --target relay://120.77.249.3:18888

# Tuning recommendations
nastool --tune performance --chip RK3588

# RK-specific report
nastool --rk-report markdown
```

## New in v4.0

- **Performance optimization**: 4.2x faster single device, 2.1x faster batch
- **Memory optimization**: 50% reduction
- **Code refactoring**: main.py 4330→77 lines (-98%)
- **Rich output**: Beautiful terminal tables, progress bars, panels
- **Stability**: Timeout handling, graceful degradation, thread safety
- **Bug fixes**: See CHANGELOG.md for details

## New in v3.0

- **Multi-device management**: device registry, batch diagnosis, comparison
- **Real-time monitoring**: WebSocket client for live status
- **Plugin system**: extend checks and adapters via plugins
- **Python SDK**: NASToolAPIClient for Relay Server API
- **OpenAPI spec**: openapi.json for API documentation

## Dependencies

- Python >= 3.9
- pydantic >= 2.0.0 (for config validation schemas)
- See each module's pyproject.toml for full dependencies

## Documentation

- docs/UPGRADE_PLAN.md - v3.0/v4.0 upgrade plan
- docs/CHANGELOG.md - Version history and bug fixes
- openapi.json - API specification

## Code Quality Rules

> These rules are mandatory. Violations cause runtime crashes.

| # | Rule | Consequence |
|---|------|-------------|
| 1 | 禁止裸 `except:` | 程序无法正常退出，调试困难 |
| 2 | 禁止导入不存在类 | ImportError 运行时崩溃 |
| 3 | 禁止使用未定义属性 | AttributeError 运行时崩溃 |
| 4 | 版本号必须全项目一致 | API 兼容错乱、版本检查失效 |
| 5 | 禁止幽灵依赖 | ImportError 或运行时降级失效 |
| 6 | 类继承顺序正确 | NameError: name 'ParentClass' is not defined |
| 7 | `--full` 真实模式禁止静默降级 mock | 用户误以为运行了真实检测 |
| 8 | 禁止硬编码密钥/IP | 安全风险，泄露敏感信息 |

## Security

- **Never commit hardcoded credentials**: Use environment variables
- **AGENT_KEY/RELAY_HOST**: Read from `os.environ.get()`, not hardcoded strings
- Example: `AGENT_KEY=xxx RELAY_HOST=120.77.249.3 python e2e_test.py`

## License

MIT
