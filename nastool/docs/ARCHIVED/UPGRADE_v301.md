# nastool v3.0.1 升级计划

> 🍓 质量优化版本 - 不新增功能，专注代码质量提升

## ✅ 已完成 (2026-04-12)

### P0 任务完成

| 任务 | 状态 | 文件 |
|------|------|------|
| 配置化改造 | ✅ 完成 | config.py (6291 bytes) |
| 日志系统重构 | ✅ 完成 | logger.py (3523 bytes) |
| 错误信息国际化 | ✅ 完成 | messages.py (7165 bytes) |
| 语法错误修复 | ✅ 完成 | core/storage.py |
| 文档更新 | ✅ 完成 | README.md, ROADMAP.md, docs/API.md |

### 文件变更

**新增文件：**
- `config.py` - 统一配置管理，环境变量支持
- `logger.py` - 日志系统，可配置级别
- `messages.py` - 消息国际化（EN/ZH）
- `docs/API.md` - API 文档

**修改文件：**
- `api/__init__.py` - 使用 Config 和 logger
- `daemon/__init__.py` - 使用 Config 和 logger
- `arm_diagnose.py` - 使用新模块
- `core/storage.py` - 修复语法错误
- `pyproject.toml` - 版本号 3.0.1
- `CHANGELOG.md` - v3.0.1 变更日志
- `README.md` - 更新到 v3.0.1
- `ROADMAP.md` - 更新路线图

---

## 版本定位

**原则**：零新功能，纯质量优化，为 v3.1 打好基础

---

## 升级目标

| 目标 | 当前状态 | v3.0.1 目标 | 结果 |
|------|----------|-------------|------|
| 硬编码IP | 25处 | 0处 | ✅ 移至 config.py |
| 硬编码路径 | 6处 | 0处 | ✅ 移至 config.py |
| 日志系统 | print输出 | logging模块 | ✅ logger.py |
| 错误信息 | 混合中英文 | 统一格式 | ✅ messages.py |
| 文档完整性 | README/CHANGELOG | + API文档 | ✅ docs/API.md |

---

## 升级任务清单

### P0 - 必须完成（影响可维护性）

#### 1. 配置化改造

**问题**：25处硬编码IP，6处硬编码路径

**解决方案**：
- 创建 `config.py` 统一管理配置
- 支持环境变量覆盖
- 支持 `config.yaml` 配置文件

```python
# config.py 示例
import os
from pathlib import Path

class Config:
    # NAS 后端配置
    NAS_HOST = os.getenv("NASTOOL_NAS_HOST", "120.77.249.3")
    NAS_PORT = int(os.getenv("NASTOOL_NAS_PORT", "8000"))
    
    # 路径配置
    DEFAULT_SCAN_PATH = Path(os.getenv("NASTOOL_SCAN_PATH", "/nas"))
    
    # Web Dashboard
    WEB_HOST = os.getenv("NASTOOL_WEB_HOST", "0.0.0.0")
    WEB_PORT = int(os.getenv("NASTOOL_WEB_PORT", "8080"))
    
    # 监控配置
    MONITOR_INTERVAL = int(os.getenv("NASTOOL_MONITOR_INTERVAL", "60"))
```

**工作量**：2小时
**文件影响**：
- `checks/network/*.py` (4处IP)
- `api/__init__.py` (2处IP)
- `daemon/__init__.py` (1处IP)
- `nas_integration/client.py` (2处IP)
- `arm_diagnose.py` (默认值)

---

#### 2. 日志系统重构

**问题**：大量 `print()` 语句，难以控制日志级别和格式

**解决方案**：
- 引入 `logging` 模块
- 支持日志级别配置
- 统一日志格式

```python
# logger.py 示例
import logging
import sys

def setup_logger(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("nastool")
    logger.setLevel(getattr(logging, level.upper()))
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
```

**工作量**：3小时
**文件影响**：所有 `.py` 文件

---

#### 3. 错误信息国际化

**问题**：错误信息混合中英文

**解决方案**：
- 错误信息统一英文
- 用户界面保留中文（Web Dashboard）
- 创建 `messages.py` 统一管理

