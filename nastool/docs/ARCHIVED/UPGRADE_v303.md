# nastool v3.0.3 升级计划

> 🍓 持续质量优化 - 不新增功能，完善代码规范

## ✅ 已完成 (2026-04-12)

### P0 任务完成

| 任务 | 状态 | 说明 |
|------|------|------|
| constants.py 创建 | ✅ 完成 | 5100 bytes，集中管理路径/端点/阈值 |
| exceptions.py 创建 | ✅ 完成 | 9374 bytes，9 个异常类 |
| 测试文件创建 | ✅ 完成 | test_constants.py + test_exceptions.py |
| 版本更新 | ✅ 完成 | 3.0.2 → 3.0.3 |

### 新增文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `constants.py` | 5,100 bytes | 常量集中管理（路径/端点/阈值/图标） |
| `exceptions.py` | 9,374 bytes | 统一异常类（9 个自定义异常） |
| `tests/test_constants.py` | 5,000 bytes | 常量模块测试 |
| `tests/test_exceptions.py` | 9,448 bytes | 异常类测试 |

### constants.py 内容

```python
DEFAULT_PATHS      # 存储路径（NAS root, media, temp, logs）
DEFAULT_ENDPOINTS  # API 端点路径
DEFAULT_THRESHOLDS # 阈值（磁盘/内存/温度/写入速度）
DEFAULT_PORTS      # 默认端口
CHIP_MANUFACTURERS # 芯片厂商名称
CHECK_CATEGORIES   # 检查分类
FIX_CATEGORIES     # 修复分类
EXIT_CODES         # 退出码
ANSI_COLORS        # ANSI 颜色码
STATUS_ICONS       # 状态图标

# 辅助函数
get_path(key)      # 获取路径（支持嵌套键）
get_endpoint(name) # 获取端点
get_threshold(name)# 获取阈值
```

### exceptions.py 内容

| 异常类 | 用途 |
|--------|------|
| `NastoolError` | 基础异常类 |
| `CheckFailedError` | 诊断检查失败 |
| `FixFailedError` | 自动修复失败 |
| `DeviceNotDetectedError` | 设备检测失败 |
| `ProfileNotFoundError` | 设备配置未找到 |
| `ConfigurationError` | 配置错误 |
| `NetworkError` | 网络错误 |
| `PermissionError` | 权限不足 |
| `DependencyError` | 依赖缺失 |

所有异常都支持 `to_dict()` 方法用于 API 响应。

### 验证结果

| 检查项 | 结果 |
|--------|------|
| 版本号一致性 | ✅ 3.0.3 |
| constants.py 完整性 | ✅ 所有常量定义 |
| exceptions.py 完整性 | ✅ 9 个异常类 |
| 测试文件 | ✅ 7 个测试文件 |
| 代码行数 | 9,020 行 |

---

## 版本定位

**原则**：零新功能，继续优化代码质量

**前置条件**：v3.0.2 已完成类型注解、代码格式化配置

---

## 当前状态诊断

| 指标 | 数值 | 问题 |
|------|------|------|
| print() 语句 | 97 处 | 用户输出保留，日志输出待区分 |
| 硬编码IP | 29 处 | 非config.py中的IP地址 |
| 硬编码路径 | 18 处 | 字符串中的路径引用 |
| 裸 except | 0 处 | ✅ 无隐患 |
| TODO/FIXME | 0 处 | ✅ 无遗留 |
| 文档字符串 | 100% | ✅ 全覆盖 |

---

## 升级目标

| 目标 | 当前状态 | v3.0.3 目标 |
|------|----------|-------------|
| print() 分类 | 97 处未分类 | 区分用户输出/日志输出 |
| 硬编码IP清理 | 29 处 | 移除非必要硬编码 |
| 硬编码路径清理 | 18 处 | 移至配置/常量 |
| 错误处理统一 | 分散 | 统一异常类 |
| 常量抽取 | 分散 | constants.py 集中管理 |

---

## 升级任务清单

### P0 - 必须完成（代码规范）

#### 1. print() 语句分类处理

**问题**：97 处 print() 未区分用途

**分类标准**：
| 类型 | 说明 | 处理方式 |
|------|------|----------|
| **用户输出** | banner、进度、结果展示 | 保留 print() |
| **日志输出** | 状态、错误、调试 | 改用 logger |
| **调试输出** | 开发时临时调试 | 删除或改用 logger.debug() |

**分布**：
| 文件 | 数量 | 主要类型 |
|------|------|----------|
| arm_diagnose.py | 44 | 用户输出 + 日志混合 |
| terminal.py | 12 | 用户输出（报告器）|
| jetson_patch.py | 11 | 日志输出 |
| jetson_install.py | 9 | 日志输出 |
| api/__init__.py | 6 | 日志输出 |

**解决方案**：
```python
# 用户输出 - 保留
print("🔍 Running diagnostics...")
print("✅ Check passed: disk_space")

# 日志输出 - 改用 logger
logger.info("Diagnosis started")
logger.error(f"Check failed: {error}")

# 调试输出 - 删除或降级
# print(f"DEBUG: {var}")  # 删除
logger.debug(f"Variable value: {var}")  # 或降级
```

**工作量**：3 小时

---

#### 2. 硬编码清理

**问题**：29 处硬编码IP、18 处硬编码路径

**解决方案**：

**IP 地址处理**：
```python
# 改造前
response = requests.get("http://120.77.249.3:8000/api/health")

# 改造后
from config import Config
response = requests.get(f"http://{Config.NAS_HOST}:{Config.NAS_PORT}/api/health")
```

