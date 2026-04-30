# NASTool V7.2 架构文档

## 1. 系统架构概述

NASTool 是一个用于 NAS 设备和 AI 硬件诊断的工具套件，采用模块化架构设计，支持多种设备类型和检查类型。

### 1.1 架构设计原则

- **模块化**：功能按职责划分为独立模块
- **可扩展**：支持插件机制扩展检查能力
- **准确性保障**：内置数据融合和一致性验证机制
- **异步支持**：支持异步数据采集和处理

### 1.2 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI 入口                                 │
│              (nastool-cli/nastool_cli/main.py)                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      核心模块 (nastool-core)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Checks     │  │   Plugin     │  │   Device Manager    │  │
│  │  Registry    │  │   System     │  │                     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │               │
│         ▼                 ▼                      ▼               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              准确性保障层 (Accuracy Layer)                │   │
│  │  DataFusionEngine  |  ConsistencyValidator              │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    适配器层 (nastool-adapters)                  │
│  Jetson | Ascend | ADB | 基准测试 | 报告输出                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    公共模块 (nastool-common)                   │
│  工具函数 | 安全导入 | 报告导出                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 模块结构

### 2.1 模块职责表

| 模块 | 职责 | 关键组件 |
|------|------|----------|
| **nastool-cli** | 命令行接口 | CLI 命令解析、参数处理 |
| **nastool-core** | 核心业务逻辑 | 检查框架、准确性保障、设备管理 |
| **nastool-adapters** | 设备适配 | Jetson/Ascend/ADB 适配器 |
| **nastool-common** | 公共工具 | 工具函数、安全导入 |
| **nastool-reporters** | 报告生成 | 多格式报告输出 |
| **nastool-fixes** | 自动修复 | 修复建议和自动修复 |

### 2.2 核心模块 (nastool-core)

#### 2.2.1 检查框架

```
checks/
├── __init__.py
├── base.py          # 抽象基类 Check
├── registry.py      # 检查注册中心
├── decorators.py    # 装饰器
├── migrate_ctx.py   # 迁移上下文
├── ai/              # AI 相关检查
├── network/         # 网络检查
├── security/        # 安全检查
├── storage/         # 存储检查
├── system/          # 系统检查
├── nas/             # NAS 专属检查
└── usb/             # USB 设备检查
```

#### 2.2.2 准确性保障层

| 组件 | 职责 | 位置 |
|------|------|------|
| **DataFusionEngine** | 多源数据融合 | `utils/data_source.py` |
| **ConsistencyValidator** | 一致性验证 | `utils/consistency_validator.py` |
| **AsyncDataCollector** | 异步数据采集 | `utils/async_data_source.py` |
| **HealthScorer** | 健康评分计算 | `utils/health_scorer.py` |

---

## 3. 核心数据流

### 3.1 检查执行流程

```
CLI 触发 → 检查注册中心 → 实例化检查 → 执行检查 → 数据融合 → 一致性验证 → 结果汇总 → 报告输出
```

#### 详细流程：

1. **触发阶段**：CLI 解析命令参数，确定执行模式（快速/完整）
2. **发现阶段**：从注册表获取所有注册的检查类
3. **执行阶段**：
   - 实例化检查对象
   - 调用 `run()` 方法执行检查
   - 支持同步/异步两种模式
4. **准确性保障阶段**：
   - 多源数据融合（如启用）
   - 一致性验证（时间/值/趋势/来源）
   - 计算综合置信度
5. **汇总阶段**：收集所有检查结果，计算健康分数
6. **输出阶段**：生成报告（文本/JSON/HTML）

### 3.2 数据融合流程

```
数据源1 ──┐
数据源2 ──┼──→ DataFusionEngine ──→ 融合值 + 置信度
数据源3 ──┘
              │
              ▼
       ConsistencyValidator ──→ 一致性报告
              │
              ▼
       综合置信度计算
```

---

## 4. 关键类设计

### 4.1 Check 基类

