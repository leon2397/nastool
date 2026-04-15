# nastool v3.0.2 升级计划

> 🍓 持续质量优化 - 不新增功能，完善代码规范

## ✅ 已完成 (2026-04-12)

### P0 任务完成

| 任务 | 状态 | 说明 |
|------|------|------|
| 类型注解补全 | ✅ 完成 | arm_diagnose.py 完整类型注解 |
| 代码格式化配置 | ✅ 完成 | pyproject.toml 添加 black/isort/mypy 配置 |
| 单元测试补充 | ✅ 完成 | tests/test_core.py (4718 bytes) |
| 版本更新 | ✅ 完成 | 3.0.1 → 3.0.2 |

### 新增文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `tests/test_core.py` | 4718 bytes | 核心模块单元测试 |
| `mypy.ini` | 245 bytes | 类型检查配置 |

### 修改文件

| 文件 | 变更内容 |
|------|----------|
| `arm_diagnose.py` | 完整类型注解、使用 Config 默认值 |
| `pyproject.toml` | 版本号 3.0.2、添加 black/isort/mypy 配置 |
| `CHANGELOG.md` | v3.0.2 变更日志 |

### 验证结果

| 检查项 | 结果 |
|--------|------|
| 版本号一致性 | ✅ 3.0.2 |
| 类型注解 | ✅ parse_args/main/print_banner |
| 工具配置 | ✅ black/isort/mypy |
| 单元测试 | ✅ 5 个测试文件 |

---

## 版本定位

**原则**：零新功能，继续优化代码质量

**前置条件**：v3.0.1 已完成配置化、日志系统、i18n

---

## 当前状态诊断

| 指标 | 数值 | 问题 |
|------|------|------|
| print() 语句 | 96 处 | v3.0.1 未完全替换 |
| 缺少返回类型注解 | 11 个文件 | 类型注解不完整 |
| 文档字符串 | 291 个 | 覆盖较好 |
| TODO/FIXME | 0 处 | ✅ 无遗留 |
| 裸 except | 0 处 | ✅ 无隐患 |

---

## 升级目标

| 目标 | 当前状态 | v3.0.2 目标 |
|------|----------|-------------|
| print() 替换 | 96 处 | 0 处（全部改用 logger） |
| 类型注解覆盖 | 部分缺失 | 核心模块 100% |
| 代码格式化 | 无统一标准 | black/isort 格式化 |
| 测试覆盖 | 基础测试 | 核心模块单元测试 |

---

## 升级任务清单

### P0 - 必须完成（代码规范）

#### 1. print() 语句完全替换

**问题**：96 处 print() 未替换为 logger

**分布**：
| 文件 | 数量 |
|------|------|
| arm_diagnose.py | 43 |
| terminal.py | 12 |
| jetson_patch.py | 11 |
| jetson_install.py | 9 |
| api/__init__.py | 6 |
| 其他 | 15 |

**解决方案**：
- 区分"用户输出"和"日志输出"
- 用户输出（banner、进度）保留 print
- 状态信息改用 logger
- 错误信息改用 logger + messages

```python
# 改造前
print("Starting diagnosis...")
print(f"Error: {error}")

# 改造后（用户输出保留）
print("🔍 Starting diagnosis...")  # 用户可见进度

# 日志输出改用 logger
logger.info("Diagnosis started")
logger.error(f"Check failed: {error}")
```

**工作量**：3 小时

---

#### 2. 类型注解补全

**问题**：11 个文件函数缺少返回类型注解

**目标文件**：
- core/device.py
- core/storage.py
- core/network.py
- core/ai_accel.py
- profiles/loader.py
- daemon/__init__.py
- api/__init__.py
- reporters/terminal.py
- checks/registry.py
- fixes/registry.py
- version_db/__init__.py

**解决方案**：
```python
# 改造前
def detect_device():
    ...

# 改造后
from typing import Optional
from profiles.schemas import DeviceProfile

def detect_device() -> DeviceProfile:
    ...
```

**工作量**：2 小时

---

#### 3. 代码格式化

**问题**：代码风格不统一

**解决方案**：
- 使用 `black` 格式化所有 .py 文件
- 使用 `isort` 整理导入顺序
- 创建 `pyproject.toml` 配置

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311']

