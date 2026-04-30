# nastool 项目拆分计划 v1.0

> **目标：** 模块化拆分，独立开发，统一协调，提升稳定性
> **创建：** 2026-04-17
> **当前状态：** 单体项目，~260 个 Python 文件

---

## 一、当前结构分析

### 1.1 目录结构

```
C:\tools416\nastool\
├── arm_diagnose.py        # 主入口（22KB）
├── config.py              # 配置管理
├── constants.py           # 常量定义
├── exceptions.py          # 异常类
├── logger.py              # 日志工具
├── messages.py            # 消息模板
├── jetson_install.py      # Jetson 安装脚本
├── jetson_patch.py        # Jetson 补丁
│
├── checks/                # 检测模块（103py）
│   ├── __init__.py
│   ├── base.py            # 基类
│   ├── registry.py        # 注册中心
│   ├── system/            # 系统检测
│   ├── hardware/          # 硬件检测
│   ├── network/           # 网络检测
│   ├── storage/           # 存储检测
│   └── ...                # 其他分类
│
├── adapters/              # 适配器层（28py）
│   ├── ssh/               # SSH 连接
│   ├── usb/               # USB 连接
│   ├── relay/             # Relay 连接
│   └── mock/              # Mock 适配器
│
├── fixes/                 # 修复模块（29py）
│   ├── __init__.py
│   ├── base.py
│   ├── system/            # 系统修复
│   ├── network/           # 网络修复
│   └── ...
│
├── reporters/             # 报告输出（9py）
│   ├── terminal.py        # 终端输出
│   ├── html.py            # HTML 报告
│   ├── json_report.py     # JSON 输出
│   └── ...
│
├── core/                  # 核心功能（17py）
│   ├── config_loader.py   # 配置加载
│   ├── history.py         # 历史记录
│   ├── plugin.py          # 插件系统
│   └── ...
│
├── data/                  # 数据层（4py）
│   ├── mock_profiles.py   # Mock 数据
│   └── ...
│
├── profiles/              # 设备配置（2py）
├── schemas/               # 数据结构（3py）
├── utils/                 # 工具函数（19py）
├── tests/                 # 测试用例（37py）
├── docs/                  # 文档
└── scripts/               # 脚本
```

### 1.2 依赖关系图

```
arm_diagnose.py (主入口)
    ├── checks/ ──────→ schemas/, utils/
    ├── adapters/ ────→ core/, utils/
    ├── fixes/ ───────→ checks/, utils/
    ├── reporters/ ───→ checks/, schemas/
    └── core/ ────────→ utils/, config.py

关键依赖：
  checks → schemas (CheckResult, CheckSeverity)
  fixes → checks (需要检测结果)
  reporters → checks (需要输出结果)
  adapters → core (配置、日志)
```

---

## 二、拆分目标

### 2.1 设计原则

1. **单向依赖** — 下层不依赖上层
2. **接口清晰** — 模块间通过明确的数据结构通信
3. **独立开发** — 每个模块可单独 pip install -e
4. **统一协调** — workspace 目录管理版本和集成测试

### 2.2 拆分后结构

```
C:\tools416\
│
├── nastool-core/              # 核心：检测引擎
│   ├── pyproject.toml
│   ├── nastool_core/
│   │   ├── __init__.py
│   │   ├── checks/            # 103个检测项
│   │   ├── schemas/           # CheckResult, CheckSeverity
│   │   └── constants.py       # 常量
│   └── tests/
│
├── nastool-adapters/          # 适配器层
│   ├── pyproject.toml
│   ├── nastool_adapters/
│   │   ├── __init__.py
│   │   ├── base.py            # 适配器基类
│   │   ├── ssh/               # SSH 适配器
│   │   ├── usb/               # USB 适配器
│   │   ├── relay/             # Relay 适配器
│   │   └── mock/              # Mock 适配器
│   └── tests/
│
├── nastool-fixes/             # 修复模块
│   ├── pyproject.toml
│   ├── nastool_fixes/
│   │   ├── __init__.py
│   │   ├── base.py            # 修复基类
│   │   ├── system/            # 系统修复
│   │   ├── network/           # 网络修复
│   │   └── registry.py        # 修复注册
│   └── tests/
│
├── nastool-reporters/         # 报告输出
│   ├── pyproject.toml
│   ├── nastool_reporters/
│   │   ├── __init__.py
│   │   ├── base.py            # 报告基类
│   │   ├── terminal.py        # 终端输出
│   │   ├── html/              # HTML 报告
│   │   ├── json_report.py     # JSON 输出
│   │   └── markdown.py        # Markdown 输出
│   └── tests/
│
├── nastool-cli/               # 命令行入口
│   ├── pyproject.toml
│   ├── nastool_cli/
│   │   ├── __init__.py
│   │   ├── main.py            # 主入口（原 arm_diagnose.py）
│   │   ├── commands/          # 子命令
│   │   │   ├── diagnose.py
│   │   │   ├── monitor.py
│   │   │   └── web.py
│   │   └── jetson/            # Jetson 专用
│   └── tests/
│
├── nastool-common/            # 公共工具
│   ├── pyproject.toml
│   ├── nastool_common/
│   │   ├── __init__.py
│   │   ├── config.py          # 配置管理
│   │   ├── logger.py          # 日志工具
│   │   ├── exceptions.py      # 异常类
│   │   ├── messages.py        # 消息模板
│   │   └── utils/             # 工具函数
│   └── tests/
│
└── nastool-workspace/         # 协调总目录
    ├── pyproject.toml         # workspace 配置
    ├── docs/                  # 文档
    ├── integration_tests/     # 集成测试
    ├── scripts/               # 构建/发布脚本
    └── profiles/              # 设备配置
```

