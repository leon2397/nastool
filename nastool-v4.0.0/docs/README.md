# NASTool v4.0 文档

> 统一文档入口

---

## 快速开始

### 安装

```bash
# 从源码安装
cd nastool-v4.0.0
pip install -e nastool-common
pip install -e nastool-core
pip install -e nastool-adapters
pip install -e nastool-reporters
pip install -e nastool-fixes
pip install -e nastool-cli

# 安装Rich（可选，用于美化输出）
pip install rich
```

### 5分钟上手

```bash
# 快速诊断
nastool

# 完整诊断
nastool diagnose --full

# 查看设备
nastool device list

# 批量检测
nastool diagnose --batch @devices.txt
```

---

## 命令参考

### 诊断命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `nastool` | 快速诊断 | `nastool` |
| `nastool diagnose` | 诊断（可带参数） | `nastool diagnose --full --parallel 20` |
| `nastool diagnose --mock` | Mock模式 | `nastool diagnose --mock healthy` |

**参数：**
- `--full`: 完整模式（含基准测试）
- `--parallel N`: 并发数（v4.0）
- `--mock PROFILE`: Mock模式
- `--json`: JSON输出
- `--no-color`: 无颜色

### 设备管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `nastool device list` | 列出设备 | `nastool device list --group prod` |
| `nastool device add` | 添加设备 | `nastool device add 192.168.1.100 --group prod` |
| `nastool device remove` | 移除设备 | `nastool device remove device-01` |
| `nastool device tag` | 添加标签 | `nastool device tag device-01 --tag rk3588` |

---

## v4.0 新特性

### 1. 性能优化

- **检测并行化**：单设备检测速度提升 4.2x
- **批量并行**：多设备并行检测，提升 2.1x
- **内存优化**：流式处理，内存占用减少 50%

### 2. 代码重构

- **模块化CLI**：main.py 从 4330 行精简到 77 行
- **命令注册器**：动态命令发现，易于扩展

### 3. 用户体验

- **Rich输出**：表格、进度条、彩色面板
- **实时进度**：检测进度实时显示
- **友好错误**：错误码 + 修复建议

### 4. 质量提升

- **超时控制**：所有IO操作可配置超时
- **优雅降级**：单点失败不影响整体
- **资源管理**：自动释放句柄，防止泄漏

---

## API 文档

### Python SDK

```python
from nastool_core import run_checks_parallel, CHECK_TIMEOUTS

# 并行检测
results = run_checks_parallel(
    check_ids=["network_latency", "cpu_temperature"],
    max_concurrent=10,
    timeouts=CHECK_TIMEOUTS
)

# 批量设备检测
from nastool_core.batch_parallel import batch_diagnose_parallel

results = batch_diagnose_parallel(
    device_ids=["device1", "device2"],
    check_ids=["network_latency"],
    max_concurrent_devices=5
)
```

---

## 常见问题

**Q: v4.0 与 v3.0 有什么区别？**
A: v4.0 专注优化，无功能增加，性能提升 2-4x。

**Q: 如何启用 Rich 美化输出？**
A: `pip install rich`，自动启用。

**Q: 检测超时如何配置？**
A: 修改 `nastool_core/check_timeouts.py`。

---

_文档版本: v4.0.0_