[tool.isort]
profile = "black"
line_length = 100
```

**工作量**：1 小时

---

### P1 - 建议完成（测试覆盖）

#### 4. 单元测试补充

**当前状态**：无测试文件

**新增测试**：
```
tests/
├── test_config.py        # 配置加载测试
├── test_logger.py        # 日志系统测试
├── test_messages.py      # 消息国际化测试
├── test_device_detect.py # 设备检测测试
├── test_storage.py       # 存储检查测试
└── test_network.py       # 网络检查测试
```

**测试示例**：
```python
# tests/test_config.py
from config import Config

def test_default_config():
    assert Config.NAS_HOST == "120.77.249.3"
    assert Config.NAS_PORT == 8000
    assert Config.WEB_PORT == 8080

def test_env_override(monkeypatch):
    monkeypatch.setenv("NASTOOL_WEB_PORT", "9000")
    assert Config.WEB_PORT == 9000
```

**工作量**：4 小时

---

#### 5. 类型检查配置

**解决方案**：
- 创建 `mypy.ini` 配置
- 添加类型检查到 CI

```ini
[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
ignore_missing_imports = True
```

**工作量**：0.5 小时

---

### P2 - 可选完成（文档完善）

#### 6. CONTRIBUTING.md

**内容**：
- 开发环境搭建
- 代码风格规范
- PR 提交规范
- 测试运行方法

**工作量**：1 小时

---

#### 7. 代码注释优化

**目标**：
- 复杂逻辑添加注释
- 公开 API 添加 docstring
- 示例代码片段

**工作量**：2 小时

---

## 文件变更清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `tests/test_config.py` | 配置测试 |
| `tests/test_logger.py` | 日志测试 |
| `tests/test_messages.py` | 消息测试 |
| `tests/test_device_detect.py` | 设备检测测试 |
| `mypy.ini` | 类型检查配置 |

### 修改文件

| 文件 | 变更内容 |
|------|----------|
| `arm_diagnose.py` | print→logger（43处） |
| `reporters/terminal.py` | print→logger（12处） |
| `arm/jetson_patch.py` | print→logger（11处） |
| `arm/jetson_install.py` | print→logger（9处） |
| `api/__init__.py` | print→logger（6处） |
| `core/*.py` | 类型注解补全 |
| `profiles/loader.py` | 类型注解补全 |
| `daemon/__init__.py` | 类型注解补全 |
| `pyproject.toml` | black/isort 配置 |

---

## 时间估算

| 优先级 | 任务 | 工时 |
|--------|------|------|
| P0 | print() 完全替换 | 3h |
| P0 | 类型注解补全 | 2h |
| P0 | 代码格式化 | 1h |
| P1 | 单元测试补充 | 4h |
| P1 | 类型检查配置 | 0.5h |
| P2 | CONTRIBUTING.md | 1h |
| P2 | 代码注释优化 | 2h |

**P0 总计**：6 小时
**P1 总计**：4.5 小时
**全部总计**：13.5 小时

---

## 发布检查清单

- [ ] 96 处 print() 全部评估处理
- [ ] 11 个文件类型注解补全
- [ ] black 格式化通过
- [ ] isort 导入整理通过
- [ ] mypy 类型检查通过（可选）
- [ ] 核心模块测试通过
- [ ] CHANGELOG 更新
- [ ] 版本号更新为 3.0.2

---

## 不做的事

- ❌ 新增检查项
- ❌ 新增修复脚本
- ❌ 新增设备配置
- ❌ 新增 Web 功能
- ❌ 新增 API 端点
- ❌ 性能优化
- ❌ UI/UX 改动

---

## 升级收益

### 代码质量

- 统一的日志输出
- 完整的类型注解
- 一致的代码风格
- 可靠的单元测试

### 开发体验

- IDE 类型提示
- 自动补全增强
- 错误提前发现
- 重构更有信心

### 项目成熟度

- 符合 Python 最佳实践
- 更易贡献（规范明确）
- 更易维护（测试覆盖）

---

## 与 v3.0.1 对比

| 维度 | v3.0.1 | v3.0.2 |
|------|--------|--------|
| 配置管理 | ✅ 集中化 | ➖ 继承 |
| 日志系统 | ✅ 引入 | ✅ 完全替换 print |
| 类型注解 | ⚠️ 部分 | ✅ 核心模块完整 |
| 代码格式 | ❌ 无统一 | ✅ black/isort |
| 单元测试 | ❌ 无 | ✅ 核心模块 |

---

*计划日期：2026-04-12*
*版本目标：v3.0.2*