---

## 三、模块职责定义

### 3.1 nastool-core（核心检测引擎）

**职责：**
- 定义检测基类 `Check` 和结果结构 `CheckResult`
- 实现 103 个检测项（system/hardware/network/storage/...）
- 提供检测注册中心 `CheckRegistry`
- 输出标准化检测结果

**依赖：** 无外部依赖（仅 Python 标准库）

**接口：**
```python
# 入口
def run_all_checks(device_info: dict) -> List[CheckResult]

# 数据结构
@dataclass
class CheckResult:
    check_id: str
    category: CheckCategory
    severity: CheckSeverity
    passed: bool
    title: str
    message: str
    ...
```

---

### 3.2 nastool-adapters（适配器层）

**职责：**
- 定义适配器基类 `DeviceAdapter`
- 实现 SSH/USB/Relay/Mock 连接方式
- 提供统一的设备信息获取接口

**依赖：** `nastool-common`

**接口：**
```python
class DeviceAdapter(ABC):
    @abstractmethod
    def connect(self) -> bool: ...
    
    @abstractmethod
    def get_device_info(self) -> dict: ...
    
    @abstractmethod
    def run_command(self, cmd: str) -> str: ...
```

---

### 3.3 nastool-fixes（修复模块）

**职责：**
- 定义修复基类 `Fix`
- 实现 29 个修复脚本
- 提供修复注册中心

**依赖：** `nastool-core`, `nastool-common`

**接口：**
```python
class Fix(ABC):
    @abstractmethod
    def can_fix(self, result: CheckResult) -> bool: ...
    
    @abstractmethod
    def apply(self) -> FixResult: ...
```

---

### 3.4 nastool-reporters（报告输出）

**职责：**
- 定义报告基类 `Reporter`
- 实现终端/HTML/JSON/Markdown 输出格式
- 支持自定义报告模板

**依赖：** `nastool-core`, `nastool-common`

**接口：**
```python
class Reporter(ABC):
    @abstractmethod
    def render(self, results: List[CheckResult]) -> str: ...
```

---

### 3.5 nastool-cli（命令行入口）

**职责：**
- 解析命令行参数
- 调用各模块完成诊断/修复/监控
- 协调工作流

**依赖：** 所有模块

---

### 3.6 nastool-common（公共工具）

**职责：**
- 配置管理
- 日志工具
- 异常定义
- 消息模板
- 通用工具函数

**依赖：** 无

---

## 四、依赖关系图

```
                    nastool-cli
                         │
         ┌───────────────┼───────────────┐
         ↓               ↓               ↓
   nastool-fixes   nastool-reporters   nastool-adapters
         │               │               │
         └───────────────┼───────────────┘
                         ↓
                   nastool-core
                         │
                         ↓
                  nastool-common
```

**依赖规则：**
- 上层可依赖下层
- 下层不可依赖上层
- 同层模块不可相互依赖

---

## 五、执行计划

### 5.1 Phase 1：准备工作（1天）

| 步骤 | 任务 | 产出 |
|------|------|------|
| 1.1 | 创建目标目录结构 | 6个空模块目录 |
| 1.2 | 为每个模块创建 pyproject.toml | 6个配置文件 |
| 1.3 | 创建 nastool-workspace 目录 | workspace/ |
| 1.4 | 备份原项目 | nastool-backup/ |

---

