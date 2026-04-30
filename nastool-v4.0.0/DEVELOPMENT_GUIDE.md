# NASTool V4.1 开发指南

**版本**: V4.1
**发布日期**: 2026-04-27
**适用平台**: ARM设备

## 📋 目录

1. [架构概述](#1-架构概述)
2. [核心模块](#2-核心模块)
3. [API参考](#3-API参考)
4. [开发流程](#4-开发流程)
5. [测试指南](#5-测试指南)
6. [贡献指南](#6-贡献指南)

## 1. 架构概述

NASTool采用模块化架构，将检测功能、数据处理和报告生成分离，便于扩展和维护。

### 1.1 目录结构

```
nastool-core/
├── checks/                  # 检测模块
│   ├── base.py              # Check基类
│   ├── system/              # 系统检测
│   ├── network/             # 网络检测
│   ├── storage/             # 存储检测
│   ├── ai/                  # AI检测
│   ├── security/            # 安全检测
│   └── nas/                 # NAS检测
├── utils/                   # 工具模块
│   ├── data_source.py       # 数据融合引擎
│   ├── device_identifier.py # 设备识别器
│   ├── threshold_config.py  # 阈值配置
│   ├── calibration.py       # 校准机制
│   ├── history.py           # 历史数据
│   ├── environment.py       # 环境数据
│   └── confidence_scorer.py # 置信度评分
├── config/                  # 配置文件
├── tests/                   # 测试目录
└── main.py                  # 主入口
```

### 1.2 核心流程

1. **检测初始化**: 加载配置、识别设备类型
2. **数据采集**: 从多个数据源获取数据
3. **数据处理**: 融合数据、检测异常值、验证一致性
4. **结果评估**: 计算置信度、应用阈值
5. **报告生成**: 生成检测报告、存储历史数据

## 2. 核心模块

### 2.1 检测基类 (Check)

```python
class Check(ABC):
    """检测基类"""
    
    @abstractmethod
    def run(self, target: str) -> CheckResult:
        """执行检测"""
        pass
    
    def get_thresholds(self, device_type: str) -> Dict[str, Any]:
        """获取设备特定阈值"""
        pass
    
    def validate_result(self, result: Any) -> bool:
        """验证检测结果"""
        pass
```

### 2.2 数据融合引擎 (DataFusionEngine)

```python
class DataFusionEngine:
    """数据融合引擎"""
    
    def fuse_data(
        self,
        results: List[DataSourceResult],
        fusion_method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE,
        weights: Optional[Dict[str, float]] = None
    ) -> Tuple[Any, Dict[str, Any]]:
        """融合多个数据源的结果"""
        pass
```

### 2.3 设备识别器 (DeviceIdentifier)

```python
class DeviceIdentifier:
    """设备识别器"""
    
    def identify(self) -> DeviceInfo:
        """识别当前设备"""
        pass
    
    def get_device_type(self) -> str:
        """获取设备类型"""
        pass
```

### 2.4 置信度评分器 (ConfidenceScorer)

```python
class ConfidenceScorer:
    """置信度评分器"""
    
    def calculate_confidence(
        self,
        results: List[DataSourceResult],
        check_id: Optional[str] = None,
        device_type: Optional[str] = None
    ) -> ConfidenceScore:
        """计算置信度评分"""
        pass
```

### 2.5 历史存储 (HistoryStorage)

```python
class HistoryStorage:
    """历史数据存储"""
    
    def save(self, device_id: str, check_id: str, result: CheckResult):
        """保存检测结果"""
        pass
    
    def get_history(
        self,
        device_id: str,
        check_id: str,
        days: int = 30
    ) -> List[CheckResult]:
        """获取历史记录"""
        pass
```

## 3. API参考

### 3.1 命令行接口

| 命令 | 描述 | 示例 |
|------|------|------|
| `--target` | 目标设备 | `--target localhost` |
| `--check` | 检测项 | `--check cpu_temp,network` |
| `--json` | JSON输出 | `--json` |
| `--report` | 生成报告 | `--report` |
| `--output` | 输出文件 | `--output report.txt` |
| `--parallel` | 并行度 | `--parallel 4` |
| `--verbose` | 详细模式 | `--verbose` |
| `--self-test` | 自检 | `--self-test` |
| `--calibrate` | 校准 | `--calibrate` |
| `--history` | 历史数据 | `--history --days 7` |

### 3.2 Python API

#### 基本用法

```python
from nastool_core.checks import CheckRegistry
from nastool_core.utils import DataFusionEngine

# 初始化检测注册表
registry = CheckRegistry()

# 执行检测
result = registry.run_check('cpu_temp', 'localhost')
print(f"CPU温度: {result.value}")
print(f"状态: {result.status}")
print(f"置信度: {result.confidence}")

# 使用数据融合引擎
engine = DataFusionEngine()
fusion_result, metadata = engine.fuse_data([
    DataSourceResult(value=50.0, source="thermal", timestamp=1234567890),
    DataSourceResult(value=51.0, source="sensors", timestamp=1234567891)
])
print(f"融合结果: {fusion_result}")
print(f"元数据: {metadata}")
```

#### 设备识别

```python
from nastool_core.utils import DeviceIdentifier

identifier = DeviceIdentifier()
device_info = identifier.identify()
print(f"设备类型: {device_info.type}")
print(f"设备型号: {device_info.model}")
print(f"CPU信息: {device_info.cpu_info}")
```

#### 历史数据

```python
from nastool_core.utils import HistoryStorage

storage = HistoryStorage()

# 保存结果
storage.save('localhost', 'cpu_temp', result)

# 获取历史数据
history = storage.get_history('localhost', 'cpu_temp', days=7)
print(f"历史记录数量: {len(history)}")

# 分析趋势
trend = storage.get_trend('localhost', 'cpu_temp', days=7)
print(f"趋势: {trend.direction}")
print(f"变化率: {trend.change_rate}")
```

## 4. 开发流程

### 4.1 新增检测项

1. **创建检测类**：继承`Check`基类
2. **实现run方法**：执行检测逻辑
3. **添加数据源**：支持多个数据源
4. **注册检测项**：在`CheckRegistry`中注册

### 4.2 示例：创建新检测项

```python
from nastool_core.checks.base import Check, CheckResult
from nastool_core.utils.data_source import DataSourceResult, DataFusionEngine
from nastool_core.utils.device_identifier import DeviceIdentifier

class MyCustomCheck(Check):
    """自定义检测项"""
    
    def run(self, target: str) -> CheckResult:
        # 1. 识别设备
        identifier = DeviceIdentifier()
        device_type = identifier.get_device_type()
        
        # 2. 从多个数据源获取数据
        results = []
        # 添加数据源1
        results.append(DataSourceResult(
            value=self._get_data_from_source1(target),
            source="source1",
            timestamp=datetime.now().timestamp(),
            confidence=0.9
        ))
        # 添加数据源2
        results.append(DataSourceResult(
            value=self._get_data_from_source2(target),
            source="source2",
            timestamp=datetime.now().timestamp(),
            confidence=0.85
        ))
        
        # 3. 融合数据
        engine = DataFusionEngine()
        fused_value, metadata = engine.fuse_data(results)
        
        # 4. 获取阈值
        thresholds = self.get_thresholds(device_type)
        
        # 5. 评估结果
        status = self._evaluate_status(fused_value, thresholds)
        
        # 6. 返回结果
        return CheckResult(
            check_id="my_custom_check",
            value=fused_value,
            status=status,
            message=f"Custom check result: {fused_value}",
            confidence=metadata.get("confidence", 0.0),
            metadata=metadata
        )
    
    def _get_data_from_source1(self, target: str) -> float:
        # 实现数据源1的逻辑
        pass
    
    def _get_data_from_source2(self, target: str) -> float:
        # 实现数据源2的逻辑
        pass
```

### 4.3 注册检测项

在`checks/__init__.py`中添加：

```python
from .my_custom_check import MyCustomCheck

# 注册检测项
CheckRegistry.register('my_custom_check', MyCustomCheck())
```

## 5. 测试指南

### 5.1 单元测试

```bash
# 运行单元测试
python -m pytest tests/test_core.py -v

# 运行特定测试
python -m pytest tests/test_core.py::test_check_result_creation -v
```

### 5.2 集成测试

```bash
# 运行集成测试
python -m pytest tests/test_data_fusion_integration.py -v

# 运行所有测试
python -m pytest tests/ -v
```

### 5.3 性能测试

```bash
# 运行性能测试
python -m pytest tests/test_data_fusion_integration.py::TestDataFusionIntegration::test_performance -v

# 测试执行时间
python -c "import time; start = time.time(); from nastool_core.utils import DataFusionEngine; engine = DataFusionEngine(); print(f'初始化时间: {time.time() - start}s')"
```

### 5.4 测试覆盖率

```bash
# 安装测试覆盖率工具
pip install pytest-cov

# 运行测试并生成覆盖率报告
python -m pytest tests/ --cov=nastool_core --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

## 6. 贡献指南

### 6.1 代码风格

- **PEP 8**：遵循PEP 8代码风格
- **类型提示**：使用类型提示
- **文档字符串**：为所有类和方法添加文档字符串
- **测试**：为新功能添加测试

### 6.2 提交流程

1. **Fork仓库**：在GitHub上fork仓库
2. **创建分支**：创建特性分支
3. **开发**：实现功能或修复bug
4. **测试**：运行测试确保通过
5. **提交**：提交代码并添加清晰的提交信息
6. **PR**：创建Pull Request

### 6.3 提交信息规范

```
<类型>(<范围>): <描述>

<详细描述>

<可选的关闭问题>
```

**类型**：
- `feat`：新功能
- `fix`：bug修复
- `docs`：文档更新
- `style`：代码风格
- `refactor`：代码重构
- `test`：测试添加
- `chore`：构建或依赖更新

**示例**：

```
feat(data_fusion): 添加几何平均融合方法

- 实现几何平均融合方法
- 添加相关测试用例
- 更新文档

Closes #123
```

### 6.4 代码审查

- **自我审查**：在提交前审查自己的代码
- **代码风格**：确保代码风格一致
- **测试覆盖**：确保测试覆盖新功能
- **文档**：确保文档与代码同步

## 📞 支持

- **GitHub Issues**: [https://github.com/nastool/nastool/issues](https://github.com/nastool/nastool/issues)
- **Discord**: [https://discord.gg/nastool](https://discord.gg/nastool)
- **文档**: [https://docs.nastool.org](https://docs.nastool.org)

---

**最后更新**: 2026-04-27
**版本**: 1.0