```python
class Check(ABC):
    # 静态属性（子类需覆盖）
    check_id: str          # 唯一标识
    category: CheckCategory  # 分类
    title: str             # 显示名称
    description: str       # 描述
    
    # 准确性配置
    enable_data_fusion: bool
    enable_consistency_check: bool
    fusion_method: FusionMethod
    
    # 方法
    __init__()            # 初始化准确性保障组件
    run()                 # 执行检查（抽象方法）
    _fuse_multiple_sources()  # 数据融合
    _validate_consistency()   # 一致性验证
    _enhance_result_with_accuracy()  # 增强结果准确性
```

### 4.2 CheckResult 数据类

| 字段 | 类型 | 说明 |
|------|------|------|
| check_id | str | 检查唯一标识 |
| category | CheckCategory | 分类 |
| severity | CheckSeverity | 严重程度 |
| passed | bool | 是否通过 |
| title | str | 标题 |
| current | str | 当前状态 |
| expected | str | 期望状态 |
| message | str | 详细消息 |
| confidence | float | 置信度 (0.0-1.0) |
| data_sources | List[str] | 数据来源 |
| consistency_report | Dict | 一致性报告 |

### 4.3 CheckSummary 数据类

| 字段 | 类型 | 说明 |
|------|------|------|
| total | int | 检查总数 |
| passed | int | 通过数 |
| warnings | int | 警告数 |
| critical | int | 严重问题数 |
| info | int | 信息数 |
| score | int | 健康分数 (0-100) |
| results | List[CheckResult] | 所有结果 |

---

## 5. 插件系统

### 5.1 插件加载流程

```
启动 → 扫描插件目录 → 导入插件模块 → 注册检查类 → 集成到系统
```

### 5.2 插件目录结构

```
plugins/
├── sample_rk_perf.py    # 示例插件
└── your_plugin.py       # 自定义插件
```

### 5.3 插件开发规范

```python
from nastool_core.checks import register_check, Check, CheckResult, CheckCategory

@register_check
class MyCustomCheck(Check):
    check_id = "my_custom_check"
    category = CheckCategory.SYSTEM
    title = "My Custom Check"
    description = "Description of my check"
    
    def run(self) -> CheckResult:
        # 执行检查逻辑
        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=CheckSeverity.PASSED,
            passed=True,
            title=self.title,
            current="OK",
            expected="OK",
            message="Check passed"
        )
```

---

## 6. 设备管理

### 6.1 DeviceManager 功能

| 功能 | 说明 |
|------|------|
| 设备注册 | 注册新设备或更新现有设备 |
| 设备查询 | 支持按组/类型/状态/标签筛选 |
| 设备分组 | 创建和管理设备组 |
| 标签管理 | 添加/移除设备标签 |
| 状态缓存 | 维护设备在线状态 |

### 6.2 数据存储

使用 SQLite 数据库存储设备信息，位于 `~/.nastool/devices.db`。

---

## 7. 报告系统

### 7.1 支持的报告格式

| 格式 | 说明 | 输出文件 |
|------|------|----------|
| text | 纯文本摘要 | stdout |
| json | JSON 格式 | `.json` |
| html | HTML 报告 | `.html` |
| markdown | Markdown 报告 | `.md` |

### 7.2 报告生成流程

```
检查结果 → Reporter → 格式化 → 输出（文件/控制台）
```

---

## 8. 配置管理

### 8.1 配置层次

```
默认配置 → 配置文件 → 命令行参数
```

### 8.2 配置文件位置

- 系统配置：`/etc/nastool/config.toml`
- 用户配置：`~/.nastool/config.toml`
- 项目配置：`./.nastool/config.toml`

---

## 9. 错误处理

### 9.1 异常类型

| 异常 | 说明 |
|------|------|
| CheckError | 检查执行错误 |
| DataSourceError | 数据源错误 |
| ValidationError | 验证错误 |
| ConfigError | 配置错误 |

### 9.2 错误处理策略

- 单个检查失败不影响其他检查
- 错误信息记录到日志
- 用户友好的错误提示

---

## 10. 性能优化

### 10.1 并行执行

支持检查并行执行，通过 `AsyncDataCollector` 实现。

### 10.2 缓存机制

- 检查结果缓存
- 数据源缓存
- 配置缓存

---

## 附录：模块依赖关系

```
nastool-cli
├── nastool-core
│   ├── nastool-common
│   └── nastool-adapters
│       └── nastool-common
├── nastool-reporters
│   └── nastool-common
└── nastool-fixes
    └── nastool-core
```