### 5.2 Phase 2：拆分 nastool-common（1天）

| 步骤 | 任务 | 文件 |
|------|------|------|
| 2.1 | 移动 config.py | → nastool-common/ |
| 2.2 | 移动 logger.py | → nastool-common/ |
| 2.3 | 移动 exceptions.py | → nastool-common/ |
| 2.4 | 移动 messages.py | → nastool-common/ |
| 2.5 | 移动 utils/ | → nastool-common/ |
| 2.6 | 更新 import 路径 | 所有引用文件 |
| 2.7 | 编写单元测试 | tests/ |

**验证：** `pip install -e nastool-common && python -c "from nastool_common import config, logger"`

---

### 5.3 Phase 3：拆分 nastool-core（2天）

| 步骤 | 任务 | 文件数 |
|------|------|--------|
| 3.1 | 移动 schemas/ | 3 |
| 3.2 | 移动 checks/ | 103 |
| 3.3 | 移动 constants.py | 1 |
| 3.4 | 更新 import 路径 | ~50 |
| 3.5 | 编写单元测试 | tests/ |

**验证：** `pip install -e nastool-core && python -c "from nastool_core.checks import run_all_checks"`

---

### 5.4 Phase 4：拆分 nastool-adapters（1天）

| 步骤 | 任务 | 文件数 |
|------|------|--------|
| 4.1 | 移动 adapters/ | 28 |
| 4.2 | 更新 import 路径 | ~20 |
| 4.3 | 编写单元测试 | tests/ |

**验证：** `pip install -e nastool-adapters && python -c "from nastool_adapters import SSHAdapter"`

---

### 5.5 Phase 5：拆分 nastool-reporters（1天）

| 步骤 | 任务 | 文件数 |
|------|------|--------|
| 5.1 | 移动 reporters/ | 9 |
| 5.2 | 更新 import 路径 | ~10 |
| 5.3 | 编写单元测试 | tests/ |

**验证：** `pip install -e nastool-reporters && python -c "from nastool_reporters import TerminalReporter"`

---

### 5.6 Phase 6：拆分 nastool-fixes（1天）

| 步骤 | 任务 | 文件数 |
|------|------|--------|
| 6.1 | 移动 fixes/ | 29 |
| 6.2 | 更新 import 路径 | ~30 |
| 6.3 | 编写单元测试 | tests/ |

**验证：** `pip install -e nastool-fixes && python -c "from nastool_fixes import list_available_fixes"`

---

### 5.7 Phase 7：拆分 nastool-cli（1天）

| 步骤 | 任务 | 文件数 |
|------|------|--------|
| 7.1 | 重构 arm_diagnose.py | 1 |
| 7.2 | 移动 jetson_*.py | 2 |
| 7.3 | 更新 import 路径 | ~10 |
| 7.4 | 编写集成测试 | tests/ |

**验证：** `pip install -e nastool-cli && nastool --version`

---

### 5.8 Phase 8：集成测试（1天）

| 步骤 | 任务 |
|------|------|
| 8.1 | 在 nastool-workspace 创建集成测试 |
| 8.2 | 验证各模块组合工作正常 |
| 8.3 | 验证 --mock 模式正常 |
| 8.4 | 验证 --fix 模式正常 |

---

## 六、时间估算

| Phase | 内容 | 时间 |
|-------|------|------|
| Phase 1 | 准备工作 | 1天 |
| Phase 2 | nastool-common | 1天 |
| Phase 3 | nastool-core | 2天 |
| Phase 4 | nastool-adapters | 1天 |
| Phase 5 | nastool-reporters | 1天 |
| Phase 6 | nastool-fixes | 1天 |
| Phase 7 | nastool-cli | 1天 |
| Phase 8 | 集成测试 | 1天 |
| **总计** | | **9天** |

---

## 七、风险与缓解

| 风险 | 影响 | 缓解方案 |
|------|------|---------|
| 循环依赖 | 阻塞开发 | 用 pyproject.toml 依赖声明强制检查 |
| import 路径遗漏 | 运行时报错 | 用 grep 全局搜索旧路径 |
| 测试覆盖不足 | 回归问题 | 每个模块拆分前先写测试 |
| 版本不同步 | 兼容性问题 | 用 workspace 统一版本号 |

---

## 八、后续优化方向

1. **发布到 PyPI** — 每个模块独立发布
2. **插件系统** — 允许第三方开发检测项
3. **配置分离** — 设备配置独立管理
4. **Web UI** — nastool-web 独立项目

---

_创建：2026-04-17 08:10 GMT+8_
