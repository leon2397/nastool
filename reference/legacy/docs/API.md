# NASTool V7.2 API 文档

## 1. 概述

本文档描述 NASTool 的核心 API，包括检查框架、设备管理、报告生成等模块的接口定义。

---

## 2. 检查框架 API

### 2.1 Check 基类

#### 2.1.1 类定义

```python
class Check(ABC):
    """抽象检查基类"""
    
    check_id: str = "base_check"
    category: CheckCategory = CheckCategory.SYSTEM
    title: str = "Base Check"
    description: str = "Base check class"
    
    enable_data_fusion: bool = True
    enable_consistency_check: bool = True
    fusion_method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE
```

#### 2.1.2 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `run()` | `CheckResult` | 执行检查（必须实现） |
| `_run_command(cmd, timeout=10)` | `str` | 执行 shell 命令 |
| `_read_file(path)` | `str` | 读取文件内容 |
| `_file_exists(path)` | `bool` | 检查文件是否存在 |
| `_command_exists(cmd)` | `bool` | 检查命令是否存在 |
| `_fuse_multiple_sources(results)` | `Tuple[Any, Dict]` | 数据融合 |
| `_validate_consistency(results)` | `Dict` | 一致性验证 |
| `_enhance_result_with_accuracy(result, sources)` | `CheckResult` | 增强结果准确性 |

### 2.2 CheckResult 数据类

```python
@dataclass
class CheckResult:
    check_id: str
    category: CheckCategory
    severity: CheckSeverity
    passed: bool
    title: str
    current: str
    expected: str
    message: str
    fix_available: bool = False
    fix_id: Optional[str] = None
    fix_command: Optional[str] = None
    fix_description: Optional[str] = None
    fix_risk: str = "low"
    url: Optional[str] = None
    details: dict = field(default_factory=dict)
    
    # 准确性字段
    confidence: float = 1.0
    data_sources: List[str] = field(default_factory=list)
    consistency_report: Optional[Dict[str, Any]] = None
```

### 2.3 CheckSummary 数据类

```python
@dataclass
class CheckSummary:
    total: int = 0
    passed: int = 0
    warnings: int = 0
    critical: int = 0
    info: int = 0
    score: int = 0
    results: List[CheckResult] = field(default_factory=list)
```

#### 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `add_result(result)` | `None` | 添加检查结果 |
| `calculate_score()` | `int` | 计算健康分数 |
| `get_health_report(previous_score)` | `HealthReport` | 获取详细健康报告 |

### 2.4 检查注册表 API

#### 2.4.1 注册检查

```python
def register_check(check_class: Type[Check]) -> Type[Check]:
    """装饰器：注册检查类"""
```

**使用示例：**

```python
@register_check
class MyCheck(Check):
    check_id = "my_check"
    # ...
```

#### 2.4.2 获取检查

```python
def get_check(check_id: str) -> Optional[Type[Check]]:
    """根据 ID 获取检查类"""
```

#### 2.4.3 执行所有检查

```python
def run_all_checks(
    skip_categories: Optional[List[CheckCategory]] = None,
    skip_checks: Optional[List[str]] = None
) -> CheckSummary:
    """
    执行所有注册的检查
    
    Args:
        skip_categories: 跳过的分类列表
        skip_checks: 跳过的检查 ID 列表
    
    Returns:
        CheckSummary: 检查汇总结果
    """
```

#### 2.4.4 执行单个检查

```python
def run_check(check_id: str, full: bool = False, offline: bool = False) -> CheckResult:
    """
    执行单个检查
    
    Args:
        check_id: 检查 ID
        full: 是否完整模式（包含基准测试）
        offline: 是否离线模式（跳过网络检查）
    
    Returns:
        CheckResult: 检查结果
    """
```

#### 2.4.5 列出所有检查

```python
def list_available_checks() -> Dict[str, dict]:
    """
    列出所有可用检查及其元数据
    
    Returns:
        Dict[str, dict]: 检查 ID 到元数据的映射
    """
```

---

## 3. 准确性保障 API

### 3.1 DataFusionEngine

#### 3.1.1 初始化

```python
engine = DataFusionEngine(config=DataFusionConfig(...))
```

#### 3.1.2 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `fuse_data(results, method)` | `Tuple[Any, Dict]` | 融合多源数据 |
| `detect_outliers(results)` | `List[int]` | 检测异常值索引 |
| `calculate_confidence(results)` | `float` | 计算数据置信度 |

### 3.2 ConsistencyValidator

#### 3.2.1 初始化

```python
validator = ConsistencyValidator(config=ConsistencyConfig(...))
```

#### 3.2.2 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `validate(results)` | `Dict[str, ConsistencyCheckResult]` | 验证一致性 |
| `check_time_consistency(results)` | `ConsistencyCheckResult` | 时间一致性检查 |
| `check_value_consistency(results)` | `ConsistencyCheckResult` | 值一致性检查 |
| `check_trend_consistency(results)` | `ConsistencyCheckResult` | 趋势一致性检查 |

### 3.3 AsyncDataCollector

#### 3.3.1 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `add_source(name, task, *args, **kwargs)` | `None` | 添加数据源 |
| `collect_sync()` | `List[DataSourceResult]` | 同步采集数据 |
| `collect_async()` | `Awaitable[List[DataSourceResult]]` | 异步采集数据 |
| `collect_and_fuse_sync(method)` | `Tuple[Any, Dict, List]` | 采集并融合 |

---

## 4. 设备管理 API

### 4.1 DeviceManager

#### 4.1.1 初始化