```python
# messages.py
MESSAGES = {
    "en": {
        "check.passed": "✅ {check_id}: Passed",
        "check.failed": "❌ {check_id}: Failed - {message}",
        "check.warning": "⚠️ {check_id}: Warning - {message}",
        "fix.applied": "✅ Fix applied: {fix_id}",
        "fix.failed": "❌ Fix failed: {fix_id} - {error}",
        "device.detected": "Detected device: {name}",
        "device.unknown": "Unknown device, using generic profile",
    },
    "zh": {
        "check.passed": "✅ {check_id}: 通过",
        "check.failed": "❌ {check_id}: 失败 - {message}",
        "check.warning": "⚠️ {check_id}: 警告 - {message}",
    }
}
```

**工作量**：2小时
**文件影响**：所有 `.py` 文件

---

### P1 - 建议完成（提升代码质量）

#### 4. 测试覆盖扩展

**当前状态**：4个测试文件

**扩展目标**：
- `tests/test_config.py` - 配置加载测试
- `tests/test_profiles.py` - 设备配置测试
- `tests/test_api.py` - API端点测试
- `tests/test_daemon.py` - 守护进程测试

**工作量**：4小时

---

#### 5. API 文档完善

**当前状态**：有 OpenAPI 自动文档

**补充内容**：
- 创建 `docs/API.md` 手册
- 添加请求/响应示例
- 添加错误码说明

**工作量**：1小时

---

#### 6. 类型注解清理

**当前状态**：覆盖率298%（统计异常，可能重复计算）

**优化目标**：
- 检查并修复错误的类型注解
- 添加缺失的返回类型
- 使用 `typing` 模块最佳实践

**工作量**：2小时

---

### P2 - 可选完成（锦上添花）

#### 7. 性能优化

- 异步检查（asyncio）
- 并行执行检查
- 缓存检查结果

**工作量**：3小时

---

#### 8. 代码风格统一

- 使用 `black` 格式化
- 使用 `isort` 整理导入
- 使用 `mypy` 类型检查

**工作量**：1小时

---

## 文件变更清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `config.py` | 统一配置管理 |
| `logger.py` | 日志系统 |
| `messages.py` | 错误信息国际化 |
| `docs/API.md` | API文档 |
| `tests/test_config.py` | 配置测试 |
| `tests/test_profiles.py` | 设备配置测试 |

### 修改文件

| 文件 | 变更内容 |
|------|----------|
| `arm_diagnose.py` | 使用config/logging/messages |
| `checks/**/*.py` | 替换硬编码为config |
| `api/__init__.py` | 使用config/logging |
| `daemon/__init__.py` | 使用config/logging |
| `nas_integration/client.py` | 使用config |
| `reporters/terminal.py` | 使用messages |

---

## 时间估算

| 优先级 | 任务 | 工时 |
|--------|------|------|
| P0 | 配置化改造 | 2h |
| P0 | 日志系统重构 | 3h |
| P0 | 错误信息国际化 | 2h |
| P1 | 测试覆盖扩展 | 4h |
| P1 | API文档完善 | 1h |
| P1 | 类型注解清理 | 2h |
| P2 | 性能优化 | 3h |
| P2 | 代码风格统一 | 1h |

**P0总计**：7小时
**P1总计**：7小时
**全部总计**：18小时

---

## 发布检查清单

- [ ] 所有硬编码IP移到 `config.py`
- [ ] 所有硬编码路径移到 `config.py`
- [ ] 所有 `print()` 替换为 `logger`
- [ ] 所有错误信息使用 `messages.py`
- [ ] 新增测试全部通过
- [ ] `docs/API.md` 完成
- [ ] CHANGELOG 更新
- [ ] README 更新配置说明
- [ ] 版本号更新为 3.0.1

---

## 不做的事

以下内容**不在 v3.0.1 范围**，留待后续版本：

- ❌ 新增检查项
- ❌ 新增修复脚本
- ❌ 新增设备配置
- ❌ 新增Web功能
- ❌ 新增API端点
- ❌ 性能大幅优化
- ❌ UI/UX改动

---

## 升级收益

### 对开发者

- 更易维护（配置集中管理）
- 更易调试（日志系统）
- 更易扩展（清晰架构）

### 对用户

- 配置更灵活（环境变量/配置文件）
- 日志更清晰（级别可控）
- 错误更易理解（统一格式）

### 对项目

- 代码质量提升
- 测试覆盖增加
- 文档更完善

---

*计划日期：2026-04-12*
*预计完成：v3.0.1 发布*