**路径处理**：
```python
# 改造前
path = "/nas/media/photos"

# 改造后
from constants import DEFAULT_PATHS
path = DEFAULT_PATHS["media"]["photos"]
```

**新增文件**：`constants.py`
```python
# constants.py
DEFAULT_PATHS = {
    "nas_root": "/nas",
    "media": {
        "photos": "/nas/media/photos",
        "videos": "/nas/media/videos",
    },
    "temp": "/tmp/nastool",
    "logs": "/var/log/nastool",
}

DEFAULT_ENDPOINTS = {
    "health": "/api/health",
    "register": "/api/devices/register",
}
```

**工作量**：2 小时

---

#### 3. 异常类统一

**问题**：异常处理分散，无统一异常类

**解决方案**：创建 `exceptions.py`

```python
# exceptions.py
class NastoolError(Exception):
    """Base exception for nastool"""
    pass

class CheckFailedError(NastoolError):
    """Diagnostic check failed"""
    def __init__(self, check_id: str, message: str):
        self.check_id = check_id
        self.message = message
        super().__init__(f"[{check_id}] {message}")

class FixFailedError(NastoolError):
    """Auto-fix failed"""
    def __init__(self, fix_id: str, reason: str):
        self.fix_id = fix_id
        self.reason = reason
        super().__init__(f"Fix {fix_id} failed: {reason}")

class DeviceNotDetectedError(NastoolError):
    """Could not detect device type"""
    pass

class ProfileNotFoundError(NastoolError):
    """Device profile not found"""
    def __init__(self, profile_id: str):
        self.profile_id = profile_id
        super().__init__(f"Profile not found: {profile_id}")
```

**工作量**：1 小时

---

### P1 - 建议完成（测试覆盖）

#### 4. 核心模块测试扩展

**新增测试**：
```
tests/
├── test_config.py        # 配置加载测试
├── test_logger.py        # 日志系统测试
├── test_messages.py      # 消息国际化测试
├── test_exceptions.py    # 异常类测试
├── test_constants.py     # 常量测试
└── test_integration.py   # 集成测试
```

**测试示例**：
```python
# tests/test_exceptions.py
from exceptions import CheckFailedError, FixFailedError

def test_check_failed_error():
    err = CheckFailedError("disk_space", "Low space")
    assert err.check_id == "disk_space"
    assert "disk_space" in str(err)
    assert "Low space" in str(err)

def test_fix_failed_error():
    err = FixFailedError("install_python", "Permission denied")
    assert err.fix_id == "install_python"
    assert "Permission denied" in str(err)
```

**工作量**：2 小时

---

#### 5. 导入排序优化

**解决方案**：运行 `isort` 统一导入顺序

```bash
isort --check-only --diff .
isort .
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

**工作量**：1 小时

---

## 文件变更清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `constants.py` | 常量集中管理 |
| `exceptions.py` | 统一异常类 |
| `tests/test_exceptions.py` | 异常测试 |
| `tests/test_constants.py` | 常量测试 |

### 修改文件

| 文件 | 变更内容 |
|------|----------|
| `arm_diagnose.py` | print 分类处理、使用异常类 |
| `reporters/terminal.py` | print 保留（用户输出）|
| `arm/jetson_patch.py` | print→logger、使用异常类 |
| `arm/jetson_install.py` | print→logger、使用异常类 |
| `api/__init__.py` | print→logger、使用异常类 |
| `core/*.py` | 使用 constants 和 exceptions |
| `pyproject.toml` | 版本号 3.0.3 |
| `CHANGELOG.md` | v3.0.3 变更日志 |

---

## 时间估算

| 优先级 | 任务 | 工时 |
|--------|------|------|
| P0 | print() 分类处理 | 3h |
| P0 | 硬编码清理 | 2h |
| P0 | 异常类统一 | 1h |
| P1 | 核心模块测试扩展 | 2h |
| P1 | 导入排序优化 | 0.5h |
| P2 | CONTRIBUTING.md | 1h |
| P2 | 代码注释优化 | 1h |

**P0 总计**：6 小时
**P1 总计**：2.5 小时
**全部总计**：10.5 小时

---

## 发布检查清单

- [ ] 97 处 print() 分类完成
- [ ] 29 处硬编码IP清理
- [ ] 18 处硬编码路径清理
- [ ] exceptions.py 创建完成
- [ ] constants.py 创建完成
- [ ] 新增测试通过
- [ ] CHANGELOG 更新
- [ ] 版本号更新为 3.0.3

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

- 清晰的输出分类
- 统一的异常处理
- 集中的常量管理
- 更好的可维护性

### 开发体验

- 异常信息更清晰
- 调试更方便
- 错误追踪更容易

### 项目成熟度

- 符合 Python 最佳实践
- 更易贡献
- 更易维护

---

## 与 v3.0.2 对比

| 维度 | v3.0.2 | v3.0.3 |
|------|--------|--------|
| 类型注解 | ✅ 核心模块 | ➖ 继承 |
| 代码格式 | ✅ black/isort | ➖ 继承 |
| print() | ⚠️ 未分类 | ✅ 分类处理 |
| 硬编码 | ⚠️ 47 处 | ✅ 清理至 constants |
| 异常处理 | ❌ 分散 | ✅ 统一 exceptions.py |
| 常量管理 | ❌ 分散 | ✅ constants.py |

---

*计划日期：2026-04-12*
*版本目标：v3.0.3*