```python
dm = DeviceManager(db_path=None)  # 默认路径: ~/.nastool/devices.db
```

#### 4.1.2 设备操作

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `register_device(device_id, host, ...)` | `Device` | 注册设备 |
| `get_device(device_id)` | `Optional[Device]` | 获取设备 |
| `list_devices(group, type, status, tag)` | `List[Device]` | 列出设备 |
| `remove_device(device_id)` | `bool` | 删除设备 |
| `update_device_status(device_id, status, last_seen)` | `None` | 更新状态 |

#### 4.1.3 标签操作

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `add_tag(device_id, tag)` | `None` | 添加标签 |
| `remove_tag(device_id, tag)` | `None` | 移除标签 |

#### 4.1.4 分组操作

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `create_group(name, description, metadata)` | `DeviceGroup` | 创建组 |
| `get_group(name)` | `Optional[DeviceGroup]` | 获取组 |
| `list_groups()` | `List[DeviceGroup]` | 列出所有组 |
| `delete_group(name)` | `bool` | 删除组 |

### 4.2 Device 数据类

```python
@dataclass
class Device:
    id: str
    host: str
    name: Optional[str] = None
    group: Optional[str] = None
    tags: List[str] = None
    device_type: Optional[str] = None
    last_seen: Optional[str] = None
    status: str = "unknown"
    metadata: Dict[str, Any] = None
```

### 4.3 DeviceGroup 数据类

```python
@dataclass
class DeviceGroup:
    name: str
    description: Optional[str] = None
    device_ids: List[str] = None
    metadata: Dict[str, Any] = None
```

---

## 5. 报告生成 API

### 5.1 FileReporter

#### 5.1.1 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `save_report(results, output_path, format)` | `str` | 保存报告到文件 |
| `save_json(results, output_path)` | `str` | 保存 JSON 格式 |
| `save_html(results, output_path, title)` | `str` | 保存 HTML 格式 |
| `save_markdown(results, output_path)` | `str` | 保存 Markdown 格式 |

### 5.2 报告格式说明

| 格式 | 扩展名 | 特点 |
|------|--------|------|
| json | `.json` | 结构化数据，便于程序处理 |
| html | `.html` | 可视化报告，美观易读 |
| markdown | `.md` | 轻量级，便于版本控制 |

---

## 6. 配置 API

### 6.1 获取准确性配置

```python
from nastool_core.config.accuracy_config import get_accuracy_config

config = get_accuracy_config()
```

### 6.2 配置结构

```python
@dataclass
class AccuracyConfig:
    data_fusion: DataFusionConfig
    consistency: ConsistencyConfig
```

---

## 7. 测试运行器 API

### 7.1 TestRunner

#### 7.1.1 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `discover(module_path, pattern)` | `List[str]` | 发现测试 |
| `run(test_ids, filter_pattern)` | `TestSuiteResult` | 运行测试 |
| `print_report(result)` | `None` | 打印报告 |

### 7.2 RegistryBasedTestRunner

扩展 `TestRunner`，支持从检查注册表发现测试。

```python
runner = RegistryBasedTestRunner()
runner.set_registry(get_registry())
runner.discover_from_registry()
result = runner.run()
```

---

## 8. 快速诊断 API

### 8.1 QuickDiagnose

```python
from nastool_core.utils.quick_diagnose import run_quick_diagnose

result = run_quick_diagnose()
print(result.summary())
```

#### 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `run_quick_diagnose()` | `QuickResult` | 执行快速诊断 |
| `print_quick_report(result)` | `None` | 打印快速报告 |

---

## 9. 示例代码

### 9.1 执行所有检查

```python
from nastool_core.checks import run_all_checks, list_available_checks

# 列出所有检查
checks = list_available_checks()
print(f"Available checks: {len(checks)}")

# 执行所有检查
summary = run_all_checks()
print(f"Score: {summary.score}/100")
print(f"Passed: {summary.passed}/{summary.total}")
```

### 9.2 执行单个检查

```python
from nastool_core.checks import run_check

result = run_check("python_version")
print(f"{result.title}: {'PASS' if result.passed else 'FAIL'}")
print(f"Message: {result.message}")
```

### 9.3 使用设备管理器

```python
from nastool_core.device_manager import DeviceManager

dm = DeviceManager()

# 注册设备
dm.register_device(
    device_id="rk3588-01",
    host="192.168.1.100",
    name="Production Node",
    group="prod",
    tags=["ai", "production"],
    device_type="rk3588"
)

# 列出设备
devices = dm.list_devices(group="prod")
for device in devices:
    print(f"{device.id}: {device.host} ({device.status})")
```

### 9.4 生成报告

```python
from nastool_core.checks import run_all_checks
from nastool_reporters.file_reporter import save_report

summary = run_all_checks()

# 生成 JSON 报告
save_report(summary.results, "/tmp/report.json", format="json")

# 生成 HTML 报告
save_report(summary.results, "/tmp/report.html", format="html")
```

---

## 附录：枚举类型

### CheckCategory

```python
class CheckCategory(Enum):
    SYSTEM = "system"
    NETWORK = "network"
    STORAGE = "storage"
    AI = "ai"
    SECURITY = "security"
    NAS = "nas"
    USB = "usb"
```

### CheckSeverity

```python
class CheckSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    PASSED = "passed"
```

### FusionMethod

```python
class FusionMethod(Enum):
    WEIGHTED_AVERAGE = "weighted_average"
    MEDIAN = "median"
    MAJORITY_VOTE = "majority_vote"
    TRUSTED_SOURCE = "trusted_source"
```